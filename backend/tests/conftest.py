"""Test setup: a throwaway SQLite database, the real app, and small helpers for making users and signing in."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Must be set before the app is imported, because the database address is read at import time
_tmp = tempfile.mkdtemp(prefix="taskpilot-test-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(_tmp) / "test.db").as_posix()
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-key-test-jwt-key-test-jwt-key"
os.environ["ADMIN_PASSWORD"] = "Start-Admin-1!"
os.environ.pop("FLASK_ENV", None)
os.environ.pop("APP_ENV", None)
os.environ.pop("DEMO_MODE", None)

import app as app_module  # noqa: E402
from database import db  # noqa: E402
from models import Project, ProjectMember, Task, User  # noqa: E402
from utils.ratelimit import limiter  # noqa: E402

PASSWORD = "Str0ng-Pass!"


@pytest.fixture()
def app():
    flask_app = app_module.app
    defaults = {k: flask_app.config[k] for k in ("LOGIN_LIMIT_PER_EMAIL", "LOGIN_LIMIT_PER_IP", "SIGNUP_LIMIT_PER_IP", "DEMO_MODE")}
    flask_app.config.update(LOGIN_LIMIT_PER_EMAIL=1000, LOGIN_LIMIT_PER_IP=1000, SIGNUP_LIMIT_PER_IP=1000)
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
    limiter.reset_all()
    yield flask_app
    flask_app.config.update(defaults)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make(app):
    """make.user(email, role) / make.project(title, creator, members) / make.task(...): straight into the database."""

    class Maker:
        def user(self, email, role="Member", name=None, password=PASSWORD):
            with app.app_context():
                user = User(name=name or email.split("@")[0].title(), email=email, role=role)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                return user.id

        def project(self, title, creator_id, member_ids=()):
            with app.app_context():
                project = Project(title=title, description="", created_by=creator_id)
                db.session.add(project)
                db.session.flush()
                for uid in {creator_id, *member_ids}:
                    db.session.add(ProjectMember(project_id=project.id, user_id=uid))
                db.session.commit()
                return project.id

        def task(self, title, project_id, assigned_to=None, status="Pending"):
            with app.app_context():
                task = Task(title=title, project_id=project_id, assigned_to=assigned_to, status=status)
                db.session.add(task)
                db.session.commit()
                return task.id

    return Maker()


def sign_in(client, email, password=PASSWORD):
    res = client.post("/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": "Bearer " + res.get_json()["token"]}


@pytest.fixture()
def login(client):
    return lambda email, password=PASSWORD: sign_in(client, email, password)
