from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.public_information_officer import (
    evaluate_public_information_officer,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAssignment,
    TrainingRecord,
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def make_officer(
    appointment_date=None,
):
    agency = Agency(
        name="Test Police Department"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="JANE",
        last_name="SMITH",
    )
    db.session.add(officer)
    db.session.flush()

    if appointment_date is not None:
        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type=(
                    "PUBLIC_INFORMATION_OFFICER"
                ),
                effective_date=appointment_date,
            )
        )

    db.session.commit()

    return agency, officer


def add_course(
    agency,
    officer,
    number,
    completion_date,
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=number,
            course_title=f"Course {number}",
            course_date=completion_date,
            credited_hours=Decimal("8"),
            hours_source="TCOLE_CYCLE_REPORT",
        )
    )


def test_pio_rule_not_applicable_without_assignment(app):
    with app.app_context():
        _, officer = make_officer()

        result = (
            evaluate_public_information_officer(
                officer,
                evaluation_date=date(2026, 8, 8),
            )
        )

        assert result["applicable"] is False
        assert result["status"] == "NOT_APPLICABLE"


def test_pio_first_deadline_is_first_anniversary(app):
    with app.app_context():
        _, officer = make_officer(
            date(2026, 3, 15)
        )

        result = (
            evaluate_public_information_officer(
                officer,
                evaluation_date=date(2026, 8, 8),
            )
        )

        assert (
            result["annual_period_start"]
            == "2026-03-15"
        )
        assert (
            result["annual_due_date"]
            == "2027-03-15"
        )
        assert (
            result["training_status"]
            == "FUTURE_REQUIREMENT"
        )


@pytest.mark.parametrize(
    "course_number",
    [
        "666038",
        "666318",
        "3763",
        "3775",
        "667388",
        "667952",
        "664033",
    ],
)
def test_each_approved_course_satisfies_training(
    app,
    course_number,
):
    with app.app_context():
        agency, officer = make_officer(
            date(2026, 1, 1)
        )

        add_course(
            agency,
            officer,
            course_number,
            date(2026, 6, 1),
        )

        db.session.commit()

        result = (
            evaluate_public_information_officer(
                officer,
                evaluation_date=date(2026, 8, 8),
            )
        )

        assert result["training_completed"] is True
        assert result["training_status"] == "COMPLIANT"
        assert (
            result["training_course_number"]
            == course_number
        )


def test_unapproved_course_does_not_satisfy_pio(app):
    with app.app_context():
        agency, officer = make_officer(
            date(2026, 1, 1)
        )

        add_course(
            agency,
            officer,
            "9999",
            date(2026, 6, 1),
        )

        db.session.commit()

        result = (
            evaluate_public_information_officer(
                officer,
                evaluation_date=date(2026, 8, 8),
            )
        )

        assert result["training_completed"] is False


def test_training_does_not_imply_tdem_certification(app):
    with app.app_context():
        agency, officer = make_officer(
            date(2026, 1, 1)
        )

        add_course(
            agency,
            officer,
            "666038",
            date(2026, 6, 1),
        )

        db.session.commit()

        result = (
            evaluate_public_information_officer(
                officer,
                evaluation_date=date(2026, 8, 8),
            )
        )

        assert result["training_completed"] is True
        assert (
            result["tdem_certification_status"]
            == "UNVERIFIED"
        )
        assert result["status"] == "PENDING"


def test_pio_requirement_repeats_annually(app):
    with app.app_context():
        agency, officer = make_officer(
            date(2025, 1, 10)
        )

        add_course(
            agency,
            officer,
            "666038",
            date(2025, 6, 1),
        )

        db.session.commit()

        result = (
            evaluate_public_information_officer(
                officer,
                evaluation_date=date(2026, 8, 8),
            )
        )

        assert result["annual_period_number"] == 2
        assert (
            result["annual_period_start"]
            == "2026-01-10"
        )
        assert (
            result["annual_due_date"]
            == "2027-01-10"
        )

        # Prior year's course cannot satisfy
        # the new annual period.
        assert result["training_completed"] is False


def test_pio_requirement_becomes_noncompliant_after_due_date(app):
    with app.app_context():
        _, officer = make_officer(
            date(2024, 1, 1)
        )

        result = (
            evaluate_public_information_officer(
                officer,
                evaluation_date=date(2026, 8, 8),
            )
        )

        # The evaluator moves to the annual period
        # containing the evaluation date.
        assert (
            result["annual_due_date"]
            == "2027-01-01"
        )
        assert (
            result["training_status"]
            == "FUTURE_REQUIREMENT"
        )
