from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.auth import (
    ROLE_AGENCY_ADMIN,
    ROLE_PLATFORM_ADMIN,
    hash_password,
)
from app.extensions import db
from app.models import Agency, User


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY":
                "invitation-test-secret",
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()

        agency = Agency(
            name="Invitation Police Department",
        )

        platform_admin = User(
            agency_id=None,
            email="platform@paradigm.local",
            password_hash=hash_password(
                "PlatformPassword123!"
            ),
            first_name="Platform",
            last_name="Admin",
            role=ROLE_PLATFORM_ADMIN,
            status="active",
        )

        db.session.add_all(
            [
                agency,
                platform_admin,
            ]
        )

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def login_platform(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email":
                "platform@paradigm.local",
            "password":
                "PlatformPassword123!",
        },
    )

    assert response.status_code == 200


def get_agency_id(app):
    with app.app_context():
        agency = Agency.query.one()
        return str(agency.id)


def create_invitation(app, client):
    agency_id = get_agency_id(app)

    response = client.post(
        f"/api/platform/agencies/{agency_id}"
        "/administrators",
        json={
            "first_name": "Invited",
            "last_name": "Administrator",
            "email":
                "invited@example.gov",
        },
    )

    assert response.status_code == 201

    return response.get_json()


def token_from_path(path):
    return path.split(
        "?token=",
        1,
    )[1]


def test_platform_admin_creates_pending_invitation(app):
    client = app.test_client()
    login_platform(client)

    result = create_invitation(
        app,
        client,
    )

    assert (
        result["status"]
        == "pending_invitation"
    )

    assert result["invitation_path"].startswith(
        "/activate?token="
    )

    with app.app_context():
        user = User.query.filter_by(
            email="invited@example.gov"
        ).one()

        assert user.password_hash is None
        assert (
            user.invitation_token_hash
            is not None
        )
        assert (
            user.invitation_expires_at
            is not None
        )


def test_pending_invitation_cannot_log_in(app):
    client = app.test_client()
    login_platform(client)

    create_invitation(
        app,
        client,
    )

    client.post("/api/auth/logout")

    response = client.post(
        "/api/auth/login",
        json={
            "email":
                "invited@example.gov",
            "password":
                "AnythingPassword123!",
        },
    )

    assert response.status_code == 401


def test_valid_invitation_can_be_viewed(app):
    client = app.test_client()
    login_platform(client)

    result = create_invitation(
        app,
        client,
    )

    token = token_from_path(
        result["invitation_path"]
    )

    response = client.get(
        f"/api/auth/invitation?token={token}"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert (
        data["email"]
        == "invited@example.gov"
    )

    assert (
        data["agency"]
        == "Invitation Police Department"
    )


def test_invitation_rejects_short_password(app):
    client = app.test_client()
    login_platform(client)

    result = create_invitation(
        app,
        client,
    )

    token = token_from_path(
        result["invitation_path"]
    )

    response = client.post(
        "/api/auth/activate-invitation",
        json={
            "token": token,
            "password": "short",
        },
    )

    assert response.status_code == 400


def test_invitation_activation_enables_login(app):
    client = app.test_client()
    login_platform(client)

    result = create_invitation(
        app,
        client,
    )

    token = token_from_path(
        result["invitation_path"]
    )

    response = client.post(
        "/api/auth/activate-invitation",
        json={
            "token": token,
            "password":
                "ActivatedPassword123!",
        },
    )

    assert response.status_code == 200

    client.post("/api/auth/logout")

    login = client.post(
        "/api/auth/login",
        json={
            "email":
                "invited@example.gov",
            "password":
                "ActivatedPassword123!",
        },
    )

    assert login.status_code == 200


def test_used_invitation_cannot_be_reused(app):
    client = app.test_client()
    login_platform(client)

    result = create_invitation(
        app,
        client,
    )

    token = token_from_path(
        result["invitation_path"]
    )

    first = client.post(
        "/api/auth/activate-invitation",
        json={
            "token": token,
            "password":
                "ActivatedPassword123!",
        },
    )

    assert first.status_code == 200

    second = client.post(
        "/api/auth/activate-invitation",
        json={
            "token": token,
            "password":
                "AnotherPassword123!",
        },
    )

    assert second.status_code == 404


def test_expired_invitation_is_rejected(app):
    client = app.test_client()
    login_platform(client)

    result = create_invitation(
        app,
        client,
    )

    token = token_from_path(
        result["invitation_path"]
    )

    with app.app_context():
        user = User.query.filter_by(
            email="invited@example.gov"
        ).one()

        user.invitation_expires_at = (
            datetime.now(timezone.utc)
            - timedelta(hours=1)
        )

        db.session.commit()

    response = client.get(
        f"/api/auth/invitation?token={token}"
    )

    assert response.status_code == 410


def test_resend_invalidates_previous_invitation(app):
    client = app.test_client()
    login_platform(client)

    result = create_invitation(
        app,
        client,
    )

    agency_id = get_agency_id(app)

    old_token = token_from_path(
        result["invitation_path"]
    )

    user_id = result["id"]

    resend = client.post(
        f"/api/platform/agencies/{agency_id}"
        f"/administrators/{user_id}"
        "/resend-invitation"
    )

    assert resend.status_code == 200

    new_result = resend.get_json()

    new_token = token_from_path(
        new_result["invitation_path"]
    )

    assert new_token != old_token

    old_response = client.get(
        "/api/auth/invitation"
        f"?token={old_token}"
    )

    assert old_response.status_code == 404

    new_response = client.get(
        "/api/auth/invitation"
        f"?token={new_token}"
    )

    assert new_response.status_code == 200


def test_active_user_cannot_receive_new_invitation(app):
    client = app.test_client()
    login_platform(client)

    result = create_invitation(
        app,
        client,
    )

    token = token_from_path(
        result["invitation_path"]
    )

    activated = client.post(
        "/api/auth/activate-invitation",
        json={
            "token": token,
            "password":
                "ActivatedPassword123!",
        },
    )

    assert activated.status_code == 200

    agency_id = get_agency_id(app)

    resend = client.post(
        f"/api/platform/agencies/{agency_id}"
        f"/administrators/{result['id']}"
        "/resend-invitation"
    )

    assert resend.status_code == 400


def test_duplicate_invited_email_is_rejected(app):
    client = app.test_client()
    login_platform(client)

    create_invitation(
        app,
        client,
    )

    agency_id = get_agency_id(app)

    response = client.post(
        f"/api/platform/agencies/{agency_id}"
        "/administrators",
        json={
            "first_name": "Duplicate",
            "last_name": "User",
            "email":
                "INVITED@example.gov",
        },
    )

    assert response.status_code == 409
