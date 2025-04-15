import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from deep_researcher.iterative_research import IterativeResearcher

async def test_iterative_researcher():
    # 使用一个固定的测试 client_id
    researcher = IterativeResearcher(
        max_iterations=1,  # 设置为1以加快测试速度
        max_time_minutes=5,  # 设置较短的超时时间
        verbose=True,
        client_id="test_client_123"  # 使用固定的测试ID
    )
    
    # 使用一个简单的查询
    query = "什么是人工智能"
    
    print(f"开始测试，使用 client_id: test_client_123")
    result = await researcher.run(query=query)
    
    print("\n=== 测试完成 ===")
    print(f"查询: {query}")
    print(f"结果长度: {len(result) if result else 0} 字符")

if __name__ == "__main__":
    asyncio.run(test_iterative_researcher())