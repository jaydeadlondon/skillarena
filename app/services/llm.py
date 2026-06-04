import json
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai import AIInteraction
from app.models.course import Lesson
from app.models.pvp import PvpQuestion
from app.models.user import User

LESSON_ACTIONS = {
    "explain": "Explain this lesson simply and briefly.",
    "summarize": "Summarize this lesson into concise bullet points.",
    "practice": "Create 3 short practice questions based on this lesson. Include answers.",
    "next_step": "Give exactly one tiny next step the learner should do now.",
}

VALID_QUIZ_OPTIONS = {"A", "B", "C", "D"}

PROVIDER_DEFAULTS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "meta/llama-3.1-8b-instruct",
    },
}


class LLMServiceError(RuntimeError):
    pass


def normalize_llm_base_url(provider: str, base_url: str) -> str:
    """Normalize provider base URL to the OpenAI-compatible API root.

    Expected final form examples:
    - Groq: https://api.groq.com/openai/v1
    - NVIDIA NIM: https://integrate.api.nvidia.com/v1

    Users sometimes paste a provider root URL or the full /chat/completions URL;
    this helper normalizes both cases.
    """
    base_url = base_url.strip().rstrip("/")
    if base_url.endswith("/chat/completions"):
        base_url = base_url[: -len("/chat/completions")]

    if provider == "groq" and base_url == "https://api.groq.com":
        return "https://api.groq.com/openai/v1"
    if provider == "nvidia" and base_url == "https://integrate.api.nvidia.com":
        return "https://integrate.api.nvidia.com/v1"
    return base_url


def get_llm_config() -> tuple[str, str, str]:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["groq"])
    base_url = normalize_llm_base_url(
        provider, settings.llm_base_url or defaults["base_url"]
    )
    model = settings.llm_model or defaults["model"]
    return provider, base_url, model


async def user_llm_requests_today(db: AsyncSession, user: User) -> int:
    today = datetime.now(UTC).date()
    count = await db.scalar(
        select(func.count(AIInteraction.id)).where(
            AIInteraction.user_id == user.id,
            func.date(AIInteraction.created_at) == today,
        )
    )
    return int(count or 0)


async def ensure_llm_available(db: AsyncSession, user: User) -> None:
    settings = get_settings()
    if not settings.llm_enabled:
        raise LLMServiceError(
            "AI assistant is disabled. Enable LLM_ENABLED in environment settings."
        )
    if not settings.llm_api_key or settings.llm_api_key.startswith("put-"):
        raise LLMServiceError("AI assistant API key is not configured.")
    used = await user_llm_requests_today(db, user)
    if used >= settings.llm_daily_limit_per_user:
        raise LLMServiceError("Daily AI request limit reached. Try again tomorrow.")


