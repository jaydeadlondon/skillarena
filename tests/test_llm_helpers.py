import pytest

from app.services.llm import (
    LLMServiceError,
    compact_json_from_text,
    normalize_llm_base_url,
    validate_generated_quest_items,
    validate_generated_quiz_items,
)


def test_normalize_groq_root_url():
    assert (
        normalize_llm_base_url("groq", "https://api.groq.com")
        == "https://api.groq.com/openai/v1"
    )


def test_normalize_full_chat_completions_url():
    assert (
        normalize_llm_base_url(
            "groq", "https://api.groq.com/openai/v1/chat/completions"
        )
        == "https://api.groq.com/openai/v1"
    )


def test_compact_json_from_fenced_markdown():
    data = compact_json_from_text('```json\n[{"a": 1}]\n```')
    assert data == [{"a": 1}]


def test_validate_generated_quiz_items():
    items = [
        {
            "question": "What is SkillArena?",
            "option_a": "A game",
            "option_b": "A learning platform",
            "option_c": "A database",
            "option_d": "A browser",
            "correct_option": "B",
        }
    ]
    validated = validate_generated_quiz_items(items, 5)
    assert validated[0]["correct_option"] == "B"


def test_validate_generated_quiz_items_rejects_invalid():
    with pytest.raises(LLMServiceError):
        validate_generated_quiz_items([{"question": "Incomplete"}], 5)


def test_validate_generated_quest_items():
    items = [
        {
            "title": "Study 20 minutes",
            "description": "Study for 20 minutes today.",
            "frequency": "daily",
            "target_metric": "study_minutes",
            "target_value": 20,
            "reward_points": 25,
        }
    ]
    validated = validate_generated_quest_items(items, 3, "daily")
    assert validated[0]["target_metric"] == "study_minutes"
    assert validated[0]["reward_points"] == 25


def test_validate_generated_quest_items_clamps_reward():
    items = [
        {
            "title": "Study a lot",
            "description": "Study today.",
            "frequency": "daily",
            "target_metric": "study_minutes",
            "target_value": 20,
            "reward_points": 9999,
        }
    ]
    validated = validate_generated_quest_items(items, 3, "daily")
    assert validated[0]["reward_points"] == 200
