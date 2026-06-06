# TaskPilot

A modern project management web app — landing page, JWT auth, role-based access control, Kanban board, live dashboard, and a dark SaaS UI.

**Stack:** Flask · SQLAlchemy · Flask-JWT-Extended · SQLite · Gunicorn · Vanilla JS

---

## Quick start

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # then edit .env
python app.py
```

Open `http://127.0.0.1:5000`.

**Demo admin account (seeded on first run):**
| Field | Value |
|-------|-------|
| Email | `admin@taskpilot.dev` |
| Password | `Admin@12345` (override with `ADMIN_PASSWORD` env var) |

---

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in the values:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask secret key |
| `JWT_SECRET_KEY` | Yes | JWT signing key |
| `ADMIN_PASSWORD` | No | Seed admin password (default: `Admin@12345`) |
| `DATABASE_URL` | No | SQLAlchemy DB URL — omit to use local SQLite |
| `CORS_ORIGINS` | No | Allowed CORS origin (default: `*`) |

---

## Deployment

### Render / Railway / Heroku

The repo includes a `Procfile`:

```
web: gunicorn --chdir backend app:app
```

Set `SECRET_KEY`, `JWT_SECRET_KEY`, and `ADMIN_PASSWORD` as environment variables in your platform dashboard.

> **SQLite note:** Render's free tier uses an ephemeral filesystem — your SQLite database is wiped on every redeploy. Use a persistent volume (Render Disk) or switch `DATABASE_URL` to a PostgreSQL connection string for a durable database.

---

## Project structure

```
backend/
├── app.py              # App factory, routes, seed
├── config.py           # Config from env vars
├── requirements.txt
├── models/             # User, Project, Task, ProjectMember
├── routes/             # auth, projects, tasks, users, dashboard
├── middleware/         # JWT + role guard
├── utils/              # Helpers, validators
├── static/             # CSS, JS, images
└── templates/          # Jinja2 HTML templates
```