def compact_json_from_text(text: str) -> Any:
    """Extract JSON from plain text or fenced markdown returned by an LLM."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    if not text.startswith("["):
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            text = match.group(0)
    return json.loads(text)


def lesson_system_prompt() -> str:
    return (
        "You are SkillArena's AI Study Companion. "
        "Be concise, practical, and direct. "
        "Use simple language. Avoid long lectures. "
        "Be ADHD-aware: break things into small steps and reduce overwhelm. "
        "Do not provide medical, legal, or unsafe advice. "
        "If the lesson content is insufficient, say what is missing and still help with what is available."
    )


def build_lesson_prompt(
    lesson: Lesson, action: str, custom_prompt: str | None = None
) -> str:
    action_instruction = LESSON_ACTIONS.get(action, LESSON_ACTIONS["explain"])
    if custom_prompt:
        action_instruction = f"User request: {custom_prompt[:700]}"
    return (
        f"Task: {action_instruction}\n\n"
        f"Course: {lesson.course.title if lesson.course else 'Unknown'}\n"
        f"Lesson title: {lesson.title}\n"
        f"Lesson objective/content:\n{lesson.content[:2500]}\n\n"
        "Answer in English. Keep the answer short and useful."
    )


async def call_openai_compatible_chat(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()
    provider, base_url, model = get_llm_config()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 700,
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    endpoint = f"{base_url}/chat/completions"
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
    if response.status_code >= 400:
        error_detail = response.text[:500]
        raise LLMServiceError(
            f"AI provider error: {response.status_code}. Endpoint: {endpoint}. Details: {error_detail}"
        )
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMServiceError("AI provider returned an unexpected response.") from exc


async def ask_lesson_companion(
    db: AsyncSession,
    user: User,
    lesson: Lesson,
    action: str,
    custom_prompt: str | None = None,
) -> AIInteraction:
    await ensure_llm_available(db, user)
    provider, _, model = get_llm_config()
    prompt = build_lesson_prompt(lesson, action, custom_prompt)
    try:
        response = await call_openai_compatible_chat(lesson_system_prompt(), prompt)
    except (httpx.HTTPError, LLMServiceError) as exc:
        raise LLMServiceError(str(exc)) from exc

    interaction = AIInteraction(
        user_id=user.id,
        context_type="lesson",
        context_id=lesson.id,
        prompt_type=action,
        prompt=prompt,
        response=response,
        provider=provider,
        model=model,
    )
    db.add(interaction)
    return interaction


def quiz_generator_system_prompt() -> str:
    return (
        "You generate quiz questions for SkillArena PvP battles. "
        "Return only valid JSON. No markdown, no explanation. "
        "Each question must be clear, factual, and answerable from the provided lesson text. "
        "Avoid trick questions and avoid unsafe content."
    )


def build_quiz_generation_prompt(lesson: Lesson, count: int, difficulty: int) -> str:
    count = max(1, min(int(count), 10))
    difficulty = max(1, min(int(difficulty), 3))
    return (
        f"Generate {count} multiple-choice quiz questions.\n"
        f"Difficulty: {difficulty}/3.\n\n"
        "Return JSON array only. Each item must have exactly these keys:\n"
        "question, option_a, option_b, option_c, option_d, correct_option.\n"
        "correct_option must be one of: A, B, C, D.\n\n"
        f"Course: {lesson.course.title if lesson.course else 'Unknown'}\n"
        f"Lesson title: {lesson.title}\n"
        f"Lesson content:\n{lesson.content[:3500]}\n"
    )


def validate_generated_quiz_items(items: Any, max_count: int) -> list[dict[str, str]]:
    if not isinstance(items, list):
        raise LLMServiceError("AI did not return a JSON array.")
    validated: list[dict[str, str]] = []
    for item in items[:max_count]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()[:1000]
        option_a = str(item.get("option_a", "")).strip()[:255]
        option_b = str(item.get("option_b", "")).strip()[:255]
        option_c = str(item.get("option_c", "")).strip()[:255]
        option_d = str(item.get("option_d", "")).strip()[:255]
        correct_option = str(item.get("correct_option", "")).strip().upper()[:1]
        if not question or not option_a or not option_b or not option_c or not option_d:
            continue
        if correct_option not in VALID_QUIZ_OPTIONS:
            continue
        validated.append(
            {
                "question": question,
                "option_a": option_a,
                "option_b": option_b,
                "option_c": option_c,
                "option_d": option_d,
                "correct_option": correct_option,
            }
        )
    if not validated:
        raise LLMServiceError("AI did not return valid quiz questions.")
    return validated


async def generate_quiz_questions_for_lesson(
    db: AsyncSession,
    user: User,
    lesson: Lesson,
    count: int,
    difficulty: int,
) -> tuple[list[PvpQuestion], AIInteraction]:
    await ensure_llm_available(db, user)
    provider, _, model = get_llm_config()
    count = max(1, min(int(count), 10))
    difficulty = max(1, min(int(difficulty), 3))
    prompt = build_quiz_generation_prompt(lesson, count, difficulty)
    raw_response = await call_openai_compatible_chat(
        quiz_generator_system_prompt(), prompt
    )
    try:
        parsed = compact_json_from_text(raw_response)
    except json.JSONDecodeError as exc:
        raise LLMServiceError("AI returned invalid JSON. Try again.") from exc
    items = validate_generated_quiz_items(parsed, count)

    questions: list[PvpQuestion] = []
    for item in items:
        question = PvpQuestion(
            course_id=lesson.course_id, difficulty=difficulty, is_active=True, **item
        )
        db.add(question)
        questions.append(question)

    interaction = AIInteraction(
        user_id=user.id,
        context_type="lesson",
        context_id=lesson.id,
        prompt_type="quiz_generator",
        prompt=prompt,
        response=raw_response,
        provider=provider,
        model=model,
    )
    db.add(interaction)
    return questions, interaction


async def recent_lesson_interactions(
    db: AsyncSession, user: User, lesson_id: int, limit: int = 8
) -> list[AIInteraction]:
    return (
        (
            await db.execute(
                select(AIInteraction)
                .where(
                    AIInteraction.user_id == user.id,
                    AIInteraction.context_type == "lesson",
                    AIInteraction.context_id == lesson_id,
                )
                .order_by(AIInteraction.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
