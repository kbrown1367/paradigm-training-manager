# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import os
from datetime import timedelta
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


def database_url():
    """
    Return the configured PTM database URL.

    Production must always use PostgreSQL. Falling back to
    the local SQLite development database in production would
    risk starting PTM against the wrong datastore.
    """
    configured = os.getenv(
        "DATABASE_URL"
    )

    if configured:
        value = normalize_database_url(
            configured
        )
    elif environment_name() == "production":
        raise RuntimeError(
            "DATABASE_URL is required "
            "when PTM_ENV=production."
        )
    else:
        value = "sqlite:///ptm.db"

    if (
        environment_name() == "production"
        and not value.startswith(
            "postgresql+psycopg://"
        )
    ):
        raise RuntimeError(
            "Production DATABASE_URL "
            "must use PostgreSQL."
        )

    return value


def sqlalchemy_engine_options(
    database_uri,
):
    """
    Apply connection-health settings appropriate for
    long-running PostgreSQL application processes.
    """
    if database_uri.startswith(
        "postgresql+psycopg://"
    ):
        return {
            "pool_pre_ping": True,
        }

    return {}



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
        enabled = (
            configured
            .strip()
            .lower()
            == "true"
        )

        if (
            environment_name()
            == "production"
            and not enabled
        ):
            raise RuntimeError(
                "SESSION_COOKIE_SECURE cannot "
                "be disabled when "
                "PTM_ENV=production."
            )

        return enabled

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

    # Administrative sessions should not remain valid
    # for Flask's default 31-day permanent-session period.
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=12,
    )

    # TCOLE source reports are expected to be far smaller
    # than this ceiling, including large-agency imports.
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    SQLALCHEMY_DATABASE_URI = database_url()

    SQLALCHEMY_ENGINE_OPTIONS = (
        sqlalchemy_engine_options(
            SQLALCHEMY_DATABASE_URI
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
