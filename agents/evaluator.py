"""
Evaluator Agent.

Grades a learner's answers to quiz questions and classifies the type of gap.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from tutor.config import MODEL_NAME
from tutor.models import AnswerEvaluation

EVALUATOR_INSTRUCTION = """
You are grading a learner's answer to this question:

Question: {question}
Expected answer should contain: {expected_answer_summary}
Learner's answer: {learner_answer}

Determine:
  1. is_correct: bool (did they demonstrate understanding, even if wording differs?)
  2. gap_type: one of:
       - "none" if correct
       - "missing_knowledge" if they clearly didn't know the concept
       - "misconception" if they were confident but wrong
       - "slip" if they knew the concept but made an error
  3. explanation: a 1-2 sentence note on what was right/wrong

Be generous with partial credit.

Output an AnswerEvaluation object matching the provided schema.
The question_id is "{question_id}" and subtopic_id is "{subtopic_id}".
"""

evaluator_agent = LlmAgent(
    name="Evaluator",
    model=MODEL_NAME,
    description="Grades quiz answers and classifies gap types.",
    instruction=EVALUATOR_INSTRUCTION,
    output_schema=AnswerEvaluation,
    output_key="evaluation",
)
