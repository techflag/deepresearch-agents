from __future__ import annotations
import asyncio
import time
from typing import Dict, List, Optional
from .agents.baseclass import ResearchRunner
from .agents.writer_agent import writer_agent
from .agents.knowledge_gap_agent import KnowledgeGapOutput, knowledge_gap_agent
from .agents.tool_selector_agent import AgentTask, AgentSelectionPlan, tool_selector_agent
from .agents.thinking_agent import thinking_agent
from .agents.tool_agents import TOOL_AGENTS, ToolAgentOutput
from pydantic import BaseModel, Field
from .utils.logging import log_message,TraceInfo
import json

class IterationData(BaseModel):
    """单次研究循环迭代的数据。"""
    gap: str = Field(description="迭代中解决的差距", default_factory=list)
    tool_calls: List[str] = Field(description="进行的工具调用", default_factory=list)
    findings: List[str] = Field(description="从工具调用中收集的发现", default_factory=list)
    thought: List[str] = Field(description="对迭代成功和下一步进行反思的思考", default_factory=list)


class Conversation(BaseModel):
    """用户与迭代研究者之间的对话。"""
    history: List[IterationData] = Field(description="研究循环每次迭代的数据", default_factory=list)

    def add_iteration(self, iteration_data: Optional[IterationData] = None):
        if iteration_data is None:
            iteration_data = IterationData()
        self.history.append(iteration_data)
    
    def set_latest_gap(self, gap: str):
        self.history[-1].gap = gap

    def set_latest_tool_calls(self, tool_calls: List[str]):
        self.history[-1].tool_calls = tool_calls

    def set_latest_findings(self, findings: List[str]):
        self.history[-1].findings = findings

    def set_latest_thought(self, thought: str):
        self.history[-1].thought = thought

    def get_latest_gap(self) -> str:
        return self.history[-1].gap
    
    def get_latest_tool_calls(self) -> List[str]:
        return self.history[-1].tool_calls
    
    def get_latest_findings(self) -> List[str]:
        return self.history[-1].findings
    
    def get_latest_thought(self) -> str:
        return self.history[-1].thought
    
    def get_all_findings(self) -> List[str]:
        return [finding for iteration_data in self.history for finding in iteration_data.findings]

    def compile_conversation_history(self) -> str:
        """将对话历史编译成字符串。"""
        conversation = ""
        for iteration_num, iteration_data in enumerate(self.history):
            conversation += f"[迭代 {iteration_num + 1}]\n\n"
            if iteration_data.thought:
                conversation += f"{self.get_thought_string(iteration_num)}\n\n"
            if iteration_data.gap:
                conversation += f"{self.get_task_string(iteration_num)}\n\n"
            if iteration_data.tool_calls:
                conversation += f"{self.get_action_string(iteration_num)}\n\n"
            if iteration_data.findings:
                conversation += f"{self.get_findings_string(iteration_num)}\n\n"

        return conversation
    
    def get_task_string(self, iteration_num: int) -> str:
        """获取当前迭代的任务。"""
        if self.history[iteration_num].gap:
            return f"<task>\n解决这个知识差距：{self.history[iteration_num].gap}\n</task>"
        return ""
    
    def get_action_string(self, iteration_num: int) -> str:
        """获取当前迭代的行动。"""
        if self.history[iteration_num].tool_calls:
            joined_calls = '\n'.join(self.history[iteration_num].tool_calls)
            return (
                "<action>\n调用以下工具来解决知识差距：\n"
                f"{joined_calls}\n</action>"
            )
        return ""
        
    def get_findings_string(self, iteration_num: int) -> str:
        """获取当前迭代的发现。"""
        if self.history[iteration_num].findings:
            joined_findings = '\n\n'.join(self.history[iteration_num].findings)
            return f"<findings>\n{joined_findings}\n</findings>"
        return ""
    
    def get_thought_string(self, iteration_num: int) -> str:
        """获取当前迭代的思考。"""
        if self.history[iteration_num].thought:
            return f"<thought>\n{self.history[iteration_num].thought}\n</thought>"
        return ""
    
    def latest_task_string(self) -> str:
        """获取最新的任务。"""
        return self.get_task_string(len(self.history) - 1)
    
    def latest_action_string(self) -> str:
        """获取最新的行动。"""
        return self.get_action_string(len(self.history) - 1)
    
    def latest_findings_string(self) -> str:
        """获取最新的发现。"""
        return self.get_findings_string(len(self.history) - 1)
    
    def latest_thought_string(self) -> str:
        """获取最新的思考。"""
        return self.get_thought_string(len(self.history) - 1)
    

