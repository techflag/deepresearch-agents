from __future__ import annotations
import asyncio
import time
from typing import Dict, List, Optional
from agents import custom_span, gen_trace_id, trace
from .agents.baseclass import ResearchRunner
from .agents.writer_agent import writer_agent
from .agents.knowledge_gap_agent import KnowledgeGapOutput, knowledge_gap_agent
from .agents.tool_selector_agent import AgentTask, AgentSelectionPlan, tool_selector_agent
from .agents.thinking_agent import thinking_agent
from .agents.tool_agents import TOOL_AGENTS, ToolAgentOutput
from pydantic import BaseModel, Field


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
        client_id: str = "default"  # 替换websocket参数为client_id
    ):
        self.max_iterations: int = max_iterations
        self.max_time_minutes: int = max_time_minutes
        self.start_time: float = None
        self.iteration: int = 0
        self.conversation: Conversation = Conversation()
        self.should_continue: bool = True
        self.verbose: bool = verbose
        self.tracing: bool = tracing
        self.client_id = client_id  # 保存client_id
        
    async def run(
            self, 
            query: str,
            output_length: str = "",  # 所需输出长度的文本描述，可以留空
            output_instructions: str = "",  # 最终报告的指示（例如，不包括任何标题，只有几段文本）
            background_context: str = "",
        ) -> str:
        """为给定查询运行深度研究工作流。"""
        self.start_time = time.time()

        if self.tracing:
            trace_id = gen_trace_id()
            workflow_trace = trace("iterative_researcher", trace_id=trace_id)
            print(f"查看跟踪：https://platform.openai.com/traces/trace?trace_id={trace_id}")
            workflow_trace.start(mark_as_current=True)

        await self._log_message("=== 开始迭代研究工作流 ===")
        
        # 迭代研究循环
        while self.should_continue and self._check_constraints():
            self.iteration += 1
            await self._log_message(f"\n=== 开始迭代 {self.iteration} ===")

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
                results: Dict[str, ToolAgentOutput] = await self._execute_tools(selection_plan.tasks)
            else:
                self.should_continue = False
                await self._log_message("=== 迭代研究者标记为完成 - 正在完成输出 ===")
        
        # 创建最终报告
        report = await self._create_final_report(query, length=output_length, instructions=output_instructions)
        
        elapsed_time = time.time() - self.start_time
        await self._log_message(f"迭代研究者在 {int(elapsed_time // 60)} 分钟和 {int(elapsed_time % 60)} 秒后完成，经过 {self.iteration} 次迭代。")
        
        if self.tracing:
            workflow_trace.finish(reset_current=True)

        return report
    
    def _check_constraints(self) -> bool:
        """检查是否超出了我们的约束（最大迭代次数或时间）。"""
        if self.iteration >= self.max_iterations:
            self._log_message("\n=== 结束研究循环 ===")
            self._log_message(f"达到最大迭代次数（{self.max_iterations}）")
            return False
        
        elapsed_minutes = (time.time() - self.start_time) / 60
        if elapsed_minutes >= self.max_time_minutes:
            self._log_message("\n=== 结束研究循环 ===")
            self._log_message(f"达到最大时间（{self.max_time_minutes} 分钟）")
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
        await self._log_message(f"<evaluate_gaps>评估知识差距\n{input_str}\n</evaluate_gaps>")
        result = await ResearchRunner.run(
            knowledge_gap_agent,
            input_str,
        )
        
        try:
            evaluation = result.final_output_as(KnowledgeGapOutput)
        except Exception as e:
            await self._log_message(f"知识差距评估解析错误: {str(e)}")
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
            await self._log_message(self.conversation.latest_task_string())
        
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
        await self._log_message(f"\n=== 选择代理以解决知识差距：{gap} ===")
        result = await ResearchRunner.run(
            tool_selector_agent,
            input_str,
            client_id=self.client_id
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
        await self._log_message(self.conversation.latest_action_string())
        
        return selection_plan
    
    async def _execute_tools(self, tasks: List[AgentTask]) -> Dict[str, ToolAgentOutput]:
        """并发执行选定的工具以收集信息。"""
        with custom_span("执行工具代理"):
            # 为每个代理创建一个任务
            async_tasks = []
            for task in tasks:
                async_tasks.append(self._run_agent_task(task))
            
            # 并发运行所有任务
            num_completed = 0
            results = {}
            for future in asyncio.as_completed(async_tasks):
                gap, agent_name, result = await future
                results[f"{agent_name}_{gap}"] = result
                num_completed += 1
                await self._log_message(f"<processing>\n工具执行进度：{num_completed}/{len(async_tasks)}\n</processing>")

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
            if agent:
                result = await ResearchRunner.run(
                    agent,
                    task.model_dump_json(),
                )
                # 从 RunResult 中提取 ToolAgentOutput
                output = result.final_output_as(ToolAgentOutput)
            else:
                output = ToolAgentOutput(
                    output=f"未找到代理 {agent_name} 的实现",
                    sources=[]
                )
            
            return task.gap, agent_name, output
        except Exception as e:
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
        )

        # 将观察添加到对话中
        observations = result.final_output
        self.conversation.set_latest_thought(observations)
        """获取最新的思考。<thought>"""
        await self._log_message(self.conversation.latest_thought_string())
        return observations

    async def _create_final_report(
        self, 
        query: str,
        length: str = "",
        instructions: str = ""
        ) -> str:
        """从完成的草稿创建最终响应。"""
        await self._log_message("=== 起草最终响应 ===")

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
        )
        
        await self._log_message("迭代研究者成功创建最终响应")
        
        return result.final_output
    
    async def _log_message(self, message: str) -> None:
        """增强日志功能，支持SSE发送"""
        if self.verbose:
            print(message)
            
            # 解析不同类型的消息
            if message.startswith("<task>"):
                event_type = "task"
                content = message[6:-7]  # 移除 <task> 和 </task>
            elif message.startswith("<action>"):
                event_type = "action"
                content = message[8:-9]  # 移除 <action> 和 </action>
            elif message.startswith("<findings>"):
                event_type = "findings"
                content = message[10:-11]  # 移除 <findings> 和 </findings>
            elif message.startswith("<thought>"):
                event_type = "thought"
                content = message[9:-10]  # 移除 <thought> 和 </thought>
            elif message.startswith("<processing>"):
                event_type = "processing"
                content = message[12:-13]  # 移除 <processing> 和 </processing>
            else:
                event_type = "info"
                content = message