import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///placement.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB global max

    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "rishitha")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "rishitha123")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@university.edu")
