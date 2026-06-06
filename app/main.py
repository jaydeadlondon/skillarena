import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.db.session import engine
from app.routers import (
    achievements,
    activity,
    admin,
    ai,
    auth,
    focus,
    learning,
    notifications,
    onboarding,
    pages,
    pvp,
    quests,
    shop,
    streaks,
)

settings = get_settings()
logging.basicConfig(
    level=logging.INFO if settings.app_env != "production" else logging.WARNING
)
logger = logging.getLogger("skillarena")

app = FastAPI(title=settings.app_name, debug=settings.app_env == "development")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret_key,
    same_site=settings.session_cookie_samesite,
    https_only=settings.session_cookie_secure,
    max_age=settings.session_max_age_seconds,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.state.templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(activity.router)
app.include_router(achievements.router)
app.include_router(ai.router)
app.include_router(pages.router)
app.include_router(learning.router)
app.include_router(onboarding.router)
app.include_router(notifications.router)
app.include_router(focus.router)
app.include_router(pvp.router)
app.include_router(quests.router)
app.include_router(shop.router)
app.include_router(streaks.router)
app.include_router(admin.router)


@app.on_event("startup")
async def startup_log() -> None:
    logger.info("%s started in %s mode", settings.app_name, settings.app_env)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code in {403, 404}:
        template_name = f"errors/{exc.status_code}.html"
        return request.app.state.templates.TemplateResponse(
            request,
            template_name,
            {"request": request, "status_code": exc.status_code, "detail": exc.detail},
            status_code=exc.status_code,
        )
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled application error: %s", exc)
    return request.app.state.templates.TemplateResponse(
        request,
        "errors/500.html",
        {"request": request, "status_code": 500, "detail": "Internal server error"},
        status_code=500,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.get("/health/db")
async def health_db() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("select 1"))
    return {"status": "ok", "database": "reachable"}
