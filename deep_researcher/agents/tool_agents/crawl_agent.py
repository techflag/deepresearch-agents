"""
用于爬取网站并返回结果的代理。

SearchAgent 接受 AgentTask.model_dump_json() 格式的字符串作为输入，或者可以接受简单的起始 url 字符串作为输入

然后代理：
1. 使用 crawl_website 工具爬取网站
2. 编写爬取内容的 3+ 段落摘要
3. 在信息来源旁边的括号中包含引用/URL
4. 返回格式化的摘要作为字符串
"""

from ...tools import crawl_website
from . import ToolAgentOutput
from ...llm_client import fast_model, model_supports_structured_output
from ..baseclass import ResearchAgent
from ..utils.parse_output import create_type_parser


INSTRUCTIONS = f"""
你是一个网站爬取代理，爬取网站内容并根据爬取的内容回答查询。请严格按照以下步骤操作：

* 从提供的信息中，使用 'entity_website' 作为网络爬虫的 starting_url
* 使用 crawl_website 工具爬取网站
* 使用 crawl_website 工具后，编写一个 3+ 段落的摘要，捕捉爬取内容的主要要点
* 在你的摘要中，尝试全面回答/解决提供的 'gaps' 和 'query'（如果有）
* 如果爬取的内容与 'gaps' 或 'query' 无关，只需写 "未找到相关结果"
* 如果需要，使用标题和项目符号组织摘要
* 在你的摘要中，在所有相关信息旁边的括号中包含引用/URL
* 只运行爬虫一次

仅输出 JSON。遵循以下 JSON 模式。不要输出其他任何内容。我将使用 Pydantic 解析，因此仅输出有效的 JSON：
{ToolAgentOutput.model_json_schema()}
"""

selected_model = fast_model

crawl_agent = ResearchAgent(
    name="SiteCrawlerAgent",
    instructions=INSTRUCTIONS,
    tools=[crawl_website],
    model=selected_model,
    output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
    output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
)
