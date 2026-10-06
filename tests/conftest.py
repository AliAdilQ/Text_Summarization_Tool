import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Summary, User
from app.services.seed import SAMPLE_ARTICLES
from app.services.summarizer import extractive_summary, word_count


@pytest.fixture(scope="session")
def test_password_hash():
    return generate_password_hash("Password123!")


@pytest.fixture
def app(test_password_hash):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "testing-key-not-for-deployment",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
            "SUMMARIZER_BACKEND": "extractive",
            "ENVIRONMENT": "development",
        }
    )
    with application.app_context():
        for name, admin in [("reader", False), ("other", False), ("admin", True)]:
            user = User(username=name, email=f"{name}@example.com", is_admin=admin)
            user.password_hash = test_password_hash
            db.session.add(user)
        db.session.flush()
        title, text = SAMPLE_ARTICLES[0]
        result = extractive_summary(text)
        for owner_id in (1, 2):
            db.session.add(
                Summary(
                    user_id=owner_id,
                    title=f"{title} {owner_id}",
                    original_text=text,
                    summarized_text=result,
                    summary_length="medium",
                    original_word_count=word_count(text),
                    summary_word_count=word_count(result),
                    compression_ratio=70,
                    processing_time=0.02,
                    method="extractive",
                )
            )
        db.session.commit()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def sign_in(name="reader", password="Password123!"):
        return client.post("/login", data={"identifier": name, "password": password})

    return sign_in
