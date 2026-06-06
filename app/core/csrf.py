import secrets
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

CSRF_SESSION_KEY = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER = "x-csrf-token"


def get_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def csrf_input(request: Request) -> str:
    token = get_csrf_token(request)
    return f'<input type="hidden" name="{CSRF_FORM_FIELD}" value="{token}">'


def csrf_token_from_request(request: Request) -> str | None:
    header_token = request.headers.get(CSRF_HEADER)
    if header_token:
        return header_token
    query_token = request.query_params.get(CSRF_FORM_FIELD)
    return str(query_token) if query_token else None


def is_same_origin_request(request: Request) -> bool:
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    host = request.headers.get("host")
    if not host:
        return False

    for value in (origin, referer):
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.netloc == host:
            return True
    return False


async def validate_csrf_request(request: Request) -> bool:
    expected = request.session.get(CSRF_SESSION_KEY)
    supplied = csrf_token_from_request(request)
    if expected and supplied:
        return secrets.compare_digest(str(expected), str(supplied))

    return is_same_origin_request(request)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exempt_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self.exempt_paths = exempt_paths or set()

    async def dispatch(self, request: Request, call_next):
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.url.path not in self.exempt_paths
        ):
            if not await validate_csrf_request(request):
                return JSONResponse(
                    {"detail": "Invalid or missing CSRF token."},
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        return await call_next(request)
