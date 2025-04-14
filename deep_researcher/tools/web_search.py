import json
import os
import ssl
import aiohttp
import asyncio
from agents import function_tool
from ..agents.baseclass import ResearchAgent, ResearchRunner
from ..agents.utils.parse_output import create_type_parser
from typing import List, Union, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from ..llm_client import fast_model, model_supports_structured_output
from ..sse_manager import SSEManager

load_dotenv()
CONTENT_LENGTH_LIMIT = 10000  # 将爬取的内容修剪到此长度，以避免大型上下文/令牌限制问题
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "serper").lower()

# ------- 定义类型 -------

class ScrapeResult(BaseModel):
    url: str = Field(description="网页的URL")
    text: str = Field(description="网页的完整文本内容")
    title: str = Field(description="网页的标题")
    description: str = Field(description="网页的简短描述")


class WebpageSnippet(BaseModel):
    url: str = Field(description="网页的URL")
    title: str = Field(description="网页的标题")
    description: Optional[str] = Field(description="网页的简短描述")

class SearchResults(BaseModel):
    results_list: List[WebpageSnippet]

# ------- 定义工具 -------

# 添加一个模块级变量来存储单例实例
_serper_client = None


@function_tool
async def web_search(query: str ,client_id: str = "default") -> Union[List[ScrapeResult], str]:
    """对给定查询执行网络搜索，并获取URL及其标题、描述和文本内容。
    
    参数：
        query: 搜索查询
        
    返回：
        ScrapeResult对象列表，具有以下字段：
            - url: 搜索结果的URL
            - title: 搜索结果的标题
            - description: 搜索结果的描述
            - text: 搜索结果的完整文本内容
    """
    # 仅当搜索提供商为serper时使用SerperClient
    if SEARCH_PROVIDER == "openai":
        # 对于OpenAI搜索提供商，不应直接调用此函数
        # 将使用agents模块中的WebSearchTool
        return f"当SEARCH_PROVIDER设置为'openai'时，不使用web_search函数。请检查您的配置。"
    else:
        try:
            # SerperClient的延迟初始化
            global _serper_client
            _log_message(f"执行web_search搜索:{query}")
            if _serper_client is None:
                _serper_client = SerperClient(client_id=client_id)

            search_results = await _serper_client.search(query, filter_for_relevance=True, max_results=5)
            results = await scrape_urls(search_results)
            return results
        except Exception as e:
            # 返回用户友好的错误消息
            return f"抱歉，搜索时遇到错误：{str(e)}"


# ------- 定义用于按相关性过滤搜索结果的代理 -------

FILTER_AGENT_INSTRUCTIONS = f"""
你是一个搜索结果过滤器。你的任务是分析SERP搜索结果列表，并根据链接、标题和摘要确定哪些与原始查询相关。
仅以指定格式返回相关结果。

- 删除任何引用与查询实体名称相似但不相同的实体的结果。
- 例如，如果查询询问公司"Amce Inc, acme.com"，删除链接中包含"acmesolutions.com"或"acme.net"的结果。

仅输出JSON。遵循以下JSON模式。不要输出其他任何内容。我将使用Pydantic解析，因此仅输出有效的JSON：
{SearchResults.model_json_schema()}
"""

selected_model = fast_model

filter_agent = ResearchAgent(
    name="SearchFilterAgent",
    instructions=FILTER_AGENT_INSTRUCTIONS,
    model=selected_model,
    output_type=SearchResults if model_supports_structured_output(selected_model) else None,
    output_parser=create_type_parser(SearchResults) if not model_supports_structured_output(selected_model) else None
)

# ------- 定义底层工具逻辑 -------

# 创建共享连接器
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')  # 添加此行以允许较旧的密码套件


class SerperClient:
    """Serper API的客户端，用于执行Google搜索。"""

    def __init__(self, api_key: str = None, client_id: str = "default"):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.client_id = client_id
        if not self.api_key:
            raise ValueError("未提供API密钥。设置SERPER_API_KEY环境变量。")
        
        self.url = "https://api.bochaai.com/v1/web-search"
        self.headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json"
        }

        _log_message(f"SerperClient初始化完成:{self.headers}")

    async def search(self, query: str, filter_for_relevance: bool = True, max_results: int = 5) -> List[WebpageSnippet]:
        """使用Serper API执行Google搜索并获取顶部结果的基本详细信息。
        
        参数：
            query: 搜索查询
            num_results: 返回的最大结果数（最多10个）
            
        返回：
            包含搜索结果的字典
        """
        _log_message(f"执行search搜索：{query}")
        _log_message(f"<search> 执行搜索：{query}</search>",self.client_id)
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                self.url,
                headers=self.headers,
                json={"query": query, "summary": True}
            ) as response:
                response.raise_for_status()
                results = await response.json()
                results_list = [
                    WebpageSnippet(
                        url=result.get('url', ''),
                        title=result.get('name', ''),
                        description=result.get('snippet', '')
                    )
                    for result in results["data"]["webPages"]["value"]
                ]
                
        if not results_list:
            return []
            
        if not filter_for_relevance:
            return results_list[:max_results]
            
        return await self._filter_results(results_list, query, max_results=max_results)

    async def _filter_results(self, results: List[WebpageSnippet], query: str, max_results: int = 5) -> List[WebpageSnippet]:
        serialized_results = [result.model_dump() if isinstance(result, WebpageSnippet) else result for result in results]
        
        user_prompt = f"""
        原始搜索查询: {query}
        
        要分析的搜索结果:
        {json.dumps(serialized_results, indent=2)}
        
        返回{max_results}个或更少的搜索结果。
        """
        _log_message(f"<filter>\n过滤搜索结果：{user_prompt}\n</filter>",self.client_id)
        try:
            result = await ResearchRunner.run(filter_agent, user_prompt)
            output = result.final_output_as(SearchResults)
            return output.results_list
        except Exception as e:
            print("过滤结果时出错:", str(e))
            return results[:max_results]


