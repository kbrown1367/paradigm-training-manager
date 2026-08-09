from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAward,
    TrainingRecord,
)
from app.services.compliance_email import (
    build_compliance_email,
)


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


def make_officer():
    agency = Agency(
        name="Test Police Department",
        email_domain="example.gov",
        email_pattern="FIRST_INITIAL_LAST",
    )

    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="Jane",
        last_name="Smith",
    )

    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Peace Officer License",
            award_date=date(2020, 1, 1),
        )
    )

    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="9999",
            course_title="General Training",
            course_date=date(2026, 1, 1),
            credited_hours=Decimal("8.00"),
            hours_source="TCOLE",
            source="TCOLE",
        )
    )

    db.session.commit()

    return officer


def test_compliance_email_uses_resolved_address(app):
    with app.app_context():
        officer = make_officer()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["recipient"] == (
            "jsmith@example.gov"
        )
        assert result["can_email"] is True


def test_compliance_email_contains_status(app):
    with app.app_context():
        officer = make_officer()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert "Current Status:" in result["body"]
        assert (
            "TCOLE Training Compliance Status"
            == result["subject"]
        )


def test_compliance_email_contains_due_items(app):
    with app.app_context():
        officer = make_officer()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert (
            "OUTSTANDING REQUIREMENTS"
            in result["body"]
        )
        assert "Due 8/31/2027" in result["body"]


def test_compliance_email_without_address_is_disabled(
    app,
):
    with app.app_context():
        officer = make_officer()

        officer.agency.email_domain = None
        officer.agency.email_pattern = None
        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["recipient"] is None
        assert result["can_email"] is False
