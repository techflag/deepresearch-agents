import asyncio
import os
import sys
# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from deep_researcher import DeepResearcher

def test_start_research():
    # 测试数据 - 使用固定client_id
    test_data = {
        "query": "测试研究查询",
        "max_iterations": 3,
        "max_time_minutes": 10
    }
    fixed_client_id = "666666666666666666666666"  # 固定测试ID

    manager = DeepResearcher(
        max_iterations=3,
        max_time_minutes=10,
        verbose=True,
        tracing=False,
        client_id=fixed_client_id
    )
    
    # 修正query变量名
    report = asyncio.run(
        manager.run(
            query=test_data["query"],  # 使用test_data中的query
        )
    )
    print("\n=== Final Report ===")
    print(report)

if __name__ == "__main__":
    asyncio.run(test_start_research())
    