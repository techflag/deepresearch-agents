"""
用于生成报告初始大纲的代理，包括章节标题列表和每个章节要解决的关键问题。

该代理接受以下格式的字符串作为输入：
===========================================================
QUERY: <original user query>
===========================================================

然后代理输出一个ReportPlan对象，其中包括：
1. 初始背景上下文的摘要（如果需要），基于网络搜索和/或爬取
2. 报告大纲，包括章节标题列表和每个章节要解决的关键问题
"""

from pydantic import BaseModel, Field
from typing import List
from .baseclass import ResearchAgent
from ..llm_client import reasoning_model, model_supports_structured_output
from .tool_agents.crawl_agent import crawl_agent
from .tool_agents.search_agent import search_agent
from .utils.parse_output import create_type_parser
from datetime import datetime
from ..utils.logging import TraceInfo  # 添加这个导入


class ReportPlanSection(BaseModel):
    """需要编写的报告章节"""
    title: str = Field(description="章节标题")
    key_question: str = Field(description="该章节需要解决的关键问题")


class ReportPlan(BaseModel):
    """报告规划代理的输出"""
    background_context: str = Field(description="可以传递给研究代理的支持性上下文摘要")
    report_outline: List[ReportPlanSection] = Field(description="报告中需要编写的章节列表")
    report_title: str = Field(description="报告标题")


INSTRUCTIONS = f"""
你是一位研究经理，管理着一个研究代理团队。今天的日期是{datetime.now().strftime("%Y-%m-%d")}。
给定一个研究查询，你的工作是生成报告的初始大纲（章节标题和关键问题），以及一些背景上下文。每个章节将分配给团队中的不同研究人员，他们将对该章节进行研究。

你将获得：
- 一个初始研究查询

你的任务是：
1. 通过运行网络搜索或爬取网站，生成1-2段关于查询的初始背景上下文（如果需要）
2. 生成报告大纲，包括章节标题列表和每个章节要解决的关键问题
3. 提供将用作主标题的报告标题

指南：
- 每个章节应涵盖一个独立于其他章节的单一主题/问题
- 每个章节的关键问题应包括名称和域名/网站（如果可用且适用），如果与公司、产品或类似内容相关
- 背景上下文不应超过2段
- 背景上下文应非常具体于查询，并包括与报告所有章节的研究人员相关的任何信息
- 背景上下文应仅从网络搜索或爬取结果中获取，而不是来自先验知识（即，仅当你调用工具时才应包含）
- 例如，如果查询是关于一家公司，背景上下文应包括该公司业务的一些基本信息
- 不要进行超过2次工具调用

仅输出JSON。遵循以下JSON模式。不要输出其他任何内容。我将使用Pydantic解析，因此仅输出有效的JSON：
{ReportPlan.model_json_schema()}
"""

selected_model = reasoning_model

planner_agent = ResearchAgent[TraceInfo](
        name="PlannerAgent",
        instructions=INSTRUCTIONS,
    tools=[
        search_agent.as_tool(
            tool_name="web_search",
            tool_description="使用此工具搜索与查询相关的网络信息 - 提供3-6个单词的查询作为输入"
        ),
        crawl_agent.as_tool(
            tool_name="crawl_website",
            tool_description="使用此工具爬取与查询相关的网站信息 - 提供起始URL作为输入"
        )
    ],
    model=selected_model,
    output_type=ReportPlan if model_supports_structured_output(selected_model) else None,
    output_parser=create_type_parser(ReportPlan) if not model_supports_structured_output(selected_model) else None
)