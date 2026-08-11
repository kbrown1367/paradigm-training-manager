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
from app.services.employee_workspace import (
    build_employee_workspace,
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


def make_telecommunicator():
    agency = Agency(
        name="Test Police Department",
        email_domain="example.gov",
        email_pattern="FIRST_INITIAL_LAST",
    )

    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="404933",
        first_name="Christopher",
        last_name="Carinci",
    )

    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name=(
                "Telecommunications Operator License"
            ),
            award_date=date(2014, 1, 1),
        )
    )

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="Certificate",
            award_name="Master Telecommunicator",
            award_date=date(2024, 3, 12),
        )
    )

    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="7006",
            course_title="Protecting Your TCOLE License",
            course_date=date(2026, 8, 3),
            credited_hours=Decimal("2"),
            hours_source="TCOLE_CYCLE_REPORT",
        )
    )

    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="4202",
            course_title=(
                "Finding Wellness-Building a Healthier Life"
            ),
            course_date=date(2026, 8, 3),
            credited_hours=Decimal("4"),
            hours_source="TCOLE_CYCLE_REPORT",
        )
    )

    db.session.commit()

    return officer


def test_telecommunicator_workspace_summary_uses_unit_rule(
    app,
):
    with app.app_context():
        officer = make_telecommunicator()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        summary = result["training_summary"]

        assert summary["current_unit_hours"] == 6.0
        assert summary["minimum_total_hours"] == 20.0
        assert summary["remaining_total_hours"] == 14.0
        assert summary["training_record_count"] == 2

        messages = {
            item.get("message")
            for item in result[
                "outstanding_requirements"
            ]
        }

        assert (
            "14 additional Telecommunicator "
            "training hours required."
            in messages
        )

        assert (
            "Cardiac Emergency Communication "
            "(#786) remains outstanding."
            in messages
        )


def test_telecommunicator_email_names_requirements(
    app,
):
    with app.app_context():
        officer = make_telecommunicator()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 11),
            track="telecommunicator",
        )

        body = result["body"]

        assert (
            "14 additional Telecommunicator "
            "training hours required."
            in body
        )

        assert (
            "Cardiac Emergency Communication "
            "(#786) remains outstanding."
            in body
        )

        assert (
            "Current Certificate: Master Telecommunicator"
            in body
        )

        assert (
            "Requirement (Due 8/31/2027)"
            not in body
        )
