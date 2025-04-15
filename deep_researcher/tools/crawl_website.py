from typing import List, Set, Union
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import aiohttp
from .web_search import scrape_urls, ssl_context, ScrapeResult, WebpageSnippet
from agents import function_tool
from ..utils.message_parser import MessageParser
from ..sse_manager import SSEManager


@function_tool
async def crawl_website(starting_url: str) -> Union[List[ScrapeResult], str]:
    """爬取网站页面，从starting_url开始，然后深入到从那里链接的页面。
    优先考虑在页眉/导航中找到的链接，然后是正文链接，然后是后续页面。
    
    参数：
        starting_url: 要爬取的起始URL
        
    返回：
        ScrapeResult对象列表，具有以下字段：
            - url: 网页的URL
            - title: 网页的标题
            - description: 网页的描述
            - text: 网页的文本内容
    """
    if not starting_url:
        return "提供了空URL"

    # 确保URL有协议
    if not starting_url.startswith(('http://', 'https://')):
        starting_url = 'http://' + starting_url

    max_pages = 10
    base_domain = urlparse(starting_url).netloc
    
    async def extract_links(html: str, current_url: str) -> tuple[List[str], List[str]]:
        """从HTML内容中提取优先级链接"""
        soup = BeautifulSoup(html, 'html.parser')
        nav_links = set()
        body_links = set()
        
        # 查找导航/页眉链接
        for nav_element in soup.find_all(['nav', 'header']):
            for a in nav_element.find_all('a', href=True):
                link = urljoin(current_url, a['href'])
                if urlparse(link).netloc == base_domain:
                    _log_message(f"发现导航链接: {link}")
                    nav_links.add(link)
        
        # 查找剩余的正文链接
        for a in soup.find_all('a', href=True):
            link = urljoin(current_url, a['href'])
            if urlparse(link).netloc == base_domain and link not in nav_links:
                await _log_message(f"<scrape>发现正文链接: {link}</scrape>")
                body_links.add(link)
                
        return list(nav_links), list(body_links)

    async def fetch_page(url: str) -> str:
        """从URL获取HTML内容"""
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        await _log_message(f"<scrape>从URL获取HTML内容:{response.text()}</scrape>")
                        return await response.text()
            except Exception as e:
                print(f"获取{url}时出错: {str(e)}")
                return "获取页面时出错"

    # 使用起始URL初始化
    queue: List[str] = [starting_url]
    next_level_queue: List[str] = []
    all_pages_to_scrape: Set[str] = set([starting_url])
    
    # 广度优先爬取
    while queue and len(all_pages_to_scrape) < max_pages:
        current_url = queue.pop(0)
        
        # 获取并处理页面
        html_content = await fetch_page(current_url)
        if html_content:
            nav_links, body_links = await extract_links(html_content, current_url)
            
            # 将未访问的导航链接添加到当前队列（更高优先级）
            remaining_slots = max_pages - len(all_pages_to_scrape)
            for link in nav_links:
                link = link.rstrip('/')
                if link not in all_pages_to_scrape and remaining_slots > 0:
                    queue.append(link)
                    all_pages_to_scrape.add(link)
                    remaining_slots -= 1
            
            # 将未访问的正文链接添加到下一级队列（较低优先级）
            for link in body_links:
                link = link.rstrip('/')
                if link not in all_pages_to_scrape and remaining_slots > 0:
                    next_level_queue.append(link)
                    all_pages_to_scrape.add(link)
                    remaining_slots -= 1
        
        # 如果当前队列为空，添加下一级链接
        if not queue:
            queue = next_level_queue
            next_level_queue = []
    
    # 将集合转换为列表进行最终处理
    pages_to_scrape = list(all_pages_to_scrape)[:max_pages]
    pages_to_scrape = [WebpageSnippet(url=page, title="", description="") for page in pages_to_scrape]
    
    # 使用scrape_urls获取所有发现页面的内容
    result = await scrape_urls(pages_to_scrape)
    return result

async def _log_message(message: str, client_id: str = "default") -> None:
    try:
        print(message)
        
        sse_data = MessageParser.format_sse_data(message, client_id)
        await SSEManager.publish(
            client_id, 
            sse_data["event"], 
            sse_data["data"]
        )
    except Exception as e:
        print(f"SSE发送失败: {str(e)}")