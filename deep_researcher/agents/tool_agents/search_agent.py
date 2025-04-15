"""
用于执行网络搜索并总结结果的代理。

SearchAgent 接受 AgentTask.model_dump_json() 格式的字符串作为输入，或者可以接受简单的查询字符串作为输入

然后代理：
1. 使用 web_search 工具检索搜索结果
2. 分析检索到的信息
3. 编写搜索结果的 3+ 段落摘要
4. 在信息来源旁边的括号中包含引用/URL
5. 返回格式化的摘要作为字符串

该代理可以使用 OpenAI 的内置网络搜索功能或基于环境配置的自定义
网络搜索实现。
"""

from agents import WebSearchTool
from ...tools.web_search import web_search, SEARCH_PROVIDER
from ...llm_client import fast_model, model_supports_structured_output, get_base_url
from . import ToolAgentOutput
from ..baseclass import ResearchAgent
from ..utils.parse_output import create_type_parser

"""
entity_website 是一个可选参数，用于指定特定网站域名来限制搜索范围。例如：

1. 如果你想搜索特定公司或组织的官方信息，可以提供其官方网站域名
2. 搜索示例：
   - 如果 query = "人工智能发展"，entity_website = "microsoft.com"
   - 生成的搜索词会变成类似 "人工智能发展 site:microsoft.com"
   - 这样搜索结果就会限制在 microsoft.com 这个域名下
这个功能主要用于：

- 确保搜索结果来自可信的官方来源
- 在特定网站内搜索相关信息
- 避免获取到不相关网站的信息
在代码中，这个参数是通过 `AgentTask` 模型传入的，搜索代理会根据是否提供了这个参数来调整搜索策略。"""

INSTRUCTIONS = f"""你是一位专门从网络检索和总结信息的研究助手。

目标：
给定一个 AgentTask，按照以下步骤操作：
- 将"query"转换为优化的 Google SERP 搜索词，限制为 3-5 个词
- 如果提供了"entity_website"，确保在优化的 Google 搜索词中包含域名
- 将优化的搜索词输入 web_search 工具
- 使用 web_search 工具后，编写一个 3+ 段落的摘要，捕捉搜索结果的主要要点

指南：
- 在你的摘要中，尝试全面回答/解决提供的"gap"（这是搜索的目标）
- 摘要应始终引用详细的事实、数据和数字（如果有）
- 如果搜索结果与搜索词无关或不解决"gap"，只需写"未找到相关结果"
- 如果需要，使用标题和项目符号组织摘要
- 在你的摘要中，在所有相关信息旁边的括号中包含引用/URL
- 不要进行额外的搜索

仅输出 JSON。遵循以下 JSON 模式。不要输出其他任何内容。我将使用 Pydantic 解析，因此仅输出有效的 JSON：
{ToolAgentOutput.model_json_schema()}
"""

selected_model = fast_model
provider_base_url = get_base_url(selected_model)

if SEARCH_PROVIDER == "openai" and 'openai.com' not in provider_base_url:
    raise ValueError(f"你已将 SEARCH_PROVIDER 设置为 'openai'，但正在使用的模型 {str(selected_model.model)} 不是 OpenAI 模型")
elif SEARCH_PROVIDER == "openai":
    web_search_tool = WebSearchTool()
else:
    web_search_tool = web_search

search_agent = ResearchAgent(
    name="WebSearchAgent",
    instructions=INSTRUCTIONS,
    tools=[web_search_tool],
    model=selected_model,
    output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
    output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None,
)