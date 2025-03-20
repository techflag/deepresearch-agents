"""
Example usage of the DeepResearcher to produce a report.

See deep_output.txt for the console output from running this script, and deep_output.pdf for the final report
"""

import asyncio
from app.deep_research import DeepResearcher

manager = DeepResearcher(
    max_iterations=3,
    max_time_minutes=10,
    verbose=True
)

query = "Write a report on Plato - who was he, what were his main works " \
        "and what are the main philosophical ideas he's known for"

report = asyncio.run(
    manager.run(
        query
    )
)

print("\n=== Final Report ===")
print(report)