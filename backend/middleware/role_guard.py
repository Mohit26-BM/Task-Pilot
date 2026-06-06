from functools import wraps

from flask_jwt_extended import verify_jwt_in_request

from utils.helpers import api_error, current_user


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user()
            if not user or user.role not in roles:
                return api_error("You do not have permission to perform this action.", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
