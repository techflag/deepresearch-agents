"""
Agent used to evaluate the state of the research report (typically done in a loop) and identify knowledge gaps that still 
need to be addressed.

The Agent takes as input a string in the following format:
===========================================================
ORIGINAL QUERY: <original user query>

CURRENT DRAFT: <most recent draft of the research output>

PREVIOUS EVALUATION: <the KnowledgeGapOutput from the previous iteration>
===========================================================

The Agent then:
1. Carefully reviews the current draft and assesses its completeness in answering the original query
2. Identifies specific knowledge gaps that still exist and need to be filled
3. Returns a KnowledgeGapOutput object
"""

from pydantic import BaseModel, Field
from typing import List
from agents import Agent
from ..llm_client import fast_model


class KnowledgeGapOutput(BaseModel):
    """Output from the Knowledge Gap Agent"""
    research_complete: bool = Field(description="Whether the research and findings are complete enough to end the research loop")
    outstanding_gaps: List[str] = Field(description="List of knowledge gaps that still need to be addressed")


INSTRUCTIONS = """
You are a Research State Evaluator. Your job is to critically analyze the current state of a research report, 
identify what knowledge gaps still exist and determine the best next step to take.

You will be given:
1. The original user query
2. A summary of findings you've collected up until this point (which may be empty in the first iteration)
3. Any previous thinking you've done (which will be empty in the first iteration)

Your task is to:
1. Carefully review the current findings and assess their completeness in answering the original query
2. Determine if the draft is sufficiently complete to end the research loop
3. If not, identify up to 3 knowledge gaps that need to be addressed in sequence in order to continue with research - these should be relevant to the original query

Be specific in the gaps you identify and include relevant information as this will be passed onto another agent to process without additional context.
"""


knowledge_gap_agent = Agent(
    name="KnowledgeGapAgent",
    instructions=INSTRUCTIONS,
    model=fast_model,
    output_type=KnowledgeGapOutput,
)