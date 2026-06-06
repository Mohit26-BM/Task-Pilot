from datetime import datetime
from re import match


TASK_STATUSES = {"Pending", "In Progress", "Review", "Completed"}
TASK_PRIORITIES = {"Low", "Medium", "High", "Critical"}
TASK_TYPES = {"Bug", "Feature", "Improvement", "Documentation", "Research"}
ROLES = {"Admin", "Member"}


def require_fields(data, fields):
    missing = [field for field in fields if not str(data.get(field, "")).strip()]
    if missing:
        return f"Missing required field(s): {', '.join(missing)}"
    return None


def valid_email(email):
    return bool(match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))


def password_strength_errors(password):
    errors = []
    if len(password or "") < 8:
        errors.append("at least 8 characters")
    if not match(r".*[a-z].*", password or ""):
        errors.append("a lowercase letter")
    if not match(r".*[A-Z].*", password or ""):
        errors.append("an uppercase letter")
    if not match(r".*\d.*", password or ""):
        errors.append("a number")
    if not match(r".*[^A-Za-z0-9].*", password or ""):
        errors.append("a symbol")
    return errors


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()
