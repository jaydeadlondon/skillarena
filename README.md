# SkillArena

SkillArena is a gamified learning platform built for focused, ADHD-friendly education. The MVP combines Steam sign-in, legal embedded learning content, quests, Skill Points, PvP quiz battles, achievements, profile progression, and a dark RPG-style interface.

## Current MVP status

The current MVP includes:

- Steam-only authentication via Steam OpenID.
- Steam Web API integration for profile data and recent playtime.
- PostgreSQL database with SQLAlchemy async models.
- Course catalog with legal external video embeds, progress bars, continue-learning actions, and course completion rewards.
- Lesson pages with real YouTube playback tracking, active heartbeat fallback tracking, and progress updates.
- RPG-style user profiles with level progress, cosmetics, onboarding preferences, learning stats, PvP record, achievements, and Steam-vs-study comparison.
- Skill Points currency.
- Cosmetic shop with purchasable/equippable profile frames, backgrounds, and auras.
- Daily and weekly quests with automatic progress tracking, period-based claiming, and Skill Point rewards.
- Pomodoro-style focus sessions with selectable timers, Skill Point rewards, and streak support.
- Expanded onboarding flow for learning goals, experience level, daily/weekly targets, preferred learning style, focus challenges, PvP preferences, Steam-balance nudges, and preferred focus session length.
- Notifications page and reward animations for Skill Point rewards, refunds, and system updates.
- Learning streak system with LeetCode-style navbar streak indicator, 14-day timeline, and streak achievements.
- Active-time tracking that only counts visible, recently active browser time and updates lesson progress automatically.
- Server-rendered English UI using FastAPI and Jinja templates.
- Polished dark RPG UI with compact navigation, responsive cards, improved empty states, hover states, and page headers.
- PvP quiz battles with server-side answer validation, live WebSocket battle feed, ready check, server-authoritative deadline, battle history, result display, and tie refunds.
- Admin panel for full course/lesson editing, quests, PvP questions, users, role changes, Skill Point adjustments, and cosmetics.
- Production-readiness basics: Alembic migrations, database health check, environment examples, secure session settings, and custom error pages.
- Demo seed data for local development.

## Tech stack

- Python 3.12+
- FastAPI
- Jinja2 templates
- SQLAlchemy 2.x async ORM
- PostgreSQL 16
- asyncpg
- Docker Compose
- Steam OpenID authentication
- Steam Web API
- Vanilla CSS and JavaScript

## Project structure

```text
SkillArena/
├── app/
│   ├── core/          # Configuration
│   ├── db/            # Database engine/session/base metadata
│   ├── models/        # SQLAlchemy models
│   ├── routers/       # FastAPI route modules
│   ├── schemas/       # Reserved for Pydantic schemas
│   ├── services/      # Steam, rewards, video helpers, domain services
│   ├── static/        # CSS and JavaScript
│   └── templates/     # Jinja HTML templates
├── scripts/           # Local database/setup utilities
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── README.md
└── .env.example
```

## Environment variables

Create a local `.env` file:

```bash
cp .env.example .env
```

A production-oriented example is also available:

```text
.env.production.example
```

Main variables:

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
```

`ADMIN_STEAM_IDS` is optional but recommended for local development. Add your real SteamID64 there to receive admin access after Steam login.

## Running locally with Docker Compose

From the project root:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000
```

Health checks:

```text
http://localhost:8000/health
http://localhost:8000/health/db
```

## Database setup

Recommended migration flow:

```bash
docker compose exec web python -m alembic upgrade head
```

Alternative helper:

```bash
docker compose exec web python scripts/migrate_db.py
```

Legacy local table creation is still available for development:

```bash
docker compose exec web python scripts/create_db.py
```

Seed demo data:

```bash
docker compose exec web python scripts/seed_demo.py
```

Alternative module-style commands:

```bash
docker compose exec web python -m scripts.create_db
docker compose exec web python -m scripts.seed_demo
```

Debug registered and existing database tables:

