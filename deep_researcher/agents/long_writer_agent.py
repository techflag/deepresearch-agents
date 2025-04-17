"""
用于通过迭代编写报告的每个部分来合成最终报告的代理。
用于根据每个部分的草稿生成长篇报告。

LongWriterAgent接受以下格式的字符串作为输入：
===========================================================
ORIGINAL QUERY: <original user query>

CURRENT REPORT DRAFT: <current working draft of the report, all sections up to the current one being written>

TITLE OF NEXT SECTION TO WRITE: <title of the next section of the report to be written>

DRAFT OF NEXT SECTION: <draft of the next section of the report>
===========================================================

然后代理：
1. 阅读当前草稿和下一部分的草稿
2. 编写报告的下一部分
3. 生成更新后的新部分草稿以适应报告的流程
4. 返回更新后的新部分草稿以及参考文献/引用
"""
from .baseclass import ResearchAgent, ResearchRunner
from ..llm_client import fast_model, model_supports_structured_output
from .utils.parse_output import create_type_parser
from datetime import datetime
from pydantic import BaseModel, Field
from .proofreader_agent import ReportDraft
from typing import List, Tuple, Dict
import re
from ..utils.logging import TraceInfo  # 添加这个导入

class LongWriterOutput(BaseModel):
    next_section_markdown: str = Field(description="下一部分的最终草稿，采用markdown格式")
    references: List[str] = Field(description="该部分的URL列表及其对应的参考编号")


INSTRUCTIONS = f"""
你是一位专家报告撰写者，负责迭代编写报告的每个部分。
今天的日期是{datetime.now().strftime('%Y-%m-%d')}。
你将获得：
1. 原始研究查询
3. 包含目录和所有已编写部分的报告最终草稿（在第一次迭代中尚未编写任何部分）
3. 报告下一部分的初稿

目标：
1. 编写报告下一部分的最终草稿，在报告正文中使用方括号中的编号引用
2. 生成要附加到报告末尾的参考文献列表

引用/参考文献：
引用应按数字顺序排列，在报告正文中使用编号方括号编写。
单独地，所有URL及其对应的参考编号将包含在报告末尾。
请按照以下示例进行格式化。

LongWriterOutput(
    next_section_markdown="该公司专注于IT咨询 [1](https://example.com/first-source-url)。它在软件服务市场运营，预计每年增长10% [2](https://example.com/second-source-url)。",
    references=["[1] https://example.com/first-source-url", "[2] https://example.com/second-source-url"]
)

指南：
- 你可以重新格式化和重组部分内容和标题的流程以使其逻辑流畅，但不要删除初稿中包含的细节
- 仅当文本已在报告前面提到，或根据目录应在后面部分中涵盖时，才从初稿中删除文本
- 确保部分标题与目录匹配
- 将最终输出和参考部分格式化为markdown
- 不要为参考部分包含标题，只需列出编号的参考文献
* 不确定的参考文献如https://example.com/**，不可以胡编乱造。
* 内容必须来源于搜索到的文献，不可以自己编造。
* 不可以编造URL。
* 充分利用搜集到的信息，不要胡编乱造。
仅输出JSON。遵循以下JSON模式。不要输出其他任何内容。我将使用Pydantic解析，因此仅输出有效的JSON：
{LongWriterOutput.model_json_schema()}
"""

selected_model = fast_model

long_writer_agent = ResearchAgent[TraceInfo](
    name="LongWriterAgent",
    instructions=INSTRUCTIONS,
    model=selected_model,
    output_type=LongWriterOutput if model_supports_structured_output(selected_model) else None,
    output_parser=create_type_parser(LongWriterOutput) if not model_supports_structured_output(selected_model) else None
)


async def write_next_section(
    original_query: str,
    report_draft: str,
    next_section_title: str,
    next_section_draft: str,
) -> LongWriterOutput:
    """编写报告的下一部分"""

    user_message = f"""
    <ORIGINAL QUERY>
    {original_query}
    </ORIGINAL QUERY>

    <CURRENT REPORT DRAFT>
    {report_draft or "尚无草稿"}
    </CURRENT REPORT DRAFT>

    <TITLE OF NEXT SECTION TO WRITE>
    {next_section_title}
    </TITLE OF NEXT SECTION TO WRITE>

    <DRAFT OF NEXT SECTION>
    {next_section_draft}
    </DRAFT OF NEXT SECTION>
    """

    result = await ResearchRunner.run(
        long_writer_agent,
        user_message,
    )

    return result.final_output_as(LongWriterOutput)


