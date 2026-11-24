import secrets

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models import User
from utils.helpers import api_error, current_user, json_body
from utils.ratelimit import limiter
from utils.validators import clean_email, clean_text, password_strength_errors


auth_bp = Blueprint("auth", __name__)

# A real hash of a throwaway string. An unknown email is checked against it so that a wrong email takes as long
# as a wrong password, and the answer does not reveal which accounts exist.
_DUMMY_HASH = generate_password_hash(secrets.token_hex(16))


def _too_many(wait):
    response, status = api_error("Too many attempts. Please wait a few minutes and try again.", 429)
    response.headers["Retry-After"] = str(wait)
    return response, status


def _issue(user, status=200):
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"token": token, "user": user.to_dict()}), status


@auth_bp.post("/signup")
def signup():
    cfg = current_app.config
    allowed, wait = limiter.hit(f"signup:{request.remote_addr}", cfg["SIGNUP_LIMIT_PER_IP"], cfg["SIGNUP_WINDOW_SECONDS"])
    if not allowed:
        return _too_many(wait)

    data = json_body()
    name, error = clean_text(data.get("name"), "Name", 80)
    if error:
        return api_error(error)
    email, error = clean_email(data.get("email"))
    if error:
        return api_error(error)
    password = data.get("password")
    strength_errors = password_strength_errors(password)
    if strength_errors:
        return api_error(f"Password must include {', '.join(strength_errors)}.")
    if User.query.filter_by(email=email).first():
        return api_error("Email is already registered.", 409)

    # Everyone who signs up is a Member. Admins are made by an existing Admin on the Users page; a "role" sent in
    # the request is deliberately ignored.
    user = User(name=name, email=email, role="Member")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return _issue(user, 201)


@auth_bp.post("/login")
def login():
    cfg = current_app.config
    data = json_body()
    email = data.get("email").strip().lower() if isinstance(data.get("email"), str) else ""
    password = data.get("password") if isinstance(data.get("password"), str) else ""
    if not email or not password:
        return api_error("Missing required field(s): email, password")

    ip_ok, wait_ip = limiter.hit(f"login-ip:{request.remote_addr}", cfg["LOGIN_LIMIT_PER_IP"], cfg["LOGIN_WINDOW_SECONDS"])
    email_ok, wait_email = limiter.hit(f"login-email:{email}", cfg["LOGIN_LIMIT_PER_EMAIL"], cfg["LOGIN_WINDOW_SECONDS"])
    if not (ip_ok and email_ok):
        return _too_many(max(wait_ip, wait_email))

    user = User.query.filter_by(email=email).first()
    password_ok = check_password_hash(user.password_hash if user else _DUMMY_HASH, password)
    if not user or not password_ok:
        return api_error("Invalid email or password.", 401)

    limiter.clear(f"login-email:{email}")
    return _issue(user)


@auth_bp.get("/me")
@jwt_required()
def me():
    return jsonify(current_user().to_dict())
