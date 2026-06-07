import asyncio
from dataclasses import dataclass

import pytest

from app.models.ai import AIInteraction
from app.models.user import User
from app.services import llm
from app.services.llm import LLMServiceError, ensure_llm_available
from tests.db_helpers import run_with_test_db


@dataclass
class FakeSettings:
    llm_enabled: bool = True
    llm_api_key: str = "test-key"
    llm_daily_limit_per_user: int = 20
    llm_cooldown_seconds: int = 60


def test_ensure_llm_available_blocks_recent_request(monkeypatch):
    async def scenario(session):
        monkeypatch.setattr(llm, "get_settings", lambda: FakeSettings())
        user = User(steam_id="steam_llm_limit", display_name="LLM Limit Tester")
        session.add(user)
        await session.flush()
        session.add(
            AIInteraction(
                user_id=user.id,
                context_type="lesson",
                context_id=1,
                prompt_type="explain",
                prompt="test prompt",
                response="test response",
                provider="test",
                model="test-model",
            )
        )
        await session.flush()

        with pytest.raises(LLMServiceError, match="cooldown"):
            await ensure_llm_available(session, user)

    asyncio.run(run_with_test_db(scenario))


def test_ensure_llm_available_blocks_disabled_provider(monkeypatch):
    async def scenario(session):
        monkeypatch.setattr(
            llm, "get_settings", lambda: FakeSettings(llm_enabled=False)
        )
        user = User(steam_id="steam_llm_disabled", display_name="LLM Disabled Tester")
        session.add(user)
        await session.flush()

        with pytest.raises(LLMServiceError, match="disabled"):
            await ensure_llm_available(session, user)

    asyncio.run(run_with_test_db(scenario))


def test_ensure_llm_available_blocks_missing_key(monkeypatch):
    async def scenario(session):
        monkeypatch.setattr(llm, "get_settings", lambda: FakeSettings(llm_api_key=""))
        user = User(steam_id="steam_llm_no_key", display_name="LLM No Key Tester")
        session.add(user)
        await session.flush()

        with pytest.raises(LLMServiceError, match="API key"):
            await ensure_llm_available(session, user)

    asyncio.run(run_with_test_db(scenario))
