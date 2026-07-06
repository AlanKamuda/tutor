"""
Main orchestration for the Knowledge Gap Tutor.
"""

from __future__ import annotations

import os
import sys
import re
import time
from google.genai.errors import ClientError

from dotenv import load_dotenv
load_dotenv()

from tutor.agents.curriculum_mapper import curriculum_mapper_agent
from tutor.agents.quiz_generator import quiz_generator_agent
from tutor.agents.evaluator import evaluator_agent
from tutor.agents.gap_analyzer import gap_analyzer_agent, parse_gap_query
from tutor.agents.resource_finder import resource_finder_agent
from tutor.agents.curator import curator_agent
from tutor.config import (
    MASTERY_THRESHOLD,
    MAX_RETRIES_PER_SUBTOPIC,
    MIN_QUESTIONS_FOR_MASTERY,
    QUESTIONS_PER_SUBTOPIC,
    get_google_api_key,
)
from tutor.models import (
    AnswerEvaluation,
    CurriculumMap,
    GapType,
    MasteryReport,
    Quiz,
    Resource,
    Subtopic,
    SubtopicResult,
)

import asyncio
import threading
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

_APP_NAME = "knowledge-gap-tutor"
_USER_ID = "learner"

def run_agent(agent, state: dict, max_retries: int = 4) -> dict:
    """Run an ADK agent for one turn, injecting `state` into session state,
    and return the resulting session.state dict.

    Retries on 429 RESOURCE_EXHAUSTED (free-tier rate limit), backing off
    for whatever `retryDelay` Google's API tells us to wait, plus a small
    buffer. This wraps EVERY agent call site (curriculum mapper, quiz
    generator, evaluator, gap analyzer, resource finder, curator) since
    they all go through this one function.
    """
    for attempt in range(max_retries + 1):
        try:
            return _run_agent_threaded(agent, state)
        except ClientError as e:
            is_rate_limit = getattr(e, "code", None) == 429
            if is_rate_limit and attempt < max_retries:
                delay = _extract_retry_delay(e) or 20
                print(f"   ⏳ Rate limited — waiting {delay}s and retrying ({attempt + 1}/{max_retries})...")
                time.sleep(delay + 2)  # small buffer on top of Google's suggested delay
                continue
            raise


def _extract_retry_delay(e: ClientError) -> int | None:
    match = re.search(r"retryDelay':\s*'(\d+)s'", str(e))
    return int(match.group(1)) if match else None


def _run_agent_threaded(agent, state: dict) -> dict:
    """The actual thread-wrapped single attempt (your existing logic, just
    pulled into its own function so run_agent can retry it cleanly)."""
    result_box: dict = {}
    error_box: dict = {}

    def _runner():
        try:
            result_box["value"] = asyncio.run(_run_agent_async(agent, state))
        except Exception as exc:
            error_box["error"] = exc

    thread = threading.Thread(target=_runner)
    thread.start()
    thread.join()

    if "error" in error_box:
        raise error_box["error"]
    return result_box["value"]

async def _run_agent_async(agent, state: dict) -> dict:
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=_APP_NAME, user_id=_USER_ID)
    runner = Runner(agent=agent, app_name=_APP_NAME, session_service=session_service)
    async for _event in runner.run_async(
        user_id=_USER_ID,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text="go")]),
        state_delta=state,
    ):
        pass
    final_session = await session_service.get_session(
        app_name=_APP_NAME, user_id=_USER_ID, session_id=session.id
    )
    return final_session.state
    
# import asyncio
# from google.adk.runners import Runner
# from google.adk.sessions import InMemorySessionService
# from google.genai import types

# _APP_NAME = "knowledge-gap-tutor"
# _USER_ID = "learner"


# def run_agent(agent, state: dict) -> dict:
#     """Run an ADK agent for one turn, injecting `state` into session state,
#     and return the resulting session.state dict -- so existing
#     `result.get("output_key")` calls keep working unchanged."""
#     return asyncio.run(_run_agent_async(agent, state))


# async def _run_agent_async(agent, state: dict) -> dict:
#     session_service = InMemorySessionService()
#     session = await session_service.create_session(app_name=_APP_NAME, user_id=_USER_ID)
#     runner = Runner(agent=agent, app_name=_APP_NAME, session_service=session_service)
#     async for _event in runner.run_async(
#         user_id=_USER_ID,
#         session_id=session.id,
#         new_message=types.Content(role="user", parts=[types.Part(text="go")]),
#         state_delta=state,
#     ):
#         pass
#     final_session = await session_service.get_session(
#         app_name=_APP_NAME, user_id=_USER_ID, session_id=session.id
#     )
#     return final_session.state


# ─── Setup API key ──────────────────────────────────────────────────────────
os.environ["GOOGLE_API_KEY"] = get_google_api_key()


