from urllib.parse import urlparse


class ValidationError(ValueError):
    pass


def clean_text(
    value: str | None, *, max_length: int, field_name: str, required: bool = True
) -> str:
    value = (value or "").strip()
    if required and not value:
        raise ValidationError(f"{field_name} is required")
    if len(value) > max_length:
        raise ValidationError(f"{field_name} is too long")
    return value


def clean_optional_text(
    value: str | None, *, max_length: int, field_name: str
) -> str | None:
    value = clean_text(
        value, max_length=max_length, field_name=field_name, required=False
    )
    return value or None


def clamp_int(
    value: int | str | None, *, min_value: int, max_value: int, field_name: str
) -> int:
    try:
        parsed = int(value if value is not None else min_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a number") from exc
    return max(min_value, min(parsed, max_value))


def validate_choice(value: str | None, *, allowed: set[str], field_name: str) -> str:
    value = (value or "").strip()
    if value not in allowed:
        raise ValidationError(f"{field_name} is invalid")
    return value


def validate_url(
    value: str | None, *, field_name: str, required: bool = True, max_length: int = 1000
) -> str:
    value = clean_text(
        value, max_length=max_length, field_name=field_name, required=required
    )
    if not value and not required:
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError(f"{field_name} must be a valid http(s) URL")
    return value


def validate_hex_color_or_css(
    value: str | None, *, field_name: str = "preview value"
) -> str:
    value = clean_text(value, max_length=120, field_name=field_name, required=True)
    # Cosmetics currently use CSS color-like preview values. Keep this permissive
    # for named colors/gradients later, but block obviously dangerous strings.
    forbidden = {"<", ">", "javascript:", "url("}
    lowered = value.lower()
    if any(token in lowered for token in forbidden):
        raise ValidationError(f"{field_name} is invalid")
    return value
