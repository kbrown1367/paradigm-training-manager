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



def test_change_password_requires_authenticated_session(app):
    client = app.test_client()

    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password":
                "PilotPassword123!",
            "new_password":
                "ChangedPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == (
        "Authentication required."
    )


def test_change_password_rejects_wrong_current_password(app):
    seed_user(app)

    client = app.test_client()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email":
                "admin@pilotpd.gov",
            "password":
                "PilotPassword123!",
        },
    )

    assert login_response.status_code == 200

    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password":
                "WrongPassword123!",
            "new_password":
                "ChangedPassword123!",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "Current password is incorrect."
    )


def test_change_password_rejects_short_new_password(app):
    seed_user(app)

    client = app.test_client()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email":
                "admin@pilotpd.gov",
            "password":
                "PilotPassword123!",
        },
    )

    assert login_response.status_code == 200

    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password":
                "PilotPassword123!",
            "new_password":
                "short",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "New password must be at least "
        "12 characters."
    )


def test_change_password_rejects_same_password(app):
    seed_user(app)

    client = app.test_client()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email":
                "admin@pilotpd.gov",
            "password":
                "PilotPassword123!",
        },
    )

    assert login_response.status_code == 200

    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password":
                "PilotPassword123!",
            "new_password":
                "PilotPassword123!",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "New password must be different "
        "from the current password."
    )


def test_change_password_updates_credentials_and_keeps_session(app):
    seed_user(app)

    client = app.test_client()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email":
                "admin@pilotpd.gov",
            "password":
                "PilotPassword123!",
        },
    )

    assert login_response.status_code == 200

    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password":
                "PilotPassword123!",
            "new_password":
                "ChangedPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == (
        "Password changed successfully."
    )

    me_response = client.get(
        "/api/auth/me"
    )

    assert me_response.status_code == 200
    assert (
        me_response.get_json()["authenticated"]
        is True
    )

    logout_response = client.post(
        "/api/auth/logout"
    )

    assert logout_response.status_code == 200

    old_login = client.post(
        "/api/auth/login",
        json={
            "email":
                "admin@pilotpd.gov",
            "password":
                "PilotPassword123!",
        },
    )

    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={
            "email":
                "admin@pilotpd.gov",
            "password":
                "ChangedPassword123!",
        },
    )

    assert new_login.status_code == 200


def test_me_returns_onboarding_completion_state(app):
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

    assert (
        response.get_json()["user"][
            "onboarding_completed_at"
        ]
        is None
    )


def test_complete_onboarding_requires_authentication(app):
    client = app.test_client()

    response = client.post(
        "/api/auth/complete-onboarding"
    )

    assert response.status_code == 401


def test_agency_admin_can_complete_onboarding(app):
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

    response = client.post(
        "/api/auth/complete-onboarding"
    )

    assert response.status_code == 200

    result = response.get_json()

    assert result["completed"] is True
    assert (
        result["onboarding_completed_at"]
        is not None
    )

    me_response = client.get(
        "/api/auth/me"
    )

    assert me_response.status_code == 200

    assert (
        me_response.get_json()["user"][
            "onboarding_completed_at"
        ]
        is not None
    )


def test_complete_onboarding_is_idempotent(app):
    seed_user(app)

    client = app.test_client()

    client.post(
        "/api/auth/login",
        json={
            "email": "admin@pilotpd.gov",
            "password": "PilotPassword123!",
        },
    )

    first = client.post(
        "/api/auth/complete-onboarding"
    )

    assert first.status_code == 200

    first_value = first.get_json()[
        "onboarding_completed_at"
    ]

    second = client.post(
        "/api/auth/complete-onboarding"
    )

    assert second.status_code == 200

    assert (
        second.get_json()[
            "onboarding_completed_at"
        ]
        == first_value
    )
