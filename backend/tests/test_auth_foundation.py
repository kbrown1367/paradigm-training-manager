import pytest

from app import create_app
from app.auth import (
    ROLE_AGENCY_ADMIN,
    ROLE_PLATFORM_ADMIN,
    hash_password,
    user_is_agency_admin,
    user_is_platform_admin,
    verify_password,
)
from app.extensions import db
from app.models import Agency, User


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_password_hash_round_trip(app):
    with app.app_context():
        hashed = hash_password("PilotPassword123!")

        assert hashed != "PilotPassword123!"
        assert verify_password(
            hashed,
            "PilotPassword123!",
        )
        assert not verify_password(
            hashed,
            "wrong-password",
        )


def test_agency_admin_belongs_to_one_agency(app):
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
            last_name="Admin",
            role=ROLE_AGENCY_ADMIN,
            status="active",
        )

        db.session.add(user)
        db.session.commit()

        assert user.agency_id == agency.id
        assert user.agency == agency
        assert user in agency.users
        assert user_is_agency_admin(user)
        assert not user_is_platform_admin(user)


def test_platform_admin_does_not_require_agency(app):
    with app.app_context():
        user = User(
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

        db.session.add(user)
        db.session.commit()

        assert user.agency_id is None
        assert user_is_platform_admin(user)
        assert not user_is_agency_admin(user)


def test_inactive_user_has_no_active_role(app):
    with app.app_context():
        agency = Agency(
            name="Inactive User Agency",
        )

        db.session.add(agency)
        db.session.flush()

        user = User(
            agency_id=agency.id,
            email="inactive@example.gov",
            password_hash=hash_password(
                "PilotPassword123!"
            ),
            first_name="Inactive",
            last_name="User",
            role=ROLE_AGENCY_ADMIN,
            status="inactive",
        )

        db.session.add(user)
        db.session.commit()

        assert not user_is_agency_admin(user)
        assert not user_is_platform_admin(user)
