from functools import wraps
from urllib.parse import urlsplit

from flask import abort, make_response
from flask_login import current_user, login_required


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def safe_next(value):
    if not value or "\\" in value or any(ord(char) < 32 for char in value):
        return None
    parsed = urlsplit(value)
    return (
        value
        if not parsed.scheme
        and not parsed.netloc
        and value.startswith("/")
        and not value.startswith("//")
        else None
    )


def download_response(summary):
    response = make_response(summary.summarized_text + "\n")
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="summary-{summary.id}.txt"'
    return response
