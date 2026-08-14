# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import os
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def normalize_database_url(value):
    """
    Normalize Render/PostgreSQL URLs for the psycopg 3
    driver used by PTM.
    """
    if not value:
        return value

    if value.startswith(
        "postgres://"
    ):
        value = (
            "postgresql://"
            + value[len("postgres://"):]
        )

    if value.startswith(
        "postgresql://"
    ):
        value = (
            "postgresql+psycopg://"
            + value[
                len("postgresql://"):
            ]
        )

    return value


def environment_name():
    return (
        os.getenv(
            "PTM_ENV",
            "development",
        )
        .strip()
        .lower()
    )


def session_cookie_secure():
    configured = os.getenv(
        "SESSION_COOKIE_SECURE"
    )

    if configured is not None:
        return (
            configured
            .strip()
            .lower()
            == "true"
        )

    return (
        environment_name()
        == "production"
    )


def secret_key():
    configured = os.getenv(
        "SECRET_KEY"
    )

    if configured:
        return configured

    if (
        environment_name()
        == "production"
    ):
        raise RuntimeError(
            "SECRET_KEY is required "
            "when PTM_ENV=production."
        )

    return (
        "ptm-local-development-secret-"
        "change-before-production"
    )


class Config:
    PTM_ENV = environment_name()

    SECRET_KEY = secret_key()

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        session_cookie_secure()
    )

    SQLALCHEMY_DATABASE_URI = (
        normalize_database_url(
            os.getenv(
                "DATABASE_URL",
                "sqlite:///ptm.db",
            )
        )
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    FRONTEND_DIST_DIR = os.getenv(
        "FRONTEND_DIST_DIR",
        str(
            PROJECT_ROOT
            / "frontend"
            / "dist"
        ),
    )
