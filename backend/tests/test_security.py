"""Sign-up, sign-in, secrets, seeded accounts and the login page."""
import subprocess
import sys

import pytest

from conftest import BACKEND, PASSWORD
from database import db
from models import User


def post(client, url, **body):
    return client.post(url, json=body)


# ---------- sign-up ----------
def test_signup_always_makes_a_member_even_if_admin_is_requested(client):
    res = post(client, "/signup", name="Eve", email="eve@example.com", password=PASSWORD, role="Admin")
    assert res.status_code == 201
    assert res.get_json()["user"]["role"] == "Member"
    token = res.get_json()["token"]
    # and the new account really cannot do admin things
    assert client.get("/users", headers={"Authorization": "Bearer " + token}).status_code == 403
    assert client.post("/projects", json={"title": "x"}, headers={"Authorization": "Bearer " + token}).status_code == 403


@pytest.mark.parametrize(
    "body, fragment",
    [
        ({"name": "", "email": "a@b.co", "password": PASSWORD}, "Name is required"),
        ({"name": "A", "email": "not-an-email", "password": PASSWORD}, "valid email"),
        ({"name": "A", "email": "a@b.co", "password": "weak"}, "Password must include"),
        ({"name": ["A"], "email": "a@b.co", "password": PASSWORD}, "Name must be text"),
        ({"name": "A", "email": {"x": 1}, "password": PASSWORD}, "valid email"),
        ({"name": "A", "email": "a@b.co", "password": 12345678}, "Password must include"),
        ({"name": "x" * 81, "email": "a@b.co", "password": PASSWORD}, "too long"),
    ],
)
def test_signup_refuses_bad_input_without_crashing(client, body, fragment):
    res = client.post("/signup", json=body)
    assert res.status_code == 400
    assert fragment in res.get_json()["error"]


def test_signup_duplicate_email_is_refused_ignoring_case(client, make):
    make.user("taken@example.com")
    assert post(client, "/signup", name="X", email="TAKEN@example.com", password=PASSWORD).status_code == 409


def test_signup_with_a_non_json_body_is_a_clean_400(client):
    assert client.post("/signup", data="plain text", content_type="text/plain").status_code == 400
    assert client.post("/signup", json=["a", "list"]).status_code == 400


# ---------- sign-in ----------
def test_login_success_and_the_two_failures_look_the_same(client, make):
    make.user("real@example.com")
    ok = post(client, "/login", email="Real@Example.com", password=PASSWORD)
    assert ok.status_code == 200 and ok.get_json()["token"]
    wrong = post(client, "/login", email="real@example.com", password="nope")
    unknown = post(client, "/login", email="ghost@example.com", password="nope")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()


@pytest.mark.parametrize("body", [{"email": ["a@b.co"], "password": "x"}, {"email": "a@b.co", "password": {"a": 1}}, {"email": 5, "password": 5}, {}])
def test_login_with_odd_input_is_a_clean_error_not_a_crash(client, body):
    assert client.post("/login", json=body).status_code in (400, 401)


def test_login_is_rate_limited_per_account_and_a_success_resets_it(app, client, make):
    app.config["LOGIN_LIMIT_PER_EMAIL"] = 3
    make.user("limit@example.com")
    for _ in range(3):
        assert post(client, "/login", email="limit@example.com", password="wrong").status_code == 401
    blocked = post(client, "/login", email="limit@example.com", password=PASSWORD)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    # another account is not affected
    make.user("other@example.com")
    assert post(client, "/login", email="other@example.com", password=PASSWORD).status_code == 200


def test_login_attempts_from_one_address_are_limited_too(app, client):
    app.config["LOGIN_LIMIT_PER_IP"] = 4
    codes = [post(client, "/login", email=f"user{i}@example.com", password="x").status_code for i in range(6)]
    assert codes[:4] == [401] * 4
    assert codes[4:] == [429, 429]


def test_signup_is_rate_limited(app, client):
    app.config["SIGNUP_LIMIT_PER_IP"] = 2
    codes = [post(client, "/signup", name="A", email=f"s{i}@example.com", password=PASSWORD).status_code for i in range(4)]
    assert codes == [201, 201, 429, 429]


# ---------- tokens ----------
def test_a_token_for_a_deleted_account_is_refused_with_401_not_500(app, client, make, login):
    uid = make.user("gone@example.com")
    headers = login("gone@example.com")
    with app.app_context():
        db.session.delete(db.session.get(User, uid))
        db.session.commit()
    for url in ("/me", "/projects", "/tasks", "/dashboard/stats", "/users/options"):
        res = client.get(url, headers=headers)
        assert res.status_code == 401, url
        assert "error" in res.get_json()


def test_missing_and_garbage_tokens_get_json_401(client):
    assert client.get("/tasks").status_code == 401
    assert client.get("/tasks").get_json()["error"]
    assert client.get("/tasks", headers={"Authorization": "Bearer garbage"}).status_code == 401


