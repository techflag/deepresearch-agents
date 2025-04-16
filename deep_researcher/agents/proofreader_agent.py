"""
用于根据每个部分的初始草稿生成报告最终草稿的代理。

该代理接受原始用户查询和ReportDraft.model_dump_json()类型的字符串化对象（如下定义）作为输入。

====
QUERY:
{query}

REPORT DRAFT:
{report_draft}
====

然后代理输出报告的最终markdown。
"""

from pydantic import BaseModel, Field
from typing import List
from .baseclass import ResearchAgent
from ..llm_client import fast_model
from datetime import datetime
from ..utils.logging import TraceInfo  # 添加这个导入

class ReportDraftSection(BaseModel):
    """A section of the report that needs to be written"""
    section_title: str = Field(description="The title of the section")
    section_content: str = Field(description="The content of the section")


class ReportDraft(BaseModel):
    """Output from the Report Planner Agent"""
    sections: List[ReportDraftSection] = Field(description="List of sections that are in the report")


INSTRUCTIONS = f"""
你是一位研究专家，负责校对和编辑研究报告。
今天的日期是{datetime.now().strftime("%Y-%m-%d")}。

你获得的内容：
1. 报告的原始查询主题
2. ReportDraft格式的报告初稿，按顺序包含每个部分

你的任务是：
1. **合并部分：** 将各部分连接成单个字符串
2. **添加部分标题：** 以markdown格式将部分标题添加到每个部分的开头，以及报告的主标题
3. **去重：** 删除各部分之间的重复内容，避免重复
4. **删除不相关部分：** 如果任何部分或子部分与查询完全无关，请删除它们
5. **改进措辞：** 编辑报告的措辞，使其精炼、简洁有力，但**不要删除任何细节**或大块文本
6. **添加摘要：** 在报告开头添加简短的报告摘要/大纲，提供各部分的概述和讨论内容
7. **保留来源：** 保留所有来源/参考文献 - 将长参考文献列表移至报告末尾
8. **更新参考编号：** 继续在报告主体中包含方括号中的参考编号（[1]、[2]、[3]等），但更新编号以匹配报告末尾的新参考顺序
9. **输出最终报告：** 以markdown格式输出最终报告（不要将其包装在代码块中）

指南：
- 不要向报告添加任何新事实或数据
- 除非内容明显错误、矛盾或不相关，否则不要从报告中删除任何内容
- 删除或重新格式化任何多余或过多的标题，并确保最终标题级别的嵌套正确
- 确保最终报告流畅且结构合理
- 包括最终报告中存在的所有来源和参考文献
"""

    
proofreader_agent = ResearchAgent[TraceInfo](
    name="ProofreaderAgent",
    instructions=INSTRUCTIONS,
    model=fast_model
)