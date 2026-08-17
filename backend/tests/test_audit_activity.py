import pytest

from app import create_app
from app.auth import (
    ROLE_AGENCY_ADMIN,
    hash_password,
)
from app.extensions import db
from app.models import (
    Agency,
    AuditEvent,
    User,
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY":
                "audit-activity-test-secret",
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_authenticated_admin_change_records_full_audit_context(
    app,
):
    with app.app_context():
        agency = Agency(
            name="Audit Test Police Department",
            status="active",
        )

        db.session.add(agency)
        db.session.flush()

        user = User(
            agency_id=agency.id,
            email="audit-admin@example.gov",
            password_hash=hash_password(
                "AuditPassword123!"
            ),
            first_name="Audit",
            last_name="Administrator",
            role=ROLE_AGENCY_ADMIN,
            status="active",
        )

        db.session.add(user)
        db.session.commit()

        agency_id = agency.id
        user_id = user.id

    client = app.test_client()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email":
                "audit-admin@example.gov",
            "password":
                "AuditPassword123!",
        },
    )

    assert login_response.status_code == 200

    response = client.patch(
        f"/api/agencies/{agency_id}"
        "/email-configuration",
        json={
            "email_domain":
                "audit-example.gov",
            "email_pattern":
                "FIRST_DOT_LAST",
        },
    )

    assert response.status_code == 200

    with app.app_context():
        event = (
            AuditEvent.query.filter_by(
                agency_id=agency_id,
                user_id=user_id,
                event_type=(
                    "AGENCY_EMAIL_CONFIGURATION_UPDATED"
                ),
            )
            .order_by(
                AuditEvent.created_at.desc()
            )
            .first()
        )

        assert event is not None
        assert event.object_type == "AGENCY"
        assert event.object_id == str(agency_id)
        assert event.result == "success"

        assert event.details[
            "email_domain"
        ] == {
            "old": None,
            "new": "audit-example.gov",
        }

        assert event.details[
            "email_pattern"
        ] == {
            "old": None,
            "new": "FIRST_DOT_LAST",
        }


def test_login_event_contains_user_object_context(
    app,
):
    with app.app_context():
        agency = Agency(
            name="Login Audit Police Department",
            status="active",
        )

        db.session.add(agency)
        db.session.flush()

        user = User(
            agency_id=agency.id,
            email="login-audit@example.gov",
            password_hash=hash_password(
                "LoginAuditPassword123!"
            ),
            first_name="Login",
            last_name="Audit",
            role=ROLE_AGENCY_ADMIN,
            status="active",
        )

        db.session.add(user)
        db.session.commit()

        agency_id = agency.id
        user_id = user.id

    client = app.test_client()

    response = client.post(
        "/api/auth/login",
        json={
            "email":
                "login-audit@example.gov",
            "password":
                "LoginAuditPassword123!",
        },
    )

    assert response.status_code == 200

    with app.app_context():
        event = (
            AuditEvent.query.filter_by(
                agency_id=agency_id,
                user_id=user_id,
                event_type="AUTH_LOGIN_SUCCESS",
            )
            .order_by(
                AuditEvent.created_at.desc()
            )
            .first()
        )

        assert event is not None
        assert event.object_type == "USER"
        assert event.object_id == str(user_id)
        assert event.result == "success"