async def scrape_urls(items: List[WebpageSnippet]) -> List[ScrapeResult]:
    """从提供的URL获取文本内容。
    
    参数：
        items: 要提取内容的SearchEngineResult项目列表
        
    返回：
        ScrapeResult对象列表，具有以下字段：
            - url: 搜索结果的URL
            - title: 搜索结果的标题
            - description: 搜索结果的描述
            - text: 搜索结果的完整文本内容
    """
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        # 创建任务列表以进行并发执行
        tasks = []
        for item in items:
            if item.url:  # 跳过空URL
                tasks.append(fetch_and_process_url(session, item))
                
        # 并发执行所有任务并收集结果
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉错误并返回成功的结果
        return [r for r in results if isinstance(r, ScrapeResult)]


async def fetch_and_process_url(session: aiohttp.ClientSession, item: WebpageSnippet) -> ScrapeResult:
    """获取和处理单个URL的辅助函数。"""

    if not is_valid_url(item.url):
        return ScrapeResult(
            url=item.url,
            title=item.title,
            description=item.description,
            text=f"获取内容时出错：URL包含受限文件扩展名"
        )

    try:
        async with session.get(item.url, timeout=8) as response:
            if response.status == 200:
                content = await response.text()
                # 在线程池中运行html_to_text以避免阻塞
                text_content = await asyncio.get_event_loop().run_in_executor(
                    None, html_to_text, content
                )
                text_content = text_content[:CONTENT_LENGTH_LIMIT]  # 修剪内容以避免超过令牌限制
                return ScrapeResult(
                    url=item.url,
                    title=item.title,
                    description=item.description,
                    text=text_content
                )
            else:
                # 不抛出异常，而是返回带有错误消息的WebSearchResult
                return ScrapeResult(
                    url=item.url,
                    title=item.title,
                    description=item.description,
                    text=f"获取内容时出错：HTTP {response.status}"
                )
    except Exception as e:
        # 不抛出异常，而是返回带有错误消息的WebSearchResult
        return ScrapeResult(
            url=item.url,
            title=item.title,
            description=item.description,
            text=f"获取内容时出错：{str(e)}"
        )


def html_to_text(html_content: str) -> str:
    """
    从HTML上下文中剥离所有不必要的元素，为文本提取/LLM处理做准备。
    """
    # 使用lxml解析HTML以提高速度
    soup = BeautifulSoup(html_content, 'lxml')

    # 从相关标签中提取文本
    tags_to_extract = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote')

    # 使用生成器表达式以提高效率
    extracted_text = "\n".join(element.get_text(strip=True) for element in soup.find_all(tags_to_extract) if element.get_text(strip=True))

    return extracted_text


def is_valid_url(url: str) -> bool:
    """检查URL是否不包含受限文件扩展名。"""
    if any(ext in url for ext in [
        ".pdf", 
        ".doc", 
        ".xls",
        ".ppt",
        ".zip",
        ".rar",
        ".7z",
        ".txt", 
        ".js", 
        ".xml", 
        ".css", 
        ".png", 
        ".jpg", 
        ".jpeg", 
        ".gif", 
        ".ico", 
        ".svg", 
        ".webp", 
        ".mp3", 
        ".mp4", 
        ".avi", 
        ".mov", 
        ".wmv", 
        ".flv", 
        ".wma", 
        ".wav", 
        ".m4a", 
        ".m4v", 
        ".m4b", 
        ".m4p", 
        ".m4u"
    ]):
        return False
    return True

def _log_message(message: str, client_id: str = "default") -> None:
    """增强日志功能，支持结构化消息和SSE发送
    
    参数:
        message: 日志消息，支持以下格式:
            - <search>内容</search>
            - <filter>内容</filter>
            - <scrape>内容</scrape>
            - <error>内容</error>
            - 普通文本消息
        client_id: SSE客户端ID
    """
    try:
        # 尝试直接打印
        print(message)
        
        # 解析不同类型的消息
        if message.startswith("<search>"):
            event_type = "search"
            content = message[8:-9]  # 移除<search>和</search>
        elif message.startswith("<filter>"):
            event_type = "filter"
            content = message[8:-9]  # 移除<filter>和</filter>
        elif message.startswith("<scrape>"):
            event_type = "scrape"
            content = message[8:-9]  # 移除<scrape>和</scrape>
        elif message.startswith("<error>"):
            event_type = "error"
            content = message[7:-8]  # 移除<error>和</error>
        else:
            event_type = "info"
            content = message

        # 通过SSE发送结构化消息
        try:
            # 由于_log_message不是异步函数，这里直接调用SSEManager.publish而不使用await
            SSEManager.publish(client_id, event_type, {
                "content": content,
                "timestamp": time.time(),
                "raw_message": message
            })
        except Exception as e:
            print(f"SSE发送失败: {str(e)}")
            
    except UnicodeEncodeError:
        # 如果遇到编码错误，使用repr转义Unicode字符
        print(repr(message))