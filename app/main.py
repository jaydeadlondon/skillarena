from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.routers import admin, auth, learning, pages, pvp, quests, shop

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    SessionMiddleware, secret_key=settings.app_secret_key, same_site="lax"
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.state.templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(learning.router)
app.include_router(pvp.router)
app.include_router(quests.router)
app.include_router(shop.router)
app.include_router(admin.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
