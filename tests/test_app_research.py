import asyncio
import os
import sys
import subprocess

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from deep_researcher.utils.logging import TraceInfo  # 添加 TraceInfo 导入
# 检查并安装缺失的依赖
try:
    import agents
except ModuleNotFoundError:
    print("正在安装缺失的 agents 模块...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "agents"])
    import agents

from deep_researcher import DeepResearcher

async def test_start_research():
    # 测试数据 - 使用固定client_id
    query = """
请分析锦创书城在互联网上的传播情况，重点关注：
1. 各大社交媒体平台（如微博、小红书、抖音）的传播效果
2. 线上营销活动的形式和成效
3. 用户口碑和评价分析
4. 与其他实体书店的线上传播对比
5. 近一年来的传播趋势变化

分析维度：
- 传播渠道和方式
- 用户互动和参与度
- 内容策略效果
- 品牌形象塑造
- 营销活动效果
"""
    client_id = "7777777777777777777777"  # 固定测试ID

    researcher = DeepResearcher(
        max_iterations=3,
        max_time_minutes=10,
        verbose=True,
        tracing=False
    )
    
    # 注意：run方法已经接收client_id参数，不需要再次传递
    trace_info= TraceInfo(trace_id=client_id)
    report = await researcher.run(query,trace_info)
    print("\n=== Final Report ===")
    print(report)

if __name__ == "__main__":
    asyncio.run(test_start_research())
    