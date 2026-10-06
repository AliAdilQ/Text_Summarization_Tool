import re

import pytest

from app import create_app
from app.extensions import db
from app.models import Summary, User
from app.services.seed import seed_database


def test_csrf_rejects_form_and_api_mutations(app):
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    assert (
        client.post("/login", data={"identifier": "reader", "password": "Password123!"}).status_code
        == 400
    )
    response = client.post("/api/summarize", json={"text": "word " * 40})
    assert response.status_code == 400
    assert "session expired" in response.json["error"]
    page = client.get("/login")
    token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', page.data).group(1).decode()
    assert (
        client.post(
            "/login", data={"csrf_token": token, "identifier": "reader", "password": "Password123!"}
        ).status_code
        == 302
    )
    assert client.post("/workspace/history/clear").status_code == 400


def test_seed_is_idempotent_and_preserves_existing_passwords(app):
    with app.app_context():
        first = seed_database()
        counts = (
            db.session.scalar(db.select(db.func.count(User.id))),
            db.session.scalar(db.select(db.func.count(Summary.id))),
        )
        admin = db.session.scalar(db.select(User).where(User.username == "admin"))
        original_hash = admin.password_hash
        second = seed_database()
        assert "added 0 users and 0 summaries" in second
        assert counts == (
            db.session.scalar(db.select(db.func.count(User.id))),
            db.session.scalar(db.select(db.func.count(Summary.id))),
        )
        assert admin.password_hash == original_hash
        assert admin.check_password("Password123!")
        demo = db.session.scalar(db.select(User).where(User.username == "demo"))
        assert demo.check_password("Demo123!")
        assert "summaries" in first


def test_seeding_disabled_in_production(app):
    app.config["ENVIRONMENT"] = "production"
    with app.app_context(), pytest.raises(RuntimeError, match="disabled"):
        seed_database()


def test_production_requires_secret():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({"ENVIRONMENT": "production", "SECRET_KEY": None})


def test_security_headers_and_error_pages(client, login):
    response = client.get("/missing-page")
    assert response.status_code == 404
    assert b"A little off the page" in response.data
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "frame-ancestors 'self'" in response.headers["Content-Security-Policy"]
    login()
    assert client.get("/workspace/history").headers["Cache-Control"] == "no-store"
    assert client.get("/admin").status_code == 403


def test_oversized_body_returns_friendly_error(client):
    response = client.post(
        "/api/summarize", data='{"text":"' + "x" * 210_000 + '"}', content_type="application/json"
    )
    assert response.status_code == 413
    assert response.json["error"]


def test_internal_error_does_not_expose_traceback(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/internal-error-test")
    def trigger_error():
        raise RuntimeError("private-error-details")

    response = app.test_client().get("/internal-error-test")
    assert response.status_code == 500
    assert b"Something interrupted the flow" in response.data
    assert b"private-error-details" not in response.data
