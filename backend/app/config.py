import os


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "ptm-local-development-secret-change-before-production",
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        os.getenv(
            "SESSION_COOKIE_SECURE",
            "false",
        ).lower()
        == "true"
    )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///ptm.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
