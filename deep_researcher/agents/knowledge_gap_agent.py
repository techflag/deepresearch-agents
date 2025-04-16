"""
用于评估研究报告状态（通常在循环中完成）并识别仍需解决的知识差距的代理。

该代理接受以下格式的字符串作为输入：
===========================================================
ORIGINAL QUERY: <original user query>

CURRENT DRAFT: <most recent draft of the research output>

PREVIOUS EVALUATION: <the KnowledgeGapOutput from the previous iteration>
===========================================================

然后代理：
1. 仔细审查当前草稿并评估其在回答原始查询方面的完整性
2. 确定仍然存在并需要填补的特定知识差距
3. 返回一个KnowledgeGapOutput对象
"""

from pydantic import BaseModel, Field
from typing import List
from .baseclass import ResearchAgent
from ..llm_client import fast_model, model_supports_structured_output
from datetime import datetime
from .utils.parse_output import create_type_parser
from ..utils.logging import TraceInfo  # 添加这个导入
class KnowledgeGapOutput(BaseModel):
    research_complete: bool = Field(..., description="研究是否足够完整以结束循环")  # 添加...表示必填
    outstanding_gaps: List[str] = Field(default_factory=list, description="待解决的知识差距列表")  # 添加默认值


INSTRUCTIONS = f"""
你是一位研究状态评估员。今天的日期是{datetime.now().strftime("%Y-%m-%d")}。
你的工作是批判性地分析研究报告的当前状态，识别仍然存在的知识差距，并确定采取的最佳下一步。

你将获得：
1. 原始用户查询以及与查询相关的任何支持背景上下文
2. 你在研究过程中迄今为止所做的任务、行动、发现和思考的完整历史（在第一次迭代中，这将为空）

你的任务是：
1. 仔细审查发现和思考，特别是最新迭代的内容，并评估其在回答原始查询方面的完整性
2. 确定发现是否足够完整以结束研究循环
3. 如果不是，确定需要按顺序解决的最多3个知识差距，以继续研究 - 这些应与原始查询相关

在你确定的差距中要具体，并包括相关信息，因为这将传递给另一个代理处理，而不需要额外的上下文。

仅输出JSON并遵循以下JSON模式。不要输出其他任何内容。我将使用Pydantic解析，因此仅输出有效的JSON：
{KnowledgeGapOutput.model_json_schema()}


必须包含以下字段：
- research_complete: 布尔值，明确指示研究是否完成
- outstanding_gaps: 字符串列表，最多3个具体知识差距

示例输出格式：
{{
    "research_complete": false,
    "outstanding_gaps": ["差距1的具体描述", "差距2的具体描述"]
}}
"""

selected_model = fast_model

knowledge_gap_agent = ResearchAgent[TraceInfo](
    name="KnowledgeGapAgent",
    instructions=INSTRUCTIONS,
    model=selected_model,
    output_type=KnowledgeGapOutput if model_supports_structured_output(selected_model) else None,
    output_parser=create_type_parser(KnowledgeGapOutput) if not model_supports_structured_output(selected_model) else None
)
