"""
Quiz Generator Agent.

Given a single Subtopic, generates a short diagnostic quiz (3 questions by default)
with a mix of recall, applied, and conceptual difficulties.

The quiz is designed to probe for gaps, not to be comprehensive – we're looking
for "do you actually understand this subtopic" signals, not memorization.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from tutor.config import MODEL_NAME, QUESTIONS_PER_SUBTOPIC
from tutor.models import Quiz

QUIZ_GENERATOR_INSTRUCTION = """
You are generating a diagnostic quiz for this subtopic:
{subtopic}

Create exactly {num_questions} questions that probe understanding at different levels:
  1. RECALL: factual knowledge ("What is X?", "List the steps of Y")
  2. APPLIED: use the concept to solve a problem ("Given X, compute Y", "Apply Z to scenario W")
  3. CONCEPTUAL: deeper reasoning ("Why does X work?", "What would happen if we changed Y?")

Each question should have:
  - A clear question string (suitable for a learner to answer in 1-3 sentences)
  - An expected_answer_summary: what a correct answer should contain, for grading reference
    (this is NOT shown to the learner, only used by the Evaluator agent)

Output a Quiz object matching the provided schema.
The subtopic_id should be "{subtopic_id}".
"""

quiz_generator_agent = LlmAgent(
    name="QuizGenerator",
    model=MODEL_NAME,
    description="Creates a short diagnostic quiz for a subtopic, mixed difficulty.",
    instruction=QUIZ_GENERATOR_INSTRUCTION,
    output_schema=Quiz,
    output_key="quiz",
)
