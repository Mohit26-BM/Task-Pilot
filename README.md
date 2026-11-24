# TaskPilot

A project management web app: landing page, JWT sign-in, Admin and Member roles, projects with members, a task list and Kanban board, a live dashboard, and a dark UI.

**Stack:** Flask · SQLAlchemy · Flask-JWT-Extended · SQLite (or PostgreSQL) · Gunicorn · vanilla JS

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

**First admin account:** `admin@taskpilot.dev`. Its password comes from `ADMIN_PASSWORD` in `.env`. In development, if that is unset, an admin is created with the password `Admin@12345` and the terminal tells you so on first start. That password is only for your own machine, and a production start refuses to run while it is still in use.

Everyone who signs up on the site becomes a **Member**. Admins are made by an existing Admin on the **Users** page.

---

## Roles

| | Admin | Member |
|---|---|---|
| Projects | create, edit, delete, manage members; sees all | sees only projects they belong to |
| Tasks | create, edit, delete, assign; sees all | sees tasks in their projects or assigned to them, and can change the **status** of those |
| Users | list everyone, change roles | none (dropdowns show only teammates' names) |
| Profile | change name and password | change name and password |

Rules the app enforces:
- Whoever is assigned a task becomes a member of that task's project (so they can see it), also when the task is moved to another project.
- Removing someone from a project unassigns their tasks in it.
- There must always be at least one Admin: the last one cannot be demoted.
- Changing your password needs your current password.

---

## Environment variables

Copy `backend/.env.example` to `backend/.env`. The important ones:

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_ENV` | production: yes | Set to `production` on a live site |
| `SECRET_KEY`, `JWT_SECRET_KEY` | production: yes | Two different random values, 32+ characters. The app refuses to start in production without them. In development a missing one becomes a random value per run |
| `ADMIN_PASSWORD` | recommended | Password of `admin@taskpilot.dev` (see above) |
| `DATABASE_URL` | no | SQLAlchemy URL; omit to use a local SQLite file |
| `CORS_ORIGINS` | no | Only if another site calls the API from a browser. Empty means no cross-site access |
| `TRUST_PROXY` | behind a proxy | Number of proxies in front (usually `1`) |
| `DEMO_MODE` | no | `1` shows a shared **Demo Member** button on the login page |

Sign-in is rate limited (8 tries per account and 30 per address in 15 minutes by default; sign-up 10 per hour), see `.env.example`. Counts are kept per worker process.

---

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

The tests run the real app on a temporary database: sign-up and sign-in, rate limits, secrets and seeded accounts, who can see and change what, input checking, and the project and task rules.

---

## Deployment

### Render / Railway / Heroku

The repo includes a `Procfile`:

```
web: gunicorn --chdir backend app:app
```

Set `FLASK_ENV=production`, `SECRET_KEY`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD` and `TRUST_PROXY=1` in your platform dashboard.

**If you already deployed an older version:** it published the admin password on the login page and let anyone sign up as an Admin. After upgrading, set a new `ADMIN_PASSWORD`, change the admin password on the Profile page if it was ever a real one, and check the **Users** page for Admins you do not recognise.

> **SQLite note:** Render's free tier uses an ephemeral filesystem, so a SQLite database is wiped on every redeploy. Use a persistent disk or a PostgreSQL `DATABASE_URL`.

> **Schema changes:** the app creates missing tables on start but has no migration tool, so changing a column needs a manual migration (or a fresh database).

---

## Project structure

```
backend/
├── app.py              # App factory, pages, token handling, seeded accounts
├── config.py           # Settings from the environment; refuses weak secrets in production
├── requirements.txt
├── models/             # User, Project, Task, ProjectMember
├── routes/             # auth, projects, tasks, users, dashboard
├── middleware/         # role guard
├── utils/              # validators, rate limiter, helpers
├── static/             # CSS, JS, images
├── templates/          # Jinja2 pages
└── tests/              # pytest suite
```

## Known limitations
- No password reset by email and no way to deactivate a user (an Admin can only change roles).
- The sign-in token is kept in the browser's `localStorage`, as in most single-page setups; a cross-site-scripting bug would expose it. User text is escaped everywhere it is shown.
- Rate-limit counts are per worker, and reset when the app restarts.
