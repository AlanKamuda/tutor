"""
Curriculum Mapper Agent.

Takes a single topic string (e.g., "backpropagation in neural networks") and
returns a CurriculumMap: an ordered DAG of subtopics with prerequisite relationships.

This agent is the entry point to the pipeline – it defines the learning path.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from tutor.config import MODEL_NAME
from tutor.models import CurriculumMap

CURRICULUM_MAPPER_INSTRUCTION = """
You are building a learning curriculum for the topic:
{topic}

Break this topic into 3-5 SUBTOPICS that cover the core ideas from foundational to advanced.
Each subtopic should:
  - Have a clear, specific title (not just "Introduction" or "Advanced Topics")
  - Include a short rationale explaining why it matters for understanding the parent topic
  - List prerequisite_ids: other subtopic IDs that should be mastered BEFORE this one
    (use empty list [] if it's a foundational subtopic with no prerequisites)

Output a CurriculumMap object matching the provided schema.

Example for "gradient descent":
{{
  "topic": "gradient descent",
  "subtopics": [
    {{
      "id": "derivatives_basics",
      "title": "Derivatives and directional slope",
      "rationale": "Gradient descent is based on following the derivative downhill.",
      "prerequisite_ids": []
    }},
    {{
      "id": "loss_functions",
      "title": "Loss functions and optimization goals",
      "rationale": "You need to know WHAT you're minimizing before you can descend.",
      "prerequisite_ids": []
    }},
    {{
      "id": "gradient_descent_algorithm",
      "title": "The gradient descent update rule",
      "rationale": "The core iterative formula: θ_new = θ_old - α·∇L.",
      "prerequisite_ids": ["derivatives_basics", "loss_functions"]
    }},
    {{
      "id": "learning_rate_tuning",
      "title": "Learning rate and convergence",
      "rationale": "Understanding how α affects convergence speed and stability.",
      "prerequisite_ids": ["gradient_descent_algorithm"]
    }}
  ]
}}

Now do the same for the given topic.
"""

curriculum_mapper_agent = LlmAgent(
    name="CurriculumMapper",
    model=MODEL_NAME,
    description="Breaks a topic into an ordered curriculum of subtopics with prerequisites.",
    instruction=CURRICULUM_MAPPER_INSTRUCTION,
    output_schema=CurriculumMap,
    output_key="curriculum_map",
)