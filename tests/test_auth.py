import pytest

from app.extensions import db
from app.models import User


@pytest.mark.parametrize("path", ["/", "/about", "/summarizer", "/login", "/register", "/health"])
def test_public_pages(client, path):
    assert client.get(path).status_code == 200


def test_registration_hashes_password(client, app):
    response = client.post(
        "/register",
        data={
            "username": "New_Reader",
            "email": "NEW@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.username == "new_reader"))
        assert user.email == "new@example.com"
        assert user.check_password("StrongPass123!")
        assert user.password_hash != "StrongPass123!"
        assert not user.is_admin
    assert client.get("/workspace").status_code == 200


def test_registration_rejects_duplicates_and_short_password(client, app):
    response = client.post(
        "/register",
        data={
            "username": "reader",
            "email": "reader@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    assert b"already registered" in response.data
    response = client.post(
        "/register",
        data={"username": "new", "email": "bad", "password": "tiny", "confirm_password": "other"},
    )
    assert response.status_code == 200
    assert b"Invalid email" in response.data
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(User.id))) == 3


def test_login_logout_and_last_login(client, login, app):
    assert login(password="wrong").status_code == 200
    assert client.get("/workspace").status_code == 302
    assert login().status_code == 302
    with app.app_context():
        assert db.session.get(User, 1).last_login is not None
    assert client.get("/workspace").status_code == 200
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 302
    assert client.get("/workspace").status_code == 302


@pytest.mark.parametrize(
    "next_url",
    [
        "https://malicious.example/",
        "//malicious.example/",
        "/\\malicious.example/",
        "/\nmalicious.example/",
    ],
)
def test_login_blocks_open_redirect(client, next_url):
    response = client.post(
        "/login",
        query_string={"next": next_url},
        data={"identifier": "reader", "password": "Password123!"},
    )
    assert response.location == "/workspace"


def test_login_accepts_local_next(client):
    response = client.post(
        "/login?next=/workspace/history",
        data={"identifier": "reader@example.com", "password": "Password123!"},
    )
    assert response.location == "/workspace/history"


@pytest.mark.parametrize(
    "path",
    [
        "/workspace",
        "/workspace/history",
        "/workspace/profile",
        "/workspace/summaries/1",
        "/admin",
        "/admin/users",
        "/admin/summaries",
    ],
)
def test_authentication_required(client, path):
    assert client.get(path).status_code == 302


def test_deactivated_account_and_existing_session(client, login, app):
    login()
    with app.app_context():
        db.session.get(User, 1).active = False
        db.session.commit()
    assert client.get("/workspace").status_code == 302
    assert login().status_code == 200
    assert client.get("/workspace").status_code == 302


def test_profile_update_and_duplicate_prevention(client, login, app):
    login()
    assert client.get("/workspace/profile").status_code == 200
    response = client.post(
        "/workspace/profile", data={"username": "other", "email": "other@example.com"}
    )
    assert b"already in use" in response.data
    assert (
        client.post(
            "/workspace/profile", data={"username": "updated", "email": "updated@example.com"}
        ).status_code
        == 302
    )
    with app.app_context():
        assert db.session.get(User, 1).username == "updated"
