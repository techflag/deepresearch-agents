import asyncio
import argparse
from .iterative_research import IterativeResearcher
from .deep_research import DeepResearcher
from typing import Literal
from dotenv import load_dotenv

load_dotenv(override=True)


async def main() -> None:
    parser = argparse.ArgumentParser(description="深度研究助手")
    parser.add_argument("--query", type=str, help="研究查询")
    parser.add_argument("--model", type=str, choices=["deep", "simple"], 
                        help="研究模式（深度或简单）", default="deep")
    parser.add_argument("--max-iterations", type=int, default=5,
                       help="深度研究的最大迭代次数")
    parser.add_argument("--max-time", type=int, default=10,
                       help="深度研究的最大时间（分钟）")
    parser.add_argument("--output-length", type=str, default="5 pages",
                       help="报告的期望输出长度")
    parser.add_argument("--output-instructions", type=str, default="",
                       help="报告的额外指示")
    parser.add_argument("--verbose", action="store_true",
                       help="向控制台打印状态更新")
    parser.add_argument("--tracing", action="store_true",
                       help="为研究启用跟踪（仅对OpenAI模型有效）")
    
    args = parser.parse_args()
    
    # 如果通过命令行未提供查询，则提示用户
    query = args.query if args.query else input("您想研究什么？ ")
    
    print(f"开始对以下内容进行深度研究：{query}")
    print(f"最大迭代次数：{args.max_iterations}，最大时间：{args.max_time} 分钟")
    
    if args.model == "deep":
        manager = DeepResearcher(
            max_iterations=args.max_iterations,
            max_time_minutes=args.max_time,
            verbose=args.verbose,
            tracing=args.tracing
        )
        report = await manager.run(query)
    else:
        manager = IterativeResearcher(
            max_iterations=args.max_iterations,
            max_time_minutes=args.max_time,
            verbose=args.verbose,
            tracing=args.tracing
        )
        report = await manager.run(
            query, 
            output_length=args.output_length, 
            output_instructions=args.output_instructions
        )

    print("\n=== 最终报告 ===")
    print(report)

# 命令行入口点
def cli_entry():
    """命令行界面的入口点。"""
    asyncio.run(main())

if __name__ == "__main__":
    cli_entry()
