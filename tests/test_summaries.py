import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Summary
from app.services.seed import SAMPLE_ARTICLES


def test_guest_generation_does_not_save(client, app):
    response = client.post(
        "/api/summarize", json={"text": SAMPLE_ARTICLES[0][1], "length": "short"}
    )
    assert response.status_code == 200
    result = response.json
    assert result["summary"]
    assert result["summary_word_count"] < result["original_word_count"]
    assert 0 < result["compression_ratio"] < 100
    assert result["method"] == "extractive"
    assert not result["saved"]
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Summary.id))) == 2


def test_generation_saves_authenticated_history(client, login, app):
    login()
    response = client.post("/api/summarize", json={"text": SAMPLE_ARTICLES[1][1], "length": "long"})
    assert response.json["saved"]
    assert client.get(response.json["detail_url"]).status_code == 200
    with app.app_context():
        summary = db.session.get(Summary, response.json["id"])
        assert summary.user_id == 1
        assert summary.summary_length == "long"


@pytest.mark.parametrize(
    "payload",
    [
        {"text": ""},
        {"text": "Too short to summarize."},
        {"text": "word " * 10001},
        {"text": SAMPLE_ARTICLES[0][1], "length": "huge"},
        {"text": " " * 40},
    ],
)
def test_validation(client, payload):
    response = client.post("/api/summarize", json=payload)
    assert response.status_code == 422
    assert response.json["error"]


@pytest.mark.parametrize("payload", [None, [], {"text": 42}, {"text": "valid", "length": []}])
def test_malformed_json(client, payload):
    assert client.post("/api/summarize", json=payload).status_code == 400


@pytest.mark.parametrize("path", ["/workspace/summaries/2", "/workspace/summaries/2/download"])
def test_private_summary_read_permissions(client, login, path):
    login()
    assert client.get(path).status_code == 404


def test_private_summary_delete_permissions(client, login, app):
    login()
    assert client.post("/workspace/summaries/2/delete").status_code == 404
    with app.app_context():
        assert db.session.get(Summary, 2) is not None


def test_history_and_clear_are_scoped_to_current_user(client, login, app):
    login()
    response = client.get("/workspace/history")
    assert b"renewable energy 1" in response.data
    assert b"renewable energy 2" not in response.data
    assert client.post("/workspace/history/clear").status_code == 302
    with app.app_context():
        assert db.session.get(Summary, 1) is None
        assert db.session.get(Summary, 2) is not None


def test_copy_download_delete_detail(client, login):
    login()
    assert b"saved-summary" in client.get("/workspace/summaries/1").data
    response = client.get("/workspace/summaries/1/download")
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.mimetype == "text/plain"
    assert client.post("/workspace/summaries/1/delete").status_code == 302
    assert client.get("/workspace/summaries/1").status_code == 404


def test_rendered_user_content_is_escaped(client, login, app):
    with app.app_context():
        summary = db.session.get(Summary, 1)
        summary.original_text = '<script>alert("bad")</script>'
        db.session.commit()
    login()
    response = client.get("/workspace/summaries/1")
    assert b"&lt;script&gt;" in response.data
    assert b'<script>alert("bad")</script>' not in response.data


def test_history_filter_and_literal_search(client, login):
    login()
    assert b"renewable energy" in client.get("/workspace/history?length=medium").data
    assert b"No summaries" in client.get("/workspace/history?length=short").data
    assert b"No summaries" in client.get("/workspace/history?q=%25").data


def test_save_failure_preserves_generated_result(client, login, monkeypatch):
    login()

    def fail_commit():
        raise SQLAlchemyError("Storage unavailable")

    monkeypatch.setattr(db.session, "commit", fail_commit)
    response = client.post("/api/summarize", json={"text": SAMPLE_ARTICLES[0][1]})
    assert response.status_code == 200
    assert response.json["summary"]
    assert not response.json["saved"]
    assert "couldn't be saved" in response.json["notice"]
