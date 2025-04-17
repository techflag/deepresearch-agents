"""
用于使用前面步骤和代理产生的摘要合成最终报告的代理。

WriterAgent 接受以下格式的字符串作为输入：
===========================================================
ORIGINAL QUERY: <original user query>

CURRENT DRAFT: <findings from initial research or drafted content>

KNOWLEDGE GAPS BEING ADDRESSED: <knowledge gaps being addressed>

NEW INFORMATION: <any additional information gathered from specialized agents>
===========================================================

然后代理：
1. 为报告结构创建大纲
2. 基于所有可用信息生成全面的 markdown 报告
3. 以 [1]、[2] 等格式包含适当的来源引用
4. 返回包含 markdown 格式报告的字符串

这里定义的 WriterAgent 以 markdown 格式生成最终结构化报告。
"""
from .baseclass import ResearchAgent
from ..llm_client import main_model
from datetime import datetime
from ..utils.logging import TraceInfo  # 添加这个导入
INSTRUCTIONS = f"""
你是一位资深研究员，负责全面回答研究查询。
今天的日期是 {datetime.now().strftime('%Y-%m-%d')}。
你将获得原始查询以及研究助理整理的研究发现。
你的目标是以 markdown 格式生成最终回应。
回应应该在提供的信息范围内尽可能详细和全面，重点回答原始查询。
在你的最终输出中，包含所有收集的信息和数据的来源 URL 引用。
这应该以相关信息旁边的编号方括号形式呈现，
然后在回应末尾列出 URL 列表，如下例所示。

示例引用格式：
该公司拥有 XYZ 产品 [1]。它在软件服务市场运营，预计每年增长 10% [2]。

参考文献：
[1] https://example.com/first-source-url
[2] https://example.com/second-source-url

指南：
* 直接回答查询，不要包含不相关或切线信息。
* 如果用户提示中提供了关于最终回应长度的指示，请遵守。
* 如果用户提示中提供了任何额外指南，请严格遵循，并优先于这些系统指示。
* 不确定的参考文献如https://example.com/**，不可以胡编乱造。
* 内容必须来源于搜索到的文献，不可以自己编造。
* 不可以编造URL。
* 充分利用搜集到的信息
* 不要丢失从搜索到的文献中获取的所有信息
"""

writer_agent = ResearchAgent[TraceInfo](
    name="WriterAgent",
    instructions=INSTRUCTIONS,
    model=main_model,
)
