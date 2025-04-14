"""
Example usage of the DeepResearcher to produce a report.

See deep_output.txt for the console output from running this script, and deep_output.pdf for the final report
"""

import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from deep_researcher import DeepResearcher

manager = DeepResearcher(
    max_iterations=3,
    max_time_minutes=10,
    verbose=True,
    tracing=False
)

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

# 添加背景上下文
background_context = """
锦创书城基本信息：
- 成立时间和地点
- 主营业务和特色
- 目前的线下门店分布
- 主要目标用户群体
- 品牌定位和文化理念

研究重点：
- 关注2023年至今的传播数据
- 重点分析主流社交媒体平台的传播效果
- 包括用户评价、媒体报道和营销活动分析
- 特别关注其文化活动和读者社群运营
"""

report = asyncio.run(
    manager.run(
        query,
    )
)

print("\n=== Final Report ===")
print(report)

# 确保 sample_output 目录存在
output_dir = os.path.join(os.path.dirname(__file__), 'sample_output')
os.makedirs(output_dir, exist_ok=True)

# 生成输出文件名
output_file = os.path.join(output_dir, 'jinchuang_report.md')

# 将报告写入文件
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(report)

print(f"\n=== Final Report has been saved to: {output_file} ===")
print(report)