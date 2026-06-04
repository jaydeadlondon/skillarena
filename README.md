<div align="center">

# ⚔️ SkillArena

**A dark RPG-style gamified learning platform for focused, consistent education.**

SkillArena combines Steam authentication, structured courses, real video tracking, quests, streaks, achievements, focus sessions, PvP quiz battles, profile customization, and administrative tools into one Python-based web application.

<br>

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Web%20App-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-Async%20ORM-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

<br>

[Core Features](#core-features) • [Tech Stack](#tech-stack) • [Running Locally](#running-locally) • [Routes](#main-user-routes) • [Database](#database-management)

</div>

---

## Overview

SkillArena is designed around a simple loop: learn in small steps, earn rewards, maintain momentum, and make progress visible. The application is especially focused on reducing friction for learners who benefit from short goals, clear feedback, visual progress, and game-like motivation.

The interface is built in English with a dark RPG/gaming style.

## Core features

### Authentication

- Steam-only login through Steam OpenID.
- Steam profile synchronization.
- Steam Web API support for recent playtime statistics.
- Optional development mock login.
- Configurable admin Steam IDs.

### Learning

- Course catalog.
- Course detail pages.
- Lesson pages with embedded legal video content.
- AI Study Companion on lesson pages.
- YouTube iframe API support for real playback tracking.
- Fallback manual lesson timer for non-YouTube embeds.
- Lesson progress tracking.
- Course progress bars.
- Continue-learning flow.
- Course completion rewards.

### Activity tracking

- Active browser-time tracking through heartbeat requests.
- Tracks site, lesson, course, PvP, quest, shop, profile, focus, and admin activity.
- Counts only visible and recently active browser time.
- Lesson time is tracked from real video playback where supported.

### Gamification

- Skill Points currency.
- Daily quests.
- Weekly quests.
- Period-based quest claiming.
- Learning streaks.
- LeetCode-style streak indicator in the navigation bar.
- Achievements and achievement gallery.
- Reward notifications.
- Reward popups and confetti animations.

### Focus sessions

- Pomodoro-style focus timers.
- Available focus durations: 5, 15, 25, and 50 minutes.
- Skill Point rewards for completed focus sessions.
- Focus sessions contribute to streaks and quests.
- User onboarding preferences can mark a preferred focus session duration.

### PvP quiz battles

- PvP quiz lobby.
- Entry fee paid with Skill Points.
- Server-validated quiz answers.
- WebSocket live battle feed.
- Ready check.
- Server-authoritative battle deadline.
- Deadline-synchronized client countdown.
- Late submission handling.
- Tie handling with entry-fee refunds.
- Battle history.

### Profile and customization

- RPG-style user profile.
- Steam avatar display.
- Equipped profile cosmetics.
- Profile frames, backgrounds, and auras.
- Level progress based on lifetime earned Skill Points.
- Learning statistics.
- PvP record.
- Onboarding preferences.
- Achievement summary.
- Recent PvP battles.
- Steam-vs-study comparison.

### Cosmetic shop

- Purchasable profile cosmetics.
- Cosmetic inventory.
- Equip and unequip actions.
- Supported cosmetic types:
  - profile frame;
  - profile background;
  - aura.

### Notifications

- User notifications page.
- Skill Point reward notifications.
- PvP refund notifications.
- Admin adjustment notifications.
- Mark one notification as read.
- Mark all notifications as read.

### Onboarding

- Learning goal selection.
- Experience level selection.
- Daily and weekly learning targets.
- Preferred learning style.
- Focus challenge selection.
- Preferred focus session length.
- PvP recommendation preference.
- Steam-vs-study balance preference.

### Administration

- Admin dashboard.
- User management.
- Role management.
- Manual Skill Point adjustments.
- Course management.
- Lesson management.
- Course publishing controls.
- AI quiz generation from lesson content.
- Quest creation and activation controls.
- PvP question creation and activation controls.
- Cosmetic creation, editing, pricing, previewing, activation, and deactivation.

## Tech stack

- Python 3.12+
- FastAPI
- httpx-based LLM provider integration
- Jinja2 templates
- SQLAlchemy 2.x async ORM
- PostgreSQL
- asyncpg
- Alembic
- Docker Compose
- Steam OpenID
- Steam Web API
- WebSockets
- Vanilla JavaScript
- CSS

## Project structure

```text
SkillArena/
├── app/
│   ├── core/              # Application configuration
│   ├── db/                # Database engine, session, and base metadata
│   ├── models/            # SQLAlchemy models
│   ├── routers/           # FastAPI route modules
│   ├── schemas/           # Reserved for Pydantic schemas
│   ├── services/          # Domain services
│   ├── static/            # CSS and JavaScript assets
│   └── templates/         # Jinja templates
├── alembic/
│   ├── versions/          # Database migrations
│   └── env.py
├── scripts/               # Local utility scripts
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── README.md
└── .env.example
```

## Environment configuration

Create a local environment file:

```bash
cp .env.example .env
```

Main environment variables:

```env
APP_NAME=SkillArena
APP_ENV=development
APP_SECRET_KEY=change-me-to-a-long-random-secret
APP_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+asyncpg://skillarena:skillarena@db:5432/skillarena

STEAM_API_KEY=your-steam-web-api-key
STEAM_REALM=http://localhost:8000
STEAM_RETURN_URL=http://localhost:8000/auth/steam/callback
STEAM_MOCK_LOGIN=true
ADMIN_STEAM_IDS=7656119xxxxxxxxxx,7656119yyyyyyyyyy

SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=lax
SESSION_MAX_AGE_SECONDS=1209600

LLM_ENABLED=false
LLM_PROVIDER=groq
LLM_API_KEY=put-your-llm-api-key-here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
LLM_DAILY_LIMIT_PER_USER=20
LLM_TIMEOUT_SECONDS=30
```

A production-oriented environment template is available as:

```text
.env.production.example
```

## Running locally

Start the application and PostgreSQL:

```bash
docker compose up --build
```

Open the application:

```text
http://localhost:8000
```

If the image has already been built and dependencies have not changed, this is usually enough:

```bash
docker compose up
```

## Database management

Run database migrations:

```bash
docker compose exec web python -m alembic upgrade head
```

Alternative migration helper:

```bash
docker compose exec web python scripts/migrate_db.py
```

Seed demo data:

```bash
docker compose exec web python scripts/seed_demo.py
```

Inspect registered and existing database tables:

```bash
docker compose exec web python scripts/debug_tables.py
```

A local metadata-based table creation helper is also available:

```bash
docker compose exec web python scripts/create_db.py
```

## Health checks

Application health:

```text
GET /health
```

Database health:

```text
GET /health/db
```

## Steam authentication

Steam login:

```text
GET /auth/steam
```

Steam callback:

```text
GET /auth/steam/callback
```

Debug generated Steam login URL:

```text
GET /auth/steam/login-url
```

Development mock login:

```text
GET /auth/steam/mock
```

To give a real Steam user admin access, add their SteamID64 to:

```env
ADMIN_STEAM_IDS=7656119xxxxxxxxxx
```

A manual admin promotion helper is also available:

```bash
docker compose exec web python scripts/grant_admin.py <steam_id_64>
```

## Main user routes

```text
/                         Home page
/dashboard                User dashboard
/courses                  Course catalog
/courses/{slug}           Course detail
/learn/lessons/{id}       Lesson player
/activity/heartbeat       Activity tracking endpoint
/achievements             Achievement gallery
/ai/lessons/{id}/ask      AI Study Companion request endpoint
/ai/lessons/{id}/history  AI Study Companion history endpoint
/focus                    Focus sessions
/onboarding               User onboarding
/notifications            User notifications
/quests                   Daily and weekly quests
/streaks                  Learning streaks
/profile                  User profile
/shop                     Cosmetic shop
/pvp                      PvP lobby
/pvp/history              PvP battle history
/pvp/{id}/play            PvP battle page
/pvp/{id}/state           PvP battle state endpoint
/pvp/{id}/ws              PvP live WebSocket endpoint
```

## Admin routes

```text
/admin                    Admin dashboard
/admin/courses            Course management
/admin/courses/{id}       Course and lesson editor
/admin/users              User management
/admin/cosmetics          Cosmetic management
```

## Learning flow

1. A user logs in with Steam.
2. The user completes onboarding.
3. The dashboard recommends a next action.
4. The user opens a course and continues the next lesson.
5. Lesson video playback is tracked.
6. Lesson completion grants Skill Points.
7. Course completion grants course rewards.
8. Quests and streaks update from learning activity.
9. Achievements unlock as goals are reached.
10. Skill Points can be spent in the cosmetic shop or used for PvP entry fees.

## PvP flow

1. A user creates a PvP quiz battle.
2. The entry fee is deducted.
3. Another user joins the battle.
4. Both users press Ready.
5. The server sets `started_at` and `deadline_at`.
6. The client countdown synchronizes to the server deadline.
7. Users submit answers before the deadline.
8. The server validates answers and calculates scores.
9. The winner receives the battle reward.
10. A tie refunds both entry fees.

## Activity and video tracking

SkillArena uses two complementary tracking systems:

1. General active-time tracking through `/activity/heartbeat`.
2. Lesson video tracking through the lesson player.

YouTube lessons use the YouTube iframe API with `enablejsapi=1`. Time is counted while the video is playing and the browser tab is visible.

For non-YouTube embeds, SkillArena provides a fallback lesson timer.

## Content policy

SkillArena should only embed or link to content that is legal to use:

- YouTube videos that allow embedding;
- Vimeo videos that allow embedding;
- free public learning resources with allowed linking or embedding;
- owned or properly licensed content.

Do not mirror or embed paid/protected content without permission.

## Common development commands

Restart the web container:

```bash
docker compose restart web
```

Run migrations:

```bash
docker compose exec web python -m alembic upgrade head
```

Seed demo data:

```bash
docker compose exec web python scripts/seed_demo.py
```

Run a syntax check:

```bash
python -m compileall app scripts alembic
```

Reset the local Docker database volume:

```bash
docker compose down -v
docker compose up --build
docker compose exec web python -m alembic upgrade head
docker compose exec web python scripts/seed_demo.py
```