class IterativeResearcher:
    """迭代研究工作流的管理器，通过运行连续的研究循环对主题或子主题进行研究。"""

    def __init__(
        self, 
        max_iterations: int = 5,
        max_time_minutes: int = 10,
        verbose: bool = True,
        tracing: bool = False,
    ):
        self.max_iterations: int = max_iterations
        self.max_time_minutes: int = max_time_minutes
        self.start_time: float = None
        self.iteration: int = 0
        self.conversation: Conversation = Conversation()
        self.should_continue: bool = True
        self.verbose: bool = verbose
        self.tracing: bool = tracing
        self.trace_info: TraceInfo = TraceInfo(trace_id="default")
        
    async def run(
            self, 
            query: str,
            trace_info: TraceInfo,
            output_length: str = "",  # 所需输出长度的文本描述，可以留空
            output_instructions: str = "",  # 最终报告的指示（例如，不包括任何标题，只有几段文本）
            background_context: str = "",
        ) -> str:
        """为给定查询运行深度研究工作流。"""
        self.start_time = time.time()
        self.trace_info = trace_info

        await log_message(f"<iteration-flow> 开始迭代研究工作流\n{query}\n</iteration-flow>",self.trace_info)
        
        # 迭代研究循环
        while self.should_continue and self._check_constraints():
            self.iteration += 1
            await log_message(f"<iteration>\n=== 开始迭代 {self.iteration} :\n查询：{query}\n背景：{background_context}</iteration>",self.trace_info)

            # 为此迭代设置空白的 IterationData
            self.conversation.add_iteration()

            # 1. 生成观察
            observations: str = await self._generate_observations(query, background_context=background_context)

            # 2. 评估研究中的当前差距
            evaluation: KnowledgeGapOutput = await self._evaluate_gaps(query, background_context=background_context)
            
            # 检查是否应继续或中断循环
            if not evaluation.research_complete:
                next_gap = evaluation.outstanding_gaps[0]

                # 3. 选择代理来解决知识差距
                selection_plan: AgentSelectionPlan = await self._select_agents(next_gap, query, background_context=background_context)

                # 4. 运行选定的代理以收集信息
                print(f"选择计划: {selection_plan}")
                results: Dict[str, ToolAgentOutput] = await self._execute_tools(selection_plan.tasks)
            else:
                self.should_continue = False
                await log_message("=== 迭代研究者标记为完成 - 正在完成输出 ===",self.trace_info)
        
        # 创建最终报告
        report = await self._create_final_report(query, length=output_length, instructions=output_instructions)
        
        elapsed_time = time.time() - self.start_time
        await log_message(f"迭代研究者在 {int(elapsed_time // 60)} 分钟和 {int(elapsed_time % 60)} 秒后完成，经过 {self.iteration} 次迭代。",self.trace_info)
        

        return report
    
    def _check_constraints(self) -> bool:
        """检查是否超出了我们的约束（最大迭代次数或时间）。"""
        if self.iteration >= self.max_iterations:
            log_message("\n=== 结束研究循环 ===",self.trace_info)
            log_message(f"达到最大迭代次数（{self.max_iterations}）",self.trace_info)
            return False
        
        elapsed_minutes = (time.time() - self.start_time) / 60
        if elapsed_minutes >= self.max_time_minutes:
            log_message("\n=== 结束研究循环 ===",self.trace_info)
            log_message(f"达到最大时间（{self.max_time_minutes} 分钟）",self.trace_info)
            return False
        
        return True
    
    async def _evaluate_gaps(
        self, 
        query: str,
        background_context: str = ""
    ) -> KnowledgeGapOutput:
        """评估研究的当前状态并识别知识差距。"""

        background = f"背景上下文：\n{background_context}" if background_context else ""

        input_str = f"""
        当前迭代次数：{self.iteration}
        已用时间：{(time.time() - self.start_time) / 60:.2f} 分钟，最大 {self.max_time_minutes} 分钟

        原始查询：
        {query}

        {background}

        行动、发现和思考的历史：
        {self.conversation.compile_conversation_history() or "没有之前的行动、发现或思考可用。"}        
        """
        await log_message(f"<evaluate_gaps>评估知识差距\n{input_str}\n</evaluate_gaps>",self.trace_info)
        result = await ResearchRunner.run(
            knowledge_gap_agent,
            input_str,
            context = self.trace_info
        )
        
        try:
            evaluation = result.final_output_as(KnowledgeGapOutput)
        except Exception as e:
            await log_message(f"知识差距评估解析错误: {str(e)}",self.trace_info)
            evaluation = KnowledgeGapOutput(
                research_complete=False,
                outstanding_gaps=["无法解析知识差距评估结果"]
            )

        if not evaluation.research_complete:
            next_gap = evaluation.outstanding_gaps[0]
            self.conversation.set_latest_gap(next_gap)
            """<task>
            解决这个知识差距：{next_gap}
            </task>"""
            await log_message(self.conversation.latest_task_string(),self.trace_info)
        
        return evaluation
    
    async def _select_agents(
        self, 
        gap: str, 
        query: str,
        background_context: str = ""
    ) -> AgentSelectionPlan:
        """选择代理来解决已识别的知识差距。"""
        
        background = f"背景上下文：\n{background_context}" if background_context else ""

        input_str = f"""
        原始查询：
        {query}

        要解决的知识差距：
        {gap}

        {background}

        
        行动、发现和思考的历史：
        {self.conversation.compile_conversation_history() or "没有之前的行动、发现或思考可用。"}
        """
        await log_message(f"<agent-select>\n=== 选择代理以解决知识差距：{gap} ===</agent-select>",self.trace_info)
        result = await ResearchRunner.run(
            tool_selector_agent,
            input_str,
            context = self.trace_info
        )
        
        selection_plan = result.final_output_as(AgentSelectionPlan)
        

        # 将工具调用添加到对话中
        self.conversation.set_latest_tool_calls([
            f"[Agent] {task.agent} [Query] {task.query} [Entity] {task.entity_website if task.entity_website else 'null'}" for task in selection_plan.tasks
        ])
        """
        <action>
        调用以下工具来解决知识差距：
        """
        await log_message(self.conversation.latest_action_string(),self.trace_info)
        
        return selection_plan
    
    async def _execute_tools(self, tasks: List[AgentTask]) -> Dict[str, ToolAgentOutput]:
        """并发执行选定的工具以收集信息。"""
        # 为每个代理创建一个任务
        async_tasks = []
        for task in tasks:
            async_tasks.append(self._run_agent_task(task))
        
        # 并发运行所有任务
        num_completed = 0
        results = {}
        for future in asyncio.as_completed(async_tasks):
            gap, agent_name, result = await future
            print(f"Tool call for {agent_name}: {result}")
            results[f"{agent_name}_{gap}"] = result
            num_completed += 1
            await log_message(f"<processing>\n{agent_name}执行进度：{num_completed}/{len(async_tasks)}\n</processing>",self.trace_info)

        # 将工具输出的发现添加到对话中
        findings = []
        for tool_output in results.values():
            findings.append(tool_output.output)
        self.conversation.set_latest_findings(findings)

        return results
    
    async def _run_agent_task(self, task: AgentTask) -> tuple[str, str, ToolAgentOutput]:
        """运行单个代理任务并返回结果。"""
        try:
            agent_name = task.agent
            agent = TOOL_AGENTS.get(agent_name)
            
            # 添加详细日志记录
            await log_message(f"<function_tool_client>\n_run_agent_task开始执行代理任务: {agent_name}, 查询: {task.query}\n</function_tool_client>", self.trace_info)
            
            if agent:
                try:
                    task_data = task.model_dump()
                    print(f"task_data:{task_data}")
                    
                    # 对于 WebSearchAgent，添加特殊处理
                    await log_message(f"<function_tool_web_search>\n_run_agent_task执行WebSearchAgent搜索: {task.query}\n实体网站: {task.entity_website if task.entity_website else 'null'}\n</function_tool_web_search>", self.trace_info)
                    
                    # 使用关键字参数调用 ResearchRunner.run
                    result = await ResearchRunner.run(
                        agent, 
                        task_data, 
                        context=self.trace_info
                    )
                    
                    # 记录代理执行完成
                    await log_message(f"<processing>\n代理 {agent_name} 执行完成\n</processing>", self.trace_info)
                    
                    # 从 RunResult 中提取 ToolAgentOutput
                    output = result.final_output_as(ToolAgentOutput)
                    
                    return task.gap, agent_name, output
                except Exception as e:
                    # 捕获并记录 ResearchRunner.run 执行过程中的详细错误
                    import traceback
                    error_msg = f"执行 {agent_name} 时出错：{str(e)}\n{traceback.format_exc()}"
                    await log_message(f"<web_search_error>\n{error_msg}\n</web_search_error>", self.trace_info)
                    output = ToolAgentOutput(
                        output=f"执行 {agent_name} 时出错：{str(e)}",
                        sources=[]
                    )
                    return task.gap, agent_name, output
            else:
                error_msg = f"未找到代理 {agent_name} 的实现"
                await log_message(f"<error>\n{error_msg}\n</error>", self.trace_info)
                output = ToolAgentOutput(
                    output=error_msg,
                    sources=[]
                )
                return task.gap, agent_name, output
            
        except Exception as e:
            # 捕获并记录 _run_agent_task 函数本身的错误
            import traceback
            error_msg = f"执行 {task.agent} 解决差距 '{task.gap}' 时出错：{str(e)}\n{traceback.format_exc()}"
            await log_message(f"<web_search_error>\n{error_msg}\n</web_search_error>", self.trace_info)
            error_output = ToolAgentOutput(
                output=f"执行 {task.agent} 解决差距 '{task.gap}' 时出错：{str(e)}",
                sources=[]
            )
            return task.gap, task.agent, error_output
    
    async def _generate_observations(self, query: str, background_context: str = "") -> str:
        """从研究的当前状态生成观察。"""
                
        background = f"背景上下文：\n{background_context}" if background_context else ""

        input_str = f"""
        原始查询：
        {query}

        {background}

        行动、发现和思考的历史：
        {self.conversation.compile_conversation_history() or "没有之前的行动、发现或思考可用。"}
        """
        result = await ResearchRunner.run(
            thinking_agent,
            input_str,
            context=self.trace_info
        )

        # 将观察添加到对话中
        observations = result.final_output
        self.conversation.set_latest_thought(observations)
        """获取最新的思考。<thought>"""
        await log_message(self.conversation.latest_thought_string(),self.trace_info)
        return observations

    async def _create_final_report(
        self, 
        query: str,
        length: str = "",
        instructions: str = ""
        ) -> str:
        """从完成的草稿创建最终响应。"""
        await log_message("=== 起草最终响应 ===",self.trace_info)

        length_str = f"* 完整响应应约为 {length}。\n" if length else ""
        instructions_str = f"* {instructions}" if instructions else ""
        guidelines_str = ("\n\n指南：\n" + length_str + instructions_str).strip('\n') if length or instructions else ""

        all_findings = '\n\n'.join(self.conversation.get_all_findings()) or "尚可用发现。"

        input_str = f"""
        根据以下查询和发现提供尽可能详细的响应。{guidelines_str}

        查询：{query}

        发现：
        {all_findings}
        """

        result = await ResearchRunner.run(
            writer_agent,
            input_str,
            context = self.trace_info
        )
        
        await log_message("迭代研究者成功创建最终响应",self.trace_info)
        
        return result.final_output
    
    