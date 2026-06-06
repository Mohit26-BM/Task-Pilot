from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from models import User


def api_error(message, status=400):
    return jsonify({"error": message}), status


def current_user():
    identity = get_jwt_identity()
    return User.query.get(int(identity)) if identity else None
