import pytest

from app import create_app
from app.auth import (
    ROLE_AGENCY_ADMIN,
    hash_password,
)
from app.extensions import db
from app.models import Agency, User


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def seed_user(app, status="active"):
    with app.app_context():
        agency = Agency(
            name="Pilot Police Department",
        )

        db.session.add(agency)
        db.session.flush()

        user = User(
            agency_id=agency.id,
            email="admin@pilotpd.gov",
            password_hash=hash_password(
                "PilotPassword123!"
            ),
            first_name="Pilot",
            last_name="Administrator",
            role=ROLE_AGENCY_ADMIN,
            status=status,
        )

        db.session.add(user)
        db.session.commit()

        return str(user.id), str(agency.id)


def test_login_creates_authenticated_session(app):
    user_id, agency_id = seed_user(app)

    client = app.test_client()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "ADMIN@PILOTPD.GOV",
            "password": "PilotPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["authenticated"] is True
    assert data["user"]["id"] == user_id
    assert data["user"]["agency_id"] == agency_id
    assert (
        data["user"]["agency"]["name"]
        == "Pilot Police Department"
    )

    with client.session_transaction() as sess:
        assert sess["user_id"] == user_id


def test_login_rejects_bad_password(app):
    seed_user(app)

    client = app.test_client()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@pilotpd.gov",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == (
        "Invalid email or password."
    )


def test_login_rejects_inactive_user(app):
    seed_user(
        app,
        status="inactive",
    )

    client = app.test_client()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@pilotpd.gov",
            "password": "PilotPassword123!",
        },
    )

    assert response.status_code == 401


def test_me_requires_authenticated_session(app):
    client = app.test_client()

    response = client.get(
        "/api/auth/me"
    )

    assert response.status_code == 401
    assert (
        response.get_json()["authenticated"]
        is False
    )


def test_me_returns_authenticated_user(app):
    seed_user(app)

    client = app.test_client()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@pilotpd.gov",
            "password": "PilotPassword123!",
        },
    )

    assert login_response.status_code == 200

    response = client.get(
        "/api/auth/me"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["authenticated"] is True
    assert (
        data["user"]["email"]
        == "admin@pilotpd.gov"
    )


def test_logout_destroys_session(app):
    seed_user(app)

    client = app.test_client()

    client.post(
        "/api/auth/login",
        json={
            "email": "admin@pilotpd.gov",
            "password": "PilotPassword123!",
        },
    )

    response = client.post(
        "/api/auth/logout"
    )

    assert response.status_code == 200
    assert (
        response.get_json()["authenticated"]
        is False
    )

    response = client.get(
        "/api/auth/me"
    )

    assert response.status_code == 401
