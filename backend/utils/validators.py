from datetime import date, datetime
from re import match


TASK_STATUSES = {"Pending", "In Progress", "Review", "Completed"}
TASK_PRIORITIES = {"Low", "Medium", "High", "Critical"}
TASK_TYPES = {"Bug", "Feature", "Improvement", "Documentation", "Research"}
ROLES = {"Admin", "Member"}

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$"


def clean_text(value, label, max_len, required=True):
    """Trimmed text. Returns (text, error). Anything that is not a string (a list, an object, a number) is refused
    rather than crashing later."""
    if value is None:
        value = ""
    if not isinstance(value, str):
        return None, f"{label} must be text."
    text = value.strip()
    if required and not text:
        return None, f"{label} is required."
    if len(text) > max_len:
        return None, f"{label} is too long ({max_len} characters at most)."
    return text, None


def as_id(value):
    """A database id from JSON: a whole number (or digits in a string). Booleans and anything else give None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        number = int(value.strip())
        return number if number > 0 else None
    return None


def clean_email(value):
    """Lower-cased email. Returns (email, error)."""
    if not isinstance(value, str):
        return None, "Please provide a valid email address."
    email = value.strip().lower()
    if len(email) > 255 or not match(EMAIL_PATTERN, email):
        return None, "Please provide a valid email address."
    return email, None


def password_strength_errors(password):
    errors = []
    if not isinstance(password, str):
        return ["at least 8 characters"]
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not match(r".*[a-z].*", password):
        errors.append("a lowercase letter")
    if not match(r".*[A-Z].*", password):
        errors.append("an uppercase letter")
    if not match(r".*\d.*", password):
        errors.append("a number")
    if not match(r".*[^A-Za-z0-9].*", password):
        errors.append("a symbol")
    if len(password) > 128:
        errors.append("at most 128 characters")
    return errors


def parse_date(value):
    """YYYY-MM-DD or empty. Returns (date or None, error)."""
    if value in (None, ""):
        return None, None
    if not isinstance(value, str):
        return None, "The due date must be a date (YYYY-MM-DD)."
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date(), None
    except ValueError:
        return None, "The due date must be a real date in the form YYYY-MM-DD."


def like_escape(text):
    """Make % and _ in a search box mean themselves instead of acting as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


__all__ = [
    "TASK_STATUSES", "TASK_PRIORITIES", "TASK_TYPES", "ROLES",
    "clean_text", "as_id", "clean_email", "password_strength_errors", "parse_date", "like_escape", "date",
]