async def write_report(
    original_query: str,
    report_title: str,
    report_draft: ReportDraft,
) -> str:
    """通过迭代编写每个部分来编写最终报告"""

    # 使用标题和目录初始化报告的最终草稿
    final_draft = f"# {report_title}\n\n" + "## 目录\n\n" + "\n".join([f"{i+1}. {section.section_title}" for i, section in enumerate(report_draft.sections)]) + "\n\n"
    all_references = []

    for section in report_draft.sections:
        # 生成每个部分的最终草稿，并将其与相应的参考文献一起添加到报告中
        next_section_draft = await write_next_section(original_query, final_draft, section.section_title, section.section_content)
        section_markdown, all_references = reformat_references(
            next_section_draft.next_section_markdown,
            next_section_draft.references,
            all_references
        )
        section_markdown = reformat_section_headings(section_markdown)
        final_draft += section_markdown + '\n\n'

    # 将最终参考文献添加到报告末尾
    final_draft += '## 参考文献：\n\n' + '  \n'.join(all_references)
    return final_draft


def reformat_references(
        section_markdown: str,
        section_references: List[str],
        all_references: List[str]
    ) -> Tuple[str, List[str]]:
    """
    此方法优雅地处理引用的重新编号、去重和重新格式化，随着新部分添加到报告草稿中。
    它接受以下输入：
    1. 包含方括号内内联引用的新部分的markdown内容，例如 [1], [2]
    2. 新部分的引用列表，例如 ["[1] https://example1.com", "[2] https://example2.com"]
    3. 涵盖报告所有先前部分的引用列表

    它返回：
    1. 更新后的新部分的markdown内容，其中引用已重新编号和去重，使其从先前的引用递增
    2. 更新后的完整报告的引用列表，包括新部分的引用
    """
    def convert_ref_list_to_map(ref_list: List[str]) -> Dict[str, str]:
        ref_map = {}
        for ref in ref_list:
            try:
                ref_num = int(ref.split(']')[0].strip('['))
                url = ref.split(']', 1)[1].strip()
                ref_map[url] = ref_num
            except ValueError:
                print(f"无效的引用格式: {ref}")
                continue
        return ref_map

    section_ref_map = convert_ref_list_to_map(section_references)
    report_ref_map = convert_ref_list_to_map(all_references)
    section_to_report_ref_map = {}

    report_urls = set(report_ref_map.keys())
    ref_count = max(report_ref_map.values() or [0])
    for url, section_ref_num in section_ref_map.items():
        if url in report_urls:
            section_to_report_ref_map[section_ref_num] = report_ref_map[url]
        else:
            # 如果引用不在报告中，将其添加到报告中
            ref_count += 1
            section_to_report_ref_map[section_ref_num] = ref_count
            all_references.append(f"[{ref_count}] {url}")

    def replace_reference(match):
        # 从匹配中提取引用编号
        ref_num = int(match.group(1))
        # 查找新的引用编号
        mapped_ref_num = section_to_report_ref_map.get(ref_num)
        if mapped_ref_num:
            return f'[{mapped_ref_num}]'
        return ''

    # 使用替换函数一次性替换所有引用
    section_markdown = re.sub(r'\[(\d+)\]', replace_reference, section_markdown)

    return section_markdown, all_references


def reformat_section_headings(section_markdown: str) -> str:
    """
    重新格式化部分的标题，使其与报告一致，将部分的标题重新设置为二级标题

    例如，这个：
    # 大标题
    一些内容
    ## 子部分

    变成这个：
    ## 大标题
    一些内容
    ### 子部分
    """
    # 如果部分为空，按原样返回
    
    if not section_markdown.strip():
        return section_markdown

    # 查找第一个标题级别
    first_heading_match = re.search(r'^(#+)\s', section_markdown, re.MULTILINE)
    if not first_heading_match:
        return section_markdown

    # 计算需要的级别调整
    first_heading_level = len(first_heading_match.group(1))
    level_adjustment = 2 - first_heading_level

    def adjust_heading_level(match):
        hashes = match.group(1)
        content = match.group(2)
        new_level = max(2, len(hashes) + level_adjustment)
        return '#' * new_level + ' ' + content

    # 一次性对所有标题应用标题调整
    return re.sub(r'^(#+)\s(.+)$', adjust_heading_level, section_markdown, flags=re.MULTILINE)
