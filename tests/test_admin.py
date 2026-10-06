import pytest

from app.extensions import db
from app.models import Summary, User


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/users",
        "/admin/users/2",
        "/admin/summaries",
        "/admin/summaries/2",
        "/admin/summaries/2/download",
    ],
)
def test_members_cannot_read_admin_pages(client, login, path):
    login()
    assert client.get(path).status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/admin/users/2/role",
        "/admin/users/2/status",
        "/admin/users/2/delete",
        "/admin/summaries/2/delete",
    ],
)
def test_members_cannot_mutate_admin_data(client, login, path):
    login()
    assert client.post(path).status_code == 403


@pytest.mark.parametrize(
    "path", ["/admin", "/admin/users", "/admin/users/2", "/admin/summaries", "/admin/summaries/2"]
)
def test_admin_pages_render(client, login, path):
    login("admin")
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("action", ["role", "status", "delete"])
def test_admin_cannot_remove_own_access(client, login, app, action):
    login("admin")
    assert client.post(f"/admin/users/3/{action}").status_code == 302
    with app.app_context():
        user = db.session.get(User, 3)
        assert user.is_admin and user.active


def test_admin_can_manage_normal_users(client, login, app):
    login("admin")
    client.post("/admin/users/2/role")
    with app.app_context():
        assert db.session.get(User, 2).is_admin
    client.post("/admin/users/2/delete")
    with app.app_context():
        assert db.session.get(User, 2) is not None
    client.post("/admin/users/2/role")
    client.post("/admin/users/2/status")
    with app.app_context():
        assert not db.session.get(User, 2).active
    client.post("/admin/users/2/delete")
    with app.app_context():
        assert db.session.get(User, 2) is None
        assert db.session.get(Summary, 2) is None


def test_admin_summary_search_filter_and_deletion(client, login, app):
    login("admin")
    assert b"renewable energy 2" in client.get("/admin/summaries?user_id=2&length=medium").data
    assert b"renewable energy 1" not in client.get("/admin/summaries?user_id=2").data
    assert b"No summaries" in client.get("/admin/summaries?q=unmatched").data
    assert client.post("/admin/summaries/2/delete").status_code == 302
    with app.app_context():
        assert db.session.get(Summary, 2) is None
