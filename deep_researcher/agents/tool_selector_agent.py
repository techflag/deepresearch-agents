"""
用于确定应使用哪些专业代理来解决知识差距的代理。

该代理接受以下格式的字符串作为输入：
===========================================================
ORIGINAL QUERY: <original user query>

KNOWLEDGE GAP TO ADDRESS: <knowledge gap that needs to be addressed>
===========================================================

然后代理：
1. 分析知识差距，确定哪些代理最适合解决它
2. 返回一个AgentSelectionPlan对象，其中包含AgentTask对象列表

可用的代理有：
- WebSearchAgent：用于广泛主题的一般网络搜索
- SiteCrawlerAgent：爬取特定网站的页面以检索有关它的信息
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from ..llm_client import fast_model, model_supports_structured_output
from datetime import datetime
from .baseclass import ResearchAgent
from .utils.parse_output import create_type_parser


class AgentTask(BaseModel):
    """特定代理解决知识差距的任务"""
    gap: Optional[str] = Field(description="正在解决的知识差距", default=None)
    agent: str = Field(description="要使用的代理名称")
    query: str = Field(description="代理的具体查询")
    entity_website: Optional[str] = Field(description="被研究实体的网站，如果已知", default=None)
    client_id: Optional[str] = Field(description="客户端标识符", default=None)


class AgentSelectionPlan(BaseModel):
    """用于知识差距的代理使用计划"""
    tasks: List[AgentTask] = Field(description="解决知识差距的代理任务列表")


INSTRUCTIONS = f"""
你是一个工具选择器，负责确定哪些专业代理应该解决研究项目中的知识差距。
今天的日期是{datetime.now().strftime("%Y-%m-%d")}。

你将获得：
1. 原始用户查询
2. 研究中确定的知识差距
3. 你在研究过程中迄今为止所做的任务、行动、发现和思考的完整历史

你的任务是决定：
1. 哪些专业代理最适合解决这个差距
2. 应该给代理什么具体查询（保持简短 - 3-6个词）

可用的专业代理：
- WebSearchAgent：用于广泛主题的一般网络搜索（可以用不同的查询多次调用）
- SiteCrawlerAgent：爬取特定网站的页面以检索有关它的信息 - 如果你想了解特定公司、实体或产品的信息，请使用此代理

指南：
- 在最终输出中最多同时调用3个代理
- 如果需要覆盖知识差距的全部范围，你可以列出多个具有不同查询的WebSearchAgent
- 对代理查询要具体且简洁（3-6个词）- 它们应该精确针对所需的信息
- 如果你知道正在研究的实体的网站或域名，始终将其包含在查询中
- 如果差距与任何代理的能力不明确匹配，默认使用WebSearchAgent
- 使用行动/工具调用的历史作为指导 - 如果之前的方法没有效果，尽量不要重复
 
仅输出JSON。遵循以下JSON模式。不要输出其他任何内容。我将使用Pydantic解析，因此仅输出有效的JSON：
{AgentSelectionPlan.model_json_schema()}
"""

selected_model = fast_model

tool_selector_agent = ResearchAgent(
    name="ToolSelectorAgent",
    instructions=INSTRUCTIONS,
    model=selected_model,
    output_type=AgentSelectionPlan if model_supports_structured_output(selected_model) else None,
    output_parser=create_type_parser(AgentSelectionPlan) if not model_supports_structured_output(selected_model) else None
)
