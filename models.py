"""
Shared data contracts passed between agents via ADK session state.

Keeping these as explicit Pydantic models (rather than free-form dicts) means
every agent in the pipeline has a typed, validated contract for what it reads and writes.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    RECALL = "recall"  # "what is X"
    APPLIED = "applied"  # "use X to solve Y"
    CONCEPTUAL = "conceptual"  # "why does X work / what would happen if..."


class Subtopic(BaseModel):
    id: str
    title: str
    rationale: str = Field(
        description="Why this subtopic matters for understanding the parent topic."
    )
    prerequisite_ids: list[str] = Field(default_factory=list)


class CurriculumMap(BaseModel):
    topic: str
    subtopics: list[Subtopic]


class QuizQuestion(BaseModel):
    id: str
    subtopic_id: str
    difficulty: Difficulty
    question: str
    expected_answer_summary: str = Field(
        description="What a correct answer should contain, for grading reference."
    )


class Quiz(BaseModel):
    subtopic_id: str
    questions: list[QuizQuestion]


class GapType(str, Enum):
    MISSING_KNOWLEDGE = "missing_knowledge"  # didn't know it at all
    MISCONCEPTION = "misconception"  # confidently wrong
    SLIP = "slip"  # knew it, made an error
    NONE = "none"  # answered correctly


class AnswerEvaluation(BaseModel):
    question_id: str
    subtopic_id: str
    is_correct: bool
    gap_type: GapType
    explanation: str = Field(
        description="Short evaluator note on what was right/wrong and why."
    )


class SubtopicResult(BaseModel):
    subtopic_id: str
    title: str
    mastered: bool
    evaluations: list[AnswerEvaluation]


class Resource(BaseModel):
    subtopic_id: str
    source_type: str  # "pdf" | "blog" | "youtube" | "arxiv"
    title: str
    url: str
    relevance_note: str = Field(
        description="Why this resource targets the specific gap, not just the topic."
    )
    excerpt: Optional[str] = Field(
        default=None,
        description="Pulled excerpt / timestamp range / page range relevant to the gap.",
    )


class MasteryReport(BaseModel):
    topic: str
    subtopic_results: list[SubtopicResult]
    overall_mastery_pct: float
    remaining_gaps: list[str]
