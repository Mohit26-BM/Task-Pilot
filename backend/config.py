import os
import secrets
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load backend/.env here, before anything below reads the environment. (Loading it later, as app.py used to,
# meant the values in .env never reached SECRET_KEY / JWT_SECRET_KEY, which are read when this module is imported.)
load_dotenv(BASE_DIR / ".env")


def is_production():
    return os.getenv("FLASK_ENV", "").lower() == "production" or os.getenv("APP_ENV", "").lower() == "production"


_PLACEHOLDERS = ("change-me", "changeme", "replace-with", "change-this")


def _secret(name):
    """A signing secret. In production it must be set to something long and real; in development a missing one
    becomes a random value for this run, so there is never a guessable default that would let anyone forge a login."""
    value = os.getenv(name, "")
    weak = len(value) < 16 or any(p in value.lower() for p in _PLACEHOLDERS)
    if not weak:
        return value
    if is_production():
        raise RuntimeError(f"{name} must be set to a long random value (16+ characters) in production.")
    print(f"[taskpilot] {name} is missing or weak; using a temporary one. Logins reset on restart. Set it in backend/.env.", file=sys.stderr)
    return secrets.token_hex(32)


def _int(name, default, low, high):
    try:
        value = int(os.getenv(name, ""))
    except ValueError:
        return default
    return value if low <= value <= high else default


class Config:
    SECRET_KEY = _secret("SECRET_KEY")
    JWT_SECRET_KEY = _secret("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'database' / 'taskpilot.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 256 * 1024  # no request here needs more than a few KB

    # Sign-in and sign-up limits (attempts per window), per address and per account. Counted in memory per worker.
    LOGIN_LIMIT_PER_EMAIL = _int("LOGIN_LIMIT_PER_EMAIL", 8, 1, 1000)
    LOGIN_LIMIT_PER_IP = _int("LOGIN_LIMIT_PER_IP", 30, 1, 10000)
    SIGNUP_LIMIT_PER_IP = _int("SIGNUP_LIMIT_PER_IP", 10, 1, 10000)
    LOGIN_WINDOW_SECONDS = 15 * 60
    SIGNUP_WINDOW_SECONDS = 60 * 60

    # A shared demo Member account on the login page, for showing the app off. Off unless DEMO_MODE=1.
    DEMO_MODE = os.getenv("DEMO_MODE", "") == "1"
    DEMO_MEMBER_EMAIL = "member@taskpilot.dev"
    DEMO_MEMBER_PASSWORD = os.getenv("DEMO_MEMBER_PASSWORD", "Member@12345")