# ─── Agent Invocation Helpers ───────────────────────────────────────────────────
def build_curriculum(topic: str) -> CurriculumMap:
    """Step 1: Break topic into subtopics."""
    print(f"\n📚 Building curriculum map for: {topic}")
    
    # Call the agent with state dict
    #result = curriculum_mapper_agent.run(state={"topic": topic})
    result = run_agent(curriculum_mapper_agent, {"topic": topic})


    # Extract the output using the output_key
    curriculum_data = result.get("curriculum_map")
    curriculum = CurriculumMap(**curriculum_data)
    
    print(f"   ✓ Found {len(curriculum.subtopics)} subtopics")
    for st in curriculum.subtopics:
        prereqs = f" (requires: {', '.join(st.prerequisite_ids)})" if st.prerequisite_ids else ""
        print(f"     - {st.title}{prereqs}")
    return curriculum


def generate_quiz_for_subtopic(subtopic: Subtopic) -> Quiz:
    """Step 2a: Generate quiz for one subtopic."""
    print(f"\n🧪 Generating quiz for: {subtopic.title}")
    
    # result = quiz_generator_agent.run(state={
    #     "subtopic": subtopic.model_dump_json(),
    #     "subtopic_id": subtopic.id,
    #     "num_questions": QUESTIONS_PER_SUBTOPIC,
    # })
    
    result = run_agent(quiz_generator_agent, {
        "subtopic": subtopic.model_dump_json(),
        "subtopic_id": subtopic.id,
        "num_questions": QUESTIONS_PER_SUBTOPIC,
    })

    quiz_data = result.get("quiz")
    quiz = Quiz(**quiz_data)
    print(f"   ✓ Created {len(quiz.questions)} questions")
    return quiz


def collect_answers(quiz: Quiz) -> dict[str, str]:
    """Step 2b: Present quiz to human, collect answers."""
    answers = {}
    print(f"\n📝 Quiz time! ({len(quiz.questions)} questions)\n")
    for i, q in enumerate(quiz.questions, 1):
        print(f"Q{i} [{q.difficulty.value}]: {q.question}")
        answer = input("Your answer: ").strip()
        answers[q.id] = answer
        print()
    return answers


def evaluate_answers(quiz: Quiz, answers: dict[str, str]) -> list[AnswerEvaluation]:
    """Step 2c: Grade answers and classify gaps."""
    print("\n⚖️  Evaluating your answers...")
    evaluations = []
    
    for q in quiz.questions:
        learner_answer = answers.get(q.id, "")
        
        # result = evaluator_agent.run(state={
        #     "question": q.question,
        #     "expected_answer_summary": q.expected_answer_summary,
        #     "learner_answer": learner_answer,
        #     "question_id": q.id,
        #     "subtopic_id": q.subtopic_id,
        # })
        result = run_agent(evaluator_agent, {
            "question": q.question,
            "expected_answer_summary": q.expected_answer_summary,
            "learner_answer": learner_answer,
            "question_id": q.id,
            "subtopic_id": q.subtopic_id,
        })

        eval_data = result.get("evaluation")
        evaluation = AnswerEvaluation(**eval_data)
        evaluations.append(evaluation)
        
        status = "✓" if evaluation.is_correct else "✗"
        print(f"   {status} Q: {q.question[:60]}...")
        if not evaluation.is_correct:
            print(f"      Gap type: {evaluation.gap_type.value}")
        print(f"      {evaluation.explanation}")
    
    return evaluations


def check_mastery(evaluations: list[AnswerEvaluation]) -> bool:
    """Determine if learner passed this subtopic."""
    correct = sum(1 for e in evaluations if e.is_correct)
    total = len(evaluations)
    pct = correct / total if total > 0 else 0
    passed = correct >= MIN_QUESTIONS_FOR_MASTERY and pct >= MASTERY_THRESHOLD
    
    print(f"\n📊 Score: {correct}/{total} ({pct:.0%}) – {'MASTERED ✓' if passed else 'needs review ✗'}")
    return passed


def find_and_curate_resources(evaluations: list[AnswerEvaluation], subtopic: Subtopic) -> list[Resource]:
    """Steps 2d-g: Analyze gaps → find resources → curate best ones."""
    failed = [e for e in evaluations if not e.is_correct and e.gap_type != GapType.NONE]
    if not failed:
        return []
    
    print(f"\n🔍 Analyzing {len(failed)} gap(s)...")
    
    # Step 2d: GapAnalyzer
    failed_json = "\n".join(
        f"- Q: {e.explanation} (gap type: {e.gap_type.value})"
        for e in failed
    )
    
    #result = gap_analyzer_agent.run(state={"failed_evaluations": failed_json})
    result = run_agent(gap_analyzer_agent, {"failed_evaluations": failed_json})

    gap_query_raw = result.get("gap_query_raw", "")
    gap_query = parse_gap_query(gap_query_raw)
    
    print(f"   Gap query: {gap_query['query']}")
    print(f"   Preferred source: {gap_query['preferred_source']}")
    
    # Step 2e: ResourceFinder
    print("\n🌐 Searching for resources...")
    
    try:
        #rf_result = resource_finder_agent.run(state={"gap_query": str(gap_query)})
        rf_result = run_agent(resource_finder_agent, {"gap_query": str(gap_query)})

        candidates_raw = rf_result.get("candidate_resources", "")
    except Exception as e:
        print(f"   ⚠️ Resource finder error: {e}")
        return []
    
    print(f"   Found candidates")
    
    # Step 2f: Curator
    print("\n📚 Curating best resources...")
    
    try:
        # curator_result = curator_agent.run(state={
        #     "candidate_resources": candidates_raw,
        #     "gap_query": gap_query['query'],
        # })
        curator_result = run_agent(curator_agent, {
            "candidate_resources": candidates_raw,
            "gap_query": gap_query["query"],
        })

        curated_data = curator_result.get("curated_resources", [])
        resources = [Resource(**r) if isinstance(r, dict) else r for r in curated_data]
    except Exception as e:
        print(f"   ⚠️ Curator error: {e}")
        return []
    
    print(f"   ✓ Selected {len(resources)} resource(s):")
    for r in resources:
        print(f"     [{r.source_type}] {r.title}")
        print(f"       {r.url}")
        print(f"       → {r.relevance_note}")
        if r.excerpt:
            print(f"       Excerpt: {r.excerpt[:100]}...")
    
    return resources


