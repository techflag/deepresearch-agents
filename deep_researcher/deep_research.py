import asyncio
import time
from fastapi import WebSocket
from .iterative_research import IterativeResearcher
from .agents.planner_agent import planner_agent, ReportPlan, ReportPlanSection
from .agents.proofreader_agent import ReportDraftSection, ReportDraft, proofreader_agent
from .agents.long_writer_agent import write_report
from .agents.baseclass import ResearchRunner
from typing import List
from agents.tracing import trace, gen_trace_id, custom_span
from deep_researcher.sse_manager import SSEManager
from .utils.message_parser import MessageParser

class DeepResearcher:
    """
    深度研究工作流的管理器，将查询分解为带有章节的报告计划，然后为每个章节运行迭代研究循环。
    """
    def __init__(
            self, 
            max_iterations: int = 5,
            max_time_minutes: int = 10,
            verbose: bool = True,
            tracing: bool = False,
            client_id: str = "default" 
        ):
        self.max_iterations = max_iterations
        self.max_time_minutes = max_time_minutes
        self.verbose = verbose
        self.tracing = tracing
        self.client_id = client_id 

        if not self.tracing:
            from agents import set_tracing_disabled
            set_tracing_disabled(True)

    async def run(self, query: str) -> str:
        """运行深度研究工作流"""
        start_time = time.time()

        if self.tracing:
            trace_id = gen_trace_id()
            workflow_trace = trace("deep_researcher", trace_id=trace_id)
            print(f"查看跟踪：https://platform.openai.com/traces/trace?trace_id={trace_id}")
            workflow_trace.start(mark_as_current=True)

        # 首先构建报告计划，概述章节并编译与查询相关的任何背景上下文
        report_plan: ReportPlan = await self._build_report_plan(query)

        # 为每个章节并发运行独立的研究循环并收集结果
        research_results: List[str] = await self._run_research_loops(report_plan)
        
        # 从原始报告计划和每个章节的草稿创建最终报告
        final_report: str = await self._create_final_report(query, report_plan, research_results)

        elapsed_time = time.time() - start_time
        self._log_message(f"DeepResearcher 在 {int(elapsed_time // 60)} 分钟和 {int(elapsed_time % 60)} 秒内完成")

        if self.tracing:
            workflow_trace.finish(reset_current=True)

        return final_report

    async def _build_report_plan(self, query: str) -> ReportPlan:
        """构建初始报告计划，包括报告大纲（章节和关键问题）和背景上下文"""
        if self.tracing:
            span = custom_span(name="build_report_plan")
            span.start(mark_as_current=True)

        await self._log_message("<plan-start> 构建报告大纲 </plan-start>")
        user_message = f"QUERY: {query}"
        result = await ResearchRunner.run(
            planner_agent,
            user_message,
            client_id=self.client_id
        )
        report_plan = result.final_output_as(ReportPlan)

        if self.verbose:
            num_sections = len(report_plan.report_outline)
            message_log = '\n\n'.join(f"章节：{section.title}\n关键问题：{section.key_question}" for section in report_plan.report_outline)
            if report_plan.background_context:
                message_log += f"\n\n以下背景上下文已包含在报告构建中：\n{report_plan.background_context}"
            else:
                message_log += "\n\n报告构建中未提供背景上下文。\n"
            await self._log_message(f"<plan-section>已创建包含 {num_sections} 个章节的报告计划：\n{message_log}</plan-section>")

        if self.tracing:
            span.finish(reset_current=True)
        await self._log_message(f"<plan-end> 完整报告计划:\n{report_plan.model_dump_json(indent=2)}</plan-end>")
        return report_plan

    async def _run_research_loops(
        self, 
        report_plan: ReportPlan
    ) -> List[str]:
        """对于给定的 ReportPlan，为每个章节并发运行研究循环并收集结果"""
        async def run_research_for_section(section: ReportPlanSection):
            iterative_researcher = IterativeResearcher(
                max_iterations=self.max_iterations,
                max_time_minutes=self.max_time_minutes,
                verbose=self.verbose,
                tracing=False,
                client_id=self.client_id
            )
            args = {
                "query": section.key_question,
                "output_length": "",
                "output_instructions": "",
                "background_context": report_plan.background_context,
            }
            
            # 仅在启用跟踪时使用自定义跨度
            self._log_message("=== 初始化研究循环 ===")
            if self.tracing:
                with custom_span(
                    name=f"iterative_researcher:{section.title}", 
                    data={"key_question": section.key_question}
                ) as span:
                    await self._log_message(f"<research-start> 开始研究章节: {section.title} - 关键问题: {section.key_question}</research-start>")
                    result = await iterative_researcher.run(**args)
                    await self._log_message(f"<research-end> 完成章节研究: {section.title}</research-end>")
                    return result
            else:
                self._log_message(f"<research-start> 开始研究章节: {section.title} - 关键问题: {section.key_question}</research-start>")
                result = await iterative_researcher.run(**args)
                await self._log_message(f"<research-end> 完成章节研究: {section.title}</research-end>")
                return result
        
        
        # 在单个 gather 调用中并发运行所有研究循环
        research_results = await asyncio.gather(
            *(run_research_for_section(section) for section in report_plan.report_outline)
        )
        for i, result in enumerate(research_results):
                self._log_message(f"<research-result> 章节 {i+1} 研究结果:\n{result}</research-result>")
        return research_results

    async def _create_final_report(
        self, 
        query: str, 
        report_plan: ReportPlan, 
        section_drafts: List[str],
        use_long_writer: bool = True
    ) -> str:
        """从原始报告计划和每个章节的草稿创建最终报告"""
        if self.tracing:
            span = custom_span(name="create_final_report")
            span.start(mark_as_current=True)
        await self._log_message(f"<report-create>=== 构建最终报告 ===</report-create>")
        # 每个章节是一个包含该章节 markdown 的字符串
        # 从中我们需要构建一个 ReportDraft 对象，以提供给最终校对代理
        report_draft = ReportDraft(
            sections=[]
        )
        for i, section_draft in enumerate(section_drafts):
            report_draft.sections.append(
                ReportDraftSection(
                    section_title=report_plan.report_outline[i].title,
                    section_content=section_draft
                )
            )

        
        if use_long_writer:
            await self._log_message(f"<report-draft>使用 LongWriter 处理报告草稿：\n{report_draft.model_dump_json(indent=2)}</report-draft>")
            final_output = await write_report(query, report_plan.report_title, report_draft)
        else:
            user_prompt = f"QUERY:\n{query}\n\nREPORT DRAFT:\n{report_draft.model_dump_json()}"
            # 运行校对代理以生成最终报告
            final_report = await ResearchRunner.run(
                proofreader_agent,
                user_prompt,
                client_id=self.client_id
            )
            final_output = final_report.final_output

        await self._log_message(f"<report-finish>最终报告已完成</report-finish>")

        if self.tracing:
            span.finish(reset_current=True)

        return final_output

    async def _log_message(self, message: str) -> None:
        """如果 verbose 为 True，则记录消息"""
        if self.verbose:
            print(message)
            
            try:
                sse_data = MessageParser.format_sse_data(message, self.client_id)
                await SSEManager.publish(
                    self.client_id, 
                    sse_data["event"], 
                    sse_data["data"]
                )
            except Exception as e:
                print(f"SSE发送失败: {str(e)}")