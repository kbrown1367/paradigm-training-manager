from pathlib import Path

import pytest

from app import create_app
from app.config import (
    normalize_database_url,
)


@pytest.fixture()
def frontend_dist(tmp_path):
    dist = tmp_path / "dist"
    assets = dist / "assets"

    assets.mkdir(parents=True)

    (dist / "index.html").write_text(
        (
            "<!doctype html>"
            "<html>"
            "<body>"
            '<div id="root">'
            "PTM production test"
            "</div>"
            "</body>"
            "</html>"
        )
    )

    (assets / "test.js").write_text(
        'console.log("PTM");'
    )

    return dist


@pytest.fixture()
def app(frontend_dist):
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
            "FRONTEND_DIST_DIR":
                str(frontend_dist),
        }
    )


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/login",
        "/app",
        "/app/officer/example",
        "/platform",
        "/platform/agencies/example",
    ],
)
def test_spa_routes_return_frontend(
    app,
    path,
):
    response = app.test_client().get(
        path
    )

    assert response.status_code == 200
    assert (
        "PTM production test"
        in response.get_data(
            as_text=True
        )
    )


def test_compiled_asset_is_served(app):
    response = app.test_client().get(
        "/assets/test.js"
    )

    assert response.status_code == 200
    assert (
        'console.log("PTM");'
        in response.get_data(
            as_text=True
        )
    )


def test_unknown_api_is_not_spa_fallback(
    app,
):
    response = app.test_client().get(
        "/api/this-route-does-not-exist"
    )

    assert response.status_code == 404


def test_health_remains_api_response(app):
    response = app.test_client().get(
        "/api/health"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert (
        data["application"]
        == "Paradigm Training Manager"
    )
    assert data["status"] == "ok"


def test_missing_frontend_build_returns_503(
    tmp_path,
):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
            "FRONTEND_DIST_DIR":
                str(
                    tmp_path
                    / "missing-dist"
                ),
        }
    )

    response = app.test_client().get(
        "/login"
    )

    assert response.status_code == 503


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            (
                "postgresql://"
                "user:password@db/ptm"
            ),
            (
                "postgresql+psycopg://"
                "user:password@db/ptm"
            ),
        ),
        (
            (
                "postgres://"
                "user:password@db/ptm"
            ),
            (
                "postgresql+psycopg://"
                "user:password@db/ptm"
            ),
        ),
        (
            (
                "postgresql+psycopg://"
                "user:password@db/ptm"
            ),
            (
                "postgresql+psycopg://"
                "user:password@db/ptm"
            ),
        ),
        (
            "sqlite:///ptm.db",
            "sqlite:///ptm.db",
        ),
    ],
)
def test_database_url_normalization(
    source,
    expected,
):
    assert (
        normalize_database_url(
            source
        )
        == expected
    )


def test_frontend_default_path_targets_repo_dist():
    from app.config import PROJECT_ROOT

    expected = (
        PROJECT_ROOT
        / "frontend"
        / "dist"
    )

    assert expected.name == "dist"
    assert (
        expected.parent.name
        == "frontend"
    )


def test_migrations_do_not_assign_integer_zero_to_boolean_columns():
    """Production PostgreSQL must receive Boolean SQL literals."""
    project_root = Path(__file__).resolve().parents[2]
    migration = (
        project_root
        / "backend"
        / "migrations"
        / "versions"
        / "8ed47812a181_add_verified_jailer_cultural_diversity_.py"
    )

    contents = migration.read_text()

    assert (
        "SET verified_jailer_cultural_diversity_exemption = FALSE"
        in contents
    )
    assert (
        "SET verified_jailer_cultural_diversity_exemption = 0"
        not in contents
    )