# ---------- the login page ----------
def test_login_page_never_contains_the_admin_password(client):
    page = client.get("/login").get_data(as_text=True)
    assert "Admin@12345" not in page
    assert "Start-Admin-1!" not in page
    assert "admin@taskpilot.dev" not in page


def test_demo_button_exists_only_in_demo_mode(app, client):
    assert 'id="demoMember"' not in client.get("/login").get_data(as_text=True)
    app.config["DEMO_MODE"] = True
    page = client.get("/login").get_data(as_text=True)
    assert 'id="demoMember"' in page and "member@taskpilot.dev" in page
    assert "admin@taskpilot.dev" not in page, "no admin demo, ever"


# ---------- seeded accounts ----------
def test_seed_creates_the_admin_from_the_environment_and_no_demo_member(app):
    from app import seed_accounts

    with app.app_context():
        db.drop_all(); db.create_all()
        seed_accounts(app)
        admin = User.query.filter_by(email="admin@taskpilot.dev").first()
        assert admin.role == "Admin" and admin.check_password("Start-Admin-1!")
        assert User.query.filter_by(email="member@taskpilot.dev").first() is None


def test_seed_creates_the_demo_member_only_in_demo_mode(app):
    from app import seed_accounts

    app.config["DEMO_MODE"] = True
    with app.app_context():
        db.drop_all(); db.create_all()
        seed_accounts(app)
        assert User.query.filter_by(email="member@taskpilot.dev").first().role == "Member"


def test_seed_locks_a_leftover_demo_member_when_demo_mode_is_off(app):
    from app import seed_accounts

    with app.app_context():
        db.drop_all(); db.create_all()
        old = User(name="Demo Member", email="member@taskpilot.dev", role="Member")
        old.set_password("Member@12345")
        db.session.add(old)
        db.session.commit()
        seed_accounts(app)
        assert not User.query.filter_by(email="member@taskpilot.dev").first().check_password("Member@12345")


def test_production_refuses_to_keep_the_published_admin_password(app, monkeypatch):
    from app import seed_accounts

    monkeypatch.setenv("FLASK_ENV", "production")
    with app.app_context():
        db.drop_all(); db.create_all()
        old = User(name="Admin", email="admin@taskpilot.dev", role="Admin")
        old.set_password("Admin@12345")
        db.session.add(old)
        db.session.commit()

        monkeypatch.delenv("ADMIN_PASSWORD")
        with pytest.raises(RuntimeError, match="published default password"):
            seed_accounts(app)

        monkeypatch.setenv("ADMIN_PASSWORD", "A-New-Strong-One-9!")
        seed_accounts(app)
        admin = User.query.filter_by(email="admin@taskpilot.dev").first()
        assert admin.check_password("A-New-Strong-One-9!") and not admin.check_password("Admin@12345")


def test_production_does_not_invent_an_admin_without_a_password(app, monkeypatch, capsys):
    from app import seed_accounts

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("ADMIN_PASSWORD")
    with app.app_context():
        db.drop_all(); db.create_all()
        seed_accounts(app)
        assert User.query.count() == 0
    assert "Set ADMIN_PASSWORD" in capsys.readouterr().err


# ---------- secrets ----------
def _config_in_fresh_process(env):
    base = {"PATH": "", "SYSTEMROOT": "C:\\Windows", "DATABASE_URL": "sqlite://"}
    # empty values stop backend/.env from filling them in
    result = subprocess.run(
        [sys.executable, "-c", "import config; print('ok')"],
        cwd=BACKEND, env={**base, "SECRET_KEY": "", "JWT_SECRET_KEY": "", **env}, capture_output=True, text=True,
    )
    return result


def test_production_will_not_start_without_real_secrets():
    for env in ({"FLASK_ENV": "production"}, {"FLASK_ENV": "production", "SECRET_KEY": "change-me-please-change-me", "JWT_SECRET_KEY": "x" * 40}, {"FLASK_ENV": "production", "SECRET_KEY": "short", "JWT_SECRET_KEY": "x" * 40}):
        result = _config_in_fresh_process(env)
        assert result.returncode != 0 and "must be set to a long random value" in result.stderr, env


def test_production_starts_with_real_secrets_and_development_gets_random_ones():
    assert _config_in_fresh_process({"FLASK_ENV": "production", "SECRET_KEY": "a" * 32, "JWT_SECRET_KEY": "b" * 32}).returncode == 0
    dev = _config_in_fresh_process({})
    assert dev.returncode == 0 and "temporary one" in dev.stderr


# ---------- headers and error shapes ----------
def test_security_headers_and_no_store_on_json(client):
    res = client.get("/login")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert client.post("/login", json={}).headers["Cache-Control"] == "no-store"


def test_api_misses_are_json(client, login, make):
    make.user("a@example.com")
    headers = login("a@example.com")
    res = client.get("/tasks/999999", headers=headers)
    assert res.status_code in (404, 405)
    assert res.is_json


def test_cors_is_off_unless_configured(client):
    res = client.get("/login", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in res.headers
