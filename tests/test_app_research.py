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

分析锦创书城在互联网上的传播情况，重点关注以下内容：

1、各大社交媒体平台（如微博、小红书、抖音）的传播效果，通过用户视角的关键词搜索获取相关帖子内容，排除无法获取的数据（如粉丝数量、浏览量）。
2、线上营销活动的形式、内容及用户反馈。
3、用户口碑和评价的整体趋势与情感倾向。
4、与其他实体书店（如钟书阁、西西弗书店）的线上传播策略和效果对比。
5、不包含无法获取的数据，如购买人数、销售额等。

关键词要求：

1、采用用户视角的搜索关键词，贴近日常用语，如“锦创书城 怎么样”“锦创书城 打卡”，避免专业术语（如“锦创书城 社交媒体 传播效果”）。
2、建议关键词示例（可扩展）：锦创书城 怎么样、好不好、体验、推荐、环境、活动、打卡、服务、书籍、种草。
分析维度：
1、传播渠道和方式：锦创书城在各平台的内容形式（如图文、短视频、直播）及传播特点。
2、用户互动和参与度：帖子下的点赞、评论、转发等互动情况，反映用户参与程度。
3、内容策略效果：不同内容类型（如环境分享、活动宣传、书籍推荐）的吸引力和传播效果。
4、品牌形象塑造：通过用户评价和内容呈现，分析锦创书城的品牌形象（如文艺、亲民、独特）。
5、营销活动效果：线上活动的类型（如签售会、折扣促销、读书会）、用户参与情况及反馈。
输出要求：
1、基于公开可获取的社交媒体数据，提供定性分析，辅以具体案例（如典型帖子或活动）。
2、对比分析时，列举其他实体书店的具体线上传播案例，突出差异和优劣。
3、报告中避免猜测或包含无法验证的数据，保持客观性。
4、如数据不足，说明局限性并建议进一步调研方向，但是保留章节以便后期人工协助。
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
    try:
        asyncio.run(test_start_research())
    except Exception as e:
        import traceback
        with open('global_error.log', 'a', encoding='utf-8') as f:
            f.write(traceback.format_exc())
        raise
    