```bash
docker compose exec web python scripts/debug_tables.py
```

Alembic is configured for schema migrations. The legacy `create_db.py` script remains available for local development and creates missing tables with SQLAlchemy metadata.

## Steam authentication

Steam login route:

```text
/auth/steam
```

Debug generated Steam login URL:

```text
/auth/steam/login-url
```

Steam callback route:

```text
/auth/steam/callback
```

For real Steam login:

1. Put your Steam Web API key into `.env`.
2. Set `STEAM_MOCK_LOGIN=false` if you want to hide development mock login behavior.
3. Make sure the app is opened using the same host you expect for callback URLs, usually `http://localhost:8000` in local development.

## Admin access

Admin-only pages require the user role `admin`.

Recommended local method:

1. Find your SteamID64.
2. Add it to `.env`:

```env
ADMIN_STEAM_IDS=your_steam_id_64
```

3. Restart the web container:

```bash
docker compose restart web
```

4. Log out and log in through Steam again.

You can also promote a user manually with the helper script:

```bash
docker compose exec web python scripts/grant_admin.py your_steam_id_64
```

Admin panel:

```text
/admin
```

## Main routes

```text
/                         Home page
/health                   Application health check
/health/db                Database health check
/dashboard                User dashboard
/courses                  Course catalog
/courses/{slug}           Course detail
/learn/lessons/{id}       Lesson player
/activity/heartbeat       Activity tracking endpoint
/focus                    Pomodoro-style focus sessions
/onboarding               User onboarding and learning setup
/notifications            User notifications
/quests                   Daily quests
/streaks                  Learning streaks
/profile                  User profile
/shop                     Cosmetic shop
/pvp                      PvP lobby
/pvp/history              PvP battle history
/pvp/{id}/play            PvP battle page
/admin                    Admin panel
/admin/courses            Admin course management
/admin/courses/{id}       Admin course and lesson editor
/admin/users              Admin user management
/admin/cosmetics          Admin cosmetic management
/auth/steam               Steam login
/auth/steam/mock          Development mock login
```

## MVP gameplay loop

1. User signs in with Steam.
2. User completes onboarding with learning goal and focus preferences.
3. User opens the dashboard and sees Skill Points, quests, study stats, and Steam-vs-study balance.
4. User selects a course.
5. User completes small lessons.
6. Lesson progress increases study time, course progress, and rewards Skill Points.
7. Completed courses grant course rewards and guide the user to the next learning step.
8. User builds a daily streak through lessons, focus sessions, study time, or PvP wins.
9. User completes daily quests and claims extra Skill Points.
10. User joins PvP quiz battles and pays an entry fee.
11. Server validates PvP answers and pays the winner.
12. User spends Skill Points in the cosmetic shop.
13. User profile displays progress, achievements, and earned identity markers.

## Legal content policy

SkillArena should only embed or link to materials that are legal to use:

- YouTube videos that allow embedding.
- Vimeo videos that allow embedding.
- Free public learning resources with allowed embedding/linking.
- Own uploaded or owned content in future versions.

Do not mirror or embed paid/protected Udemy content unless explicit permission or a valid integration permits it.

## Development notes

After pulling new model changes, run:

```bash
docker compose exec web python scripts/create_db.py
```

If the web app behaves like it is using old Python code, restart the container:

```bash
docker compose restart web
```

For a full clean local restart:

```bash
docker compose down
docker compose up --build
```

To reset the local database completely:

```bash
docker compose down -v
docker compose up --build
docker compose exec web python scripts/create_db.py
docker compose exec web python scripts/seed_demo.py
```

## Roadmap after MVP

Planned next improvements:

- Automatic achievement evaluation.
- Cosmetic shop and profile customization.
- Stronger quest progress and claim flow.
- Stronger real-time PvP matchmaking and Redis-backed multi-process rooms.
- Alembic migrations.
- Redis-backed background jobs and scheduled Steam stat refresh.
- Production deployment configuration.
