"""Environment-backed settings, with development-only secret persistence."""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or None
    ENVIRONMENT = os.getenv("FLASK_ENV", "development")
    TEMPLATES_AUTO_RELOAD = ENVIRONMENT == "development"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///text_summarizer.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 200_000
    MAX_TEXT_CHARACTERS = 50_000
    MIN_TEXT_WORDS = 30
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    MODEL_NAME = os.getenv("MODEL_NAME", "sshleifer/distilbart-cnn-12-6")
    SUMMARIZER_BACKEND = os.getenv("SUMMARIZER_BACKEND", "auto")
    MODEL_ALLOW_DOWNLOAD = os.getenv("MODEL_ALLOW_DOWNLOAD", "false").lower() == "true"
