# TaskPilot

TaskPilot is a modern Flask task management web app with JWT authentication, role-based authorization, SQLite persistence, project/task CRUD, member-scoped access, and Chart.js analytics.

## Features

- JWT signup, login, logout, protected APIs, and hashed passwords
- Admin role for project, task, member, and user management
- Member role for assigned/project tasks, task status updates, and analytics
- Project membership, task assignment, search, filters, overdue highlighting, and status updates
- Responsive dark SaaS UI with sidebar navigation, cards, pills, modals, toasts, empty states, and Chart.js charts

## Quick Start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`.

Seeded admin account:

- Email: `admin@taskpilot.dev`
- Password: `Admin@12345`

## Environment

`DATABASE_URL` defaults to local SQLite at `database/taskpilot.db`. For Railway or Render, set:

```bash
SECRET_KEY=...
JWT_SECRET_KEY=...
DATABASE_URL=sqlite:///database/taskpilot.db
```

## API

- `POST /signup`
- `POST /login`
- `GET /me`
- `GET|POST /projects`
- `GET|PUT|DELETE /projects/<id>`
- `POST /projects/<id>/members`
- `DELETE /projects/<id>/members/<user_id>`
- `GET|POST /tasks`
- `PUT|DELETE /tasks/<id>`
- `GET /dashboard/stats`
- `GET /users`
- `PUT /users/<id>`
- `PUT /profile`

## Deployment

Use `gunicorn app:app` from the `backend` directory. The project includes `gunicorn` in `requirements.txt` and reads secrets from environment variables.
