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

query = "锦创书城互联网传播分析 - 如何提高网站的曝光度和转化率？ - 如何优化网站的用户体验？"

report = asyncio.run(
    manager.run(
        query
    )
)

print("\n=== Final Report ===")
print(report)