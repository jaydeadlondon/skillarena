import pytest

from app.core.validation import (
    ValidationError,
    clean_text,
    clamp_int,
    validate_choice,
    validate_url,
)


def test_clean_text_strips_and_limits():
    assert clean_text("  Hello  ", max_length=10, field_name="name") == "Hello"


def test_clean_text_required():
    with pytest.raises(ValidationError):
        clean_text("   ", max_length=10, field_name="name")


def test_clean_text_too_long():
    with pytest.raises(ValidationError):
        clean_text("abcdef", max_length=3, field_name="name")


def test_clamp_int():
    assert clamp_int("10", min_value=1, max_value=20, field_name="value") == 10
    assert clamp_int("-5", min_value=1, max_value=20, field_name="value") == 1
    assert clamp_int("50", min_value=1, max_value=20, field_name="value") == 20


def test_clamp_int_invalid():
    with pytest.raises(ValidationError):
        clamp_int("not-a-number", min_value=1, max_value=20, field_name="value")


def test_validate_choice():
    assert (
        validate_choice("daily", allowed={"daily", "weekly"}, field_name="frequency")
        == "daily"
    )
    with pytest.raises(ValidationError):
        validate_choice("monthly", allowed={"daily", "weekly"}, field_name="frequency")


def test_validate_url_accepts_http_https():
    assert (
        validate_url("https://example.com/video", field_name="url")
        == "https://example.com/video"
    )
    assert (
        validate_url("http://example.com/video", field_name="url")
        == "http://example.com/video"
    )


def test_validate_url_rejects_invalid_scheme():
    with pytest.raises(ValidationError):
        validate_url("javascript:alert(1)", field_name="url")