def study_subtopic(subtopic: Subtopic) -> SubtopicResult:
    """The full loop for one subtopic."""
    attempt = 0
    all_evaluations = []
    
    while attempt < MAX_RETRIES_PER_SUBTOPIC:
        attempt += 1
        print(f"\n{'─' * 60}")
        print(f"📖 Subtopic: {subtopic.title} (attempt {attempt}/{MAX_RETRIES_PER_SUBTOPIC})")
        print(f"{'─' * 60}")
        
        quiz = generate_quiz_for_subtopic(subtopic)
        answers = collect_answers(quiz)
        evaluations = evaluate_answers(quiz, answers)
        all_evaluations.extend(evaluations)
        
        if check_mastery(evaluations):
            return SubtopicResult(
                subtopic_id=subtopic.id,
                title=subtopic.title,
                mastered=True,
                evaluations=all_evaluations,
            )
        
        if attempt < MAX_RETRIES_PER_SUBTOPIC:
            resources = find_and_curate_resources(evaluations, subtopic)
            if resources:
                print("\n📖 Study the resources above, then we'll re-quiz.")
                input("Press Enter when ready to continue...")
            else:
                print("\n⚠️  No additional resources found; moving to re-quiz.")
    
    print(f"\n⚠️  Max retries reached for '{subtopic.title}' – marking for review.")
    return SubtopicResult(
        subtopic_id=subtopic.id,
        title=subtopic.title,
        mastered=False,
        evaluations=all_evaluations,
    )


def topological_sort(subtopics: list[Subtopic]) -> list[Subtopic]:
    """Order subtopics so prerequisites come first."""
    remaining = {st.id: st for st in subtopics}
    completed = set()
    ordered = []
    
    while remaining:
        ready = [
            st for st in remaining.values()
            if all(prereq in completed for prereq in st.prerequisite_ids)
        ]
        
        if not ready:
            ready = [next(iter(remaining.values()))]
        
        for st in ready:
            ordered.append(st)
            completed.add(st.id)
            del remaining[st.id]
    
    return ordered


def run_tutor(topic: str) -> MasteryReport:
    """Main entry point: orchestrates the full pipeline."""
    print(f"\n{'═' * 60}")
    print(f"🎓 Knowledge Gap Tutor")
    print(f"{'═' * 60}")
    
    # Step 1: Build curriculum
    curriculum = build_curriculum(topic)
    
    # Step 2: Study subtopics in prerequisite order
    ordered_subtopics = topological_sort(curriculum.subtopics)
    results = []
    
    for subtopic in ordered_subtopics:
        result = study_subtopic(subtopic)
        results.append(result)
    
    # Step 3: Final report
    mastered_count = sum(1 for r in results if r.mastered)
    overall_pct = mastered_count / len(results) if results else 0
    
    remaining_gaps = [
        r.title for r in results if not r.mastered
    ]
    
    report = MasteryReport(
        topic=topic,
        subtopic_results=results,
        overall_mastery_pct=overall_pct,
        remaining_gaps=remaining_gaps,
    )
    
    print(f"\n{'═' * 60}")
    print(f"📊 FINAL REPORT")
    print(f"{'═' * 60}")
    print(f"Topic: {topic}")
    print(f"Overall Mastery: {overall_pct:.0%} ({mastered_count}/{len(results)} subtopics)")
    
    if remaining_gaps:
        print("\n⚠️  Topics needing more review:")
        for gap in remaining_gaps:
            print(f"   - {gap}")
    else:
        print("\n🎉 All subtopics mastered!")
    
    return report


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m tutor.main <topic>")
        print('Example: python -m tutor.main "backpropagation in neural networks"')
        sys.exit(1)
    
    topic = " ".join(sys.argv[1:])
    run_tutor(topic)


if __name__ == "__main__":
    main()
