# SkillArena

SkillArena is a gamified learning platform built for focused, ADHD-friendly education. The MVP combines Steam sign-in, legal embedded learning content, quests, Skill Points, PvP quiz battles, achievements, profile progression, and a dark RPG-style interface.

## Current MVP status

The current MVP includes:

- Steam-only authentication via Steam OpenID.
- Steam Web API integration for profile data and recent playtime.
- PostgreSQL database with SQLAlchemy async models.
- Course catalog with legal external video embeds, including YouTube/Vimeo links.
- Lesson pages with simplified study-time tracking.
- User profiles with Steam-vs-study time comparison.
- Skill Points currency.
- Cosmetic shop with purchasable/equippable profile frames, backgrounds, and auras.
- Daily quests page with automatic progress tracking and claimable Skill Point rewards.
- Learning streak system with LeetCode-style navbar streak indicator, 14-day timeline, and streak achievements.
- Server-rendered English UI using FastAPI and Jinja templates.
- Dark RPG / gaming dashboard styling.
- Focus Mode toggle for a cleaner learning interface. Press `Exit Focus Mode` or `Esc` to leave it.
- PvP quiz battles with server-side answer validation.
- Basic admin panel for courses, lessons, quests, users, and PvP questions.
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

Health check:

```text
http://localhost:8000/health
```

## Database setup

Create tables:

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

The MVP currently uses `Base.metadata.create_all()` for local development. It creates missing tables, but it does not perform production-grade schema migrations. Alembic migrations should be added before production deployment.

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
/dashboard                User dashboard
/courses                  Course catalog
/courses/{slug}           Course detail
/learn/lessons/{id}       Lesson player
/quests                   Daily quests
/streaks                  Learning streaks
/profile                  User profile
/shop                     Cosmetic shop
/pvp                      PvP lobby
/pvp/{id}/play            PvP battle page
/admin                    Admin panel
/auth/steam               Steam login
/auth/steam/mock          Development mock login
```

## MVP gameplay loop

1. User signs in with Steam.
2. User opens the dashboard and sees Skill Points, quests, study stats, and Steam-vs-study balance.
3. User selects a course.
4. User completes small lessons.
5. Lesson progress increases study time and rewards Skill Points.
6. User builds a daily streak through lessons, study time, or PvP wins.
7. User completes daily quests and claims extra Skill Points.
8. User joins PvP quiz battles and pays an entry fee.
9. Server validates PvP answers and pays the winner.
10. User spends Skill Points in the cosmetic shop.
11. User profile displays progress, achievements, and earned identity markers.

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

Focus Mode stores its state in browser localStorage. If you ever get stuck in Focus Mode, press `Esc`, click `Exit Focus Mode`, or clear `localStorage.focusMode` in browser devtools.

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
- Better study-time tracking based on video playback and page activity.
- Real-time PvP through WebSockets.
- Alembic migrations.
- Redis-backed background jobs and scheduled Steam stat refresh.
- Production deployment configuration.
