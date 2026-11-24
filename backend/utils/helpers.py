from flask import jsonify, request
from flask_jwt_extended import get_current_user


def api_error(message, status=400):
    return jsonify({"error": message}), status


def current_user():
    """The signed-in user. Only call it behind @jwt_required() or role_required: the token's user is looked up there
    (see app.py), and a token whose account no longer exists is refused with 401 before any route code runs."""
    return get_current_user()


def json_body():
    """The request's JSON as a dict. Anything else (a list, text, nothing) counts as an empty object."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}
