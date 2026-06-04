from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai import AIInteraction
from app.models.course import Lesson
from app.models.user import User

LESSON_ACTIONS = {
    "explain": "Explain this lesson simply and briefly.",
    "summarize": "Summarize this lesson into concise bullet points.",
    "practice": "Create 3 short practice questions based on this lesson. Include answers.",
    "next_step": "Give exactly one tiny next step the learner should do now.",
}

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
