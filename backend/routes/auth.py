from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required

from database import db
from models import User
from utils.helpers import api_error, current_user
from utils.validators import ROLES, password_strength_errors, require_fields, valid_email


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/signup")
def signup():
    data = request.get_json() or {}
    error = require_fields(data, ["name", "email", "password"])
    if error:
        return api_error(error)
    if not valid_email(data["email"]):
        return api_error("Please provide a valid email address.")
    strength_errors = password_strength_errors(data["password"])
    if strength_errors:
        return api_error(f"Password must include {', '.join(strength_errors)}.")
    if User.query.filter_by(email=data["email"].lower()).first():
        return api_error("Email is already registered.", 409)

    role = data.get("role", "Member")
    if role not in ROLES:
        role = "Member"

    user = User(name=data["name"].strip(), email=data["email"].lower().strip(), role=role)
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"token": token, "user": user.to_dict()}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    error = require_fields(data, ["email", "password"])
    if error:
        return api_error(error)

    user = User.query.filter_by(email=data["email"].lower().strip()).first()
    if not user or not user.check_password(data["password"]):
        return api_error("Invalid email or password.", 401)

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"token": token, "user": user.to_dict()})


@auth_bp.get("/me")
@jwt_required()
def me():
    user = current_user()
    if not user:
        return api_error("User not found.", 404)
    return jsonify(user.to_dict())
