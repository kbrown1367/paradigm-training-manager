from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.police_chief import (
    evaluate_police_chief,
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


def make_chief(
    appointment_date=date(2020, 1, 1),
):
    agency = Agency(name="Test Police Department")
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="JOHN",
        last_name="SMITH",
    )

    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAssignment(
            agency_id=agency.id,
            officer_id=officer.id,
            assignment_type="POLICE_CHIEF",
            effective_date=appointment_date,
        )
    )

    db.session.commit()

    return agency, officer


def add_course(
    agency,
    officer,
    number,
    course_date,
    hours=8,
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=number,
            course_title=f"Course {number}",
            course_date=course_date,
            credited_hours=Decimal(str(hours)),
            hours_source="TCOLE_CYCLE_REPORT",
        )
    )


def test_chief_rule_not_applicable_without_assignment(app):
    with app.app_context():
        agency = Agency(name="Test Police Department")
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="123456",
            first_name="JOHN",
            last_name="SMITH",
        )

        db.session.add(officer)
        db.session.commit()

        result = evaluate_police_chief(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["applicable"] is False


def test_new_chief_requires_3780_and_3740_within_two_years(app):
    with app.app_context():
        agency, officer = make_chief(
            date(2025, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3780",
            date(2025, 6, 1),
            40,
        )

        db.session.commit()

        result = evaluate_police_chief(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["initial_training_complete"] is False
        assert result["initial_training_due_date"] == "2027-01-01"
        assert result["chief_status"] == "OUTSTANDING"

        assert any(
            item["course_number"] == "3740"
            for item in result["requirements"]
        )


def test_new_chief_training_fails_after_two_year_deadline(app):
    with app.app_context():
        _, officer = make_chief(
            date(2020, 1, 1)
        )

        result = evaluate_police_chief(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["initial_training_complete"] is False
        assert result["chief_status"] == "OVERDUE"

        assert all(
            item["status"] == "FAILED"
            for item in result["requirements"]
        )


def test_completed_initial_training_activates_recurring_3740(app):
    with app.app_context():
        agency, officer = make_chief(
            date(2020, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3780",
            date(2020, 6, 1),
            40,
        )
        add_course(
            agency,
            officer,
            "3740",
            date(2021, 6, 1),
            40,
        )

        db.session.commit()

        result = evaluate_police_chief(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["initial_training_complete"] is True
        assert result["continuing_education_required"] is True
        assert result["current_unit_3740_completed"] is False

        assert any(
            item["type"]
            == "CHIEF_CONTINUING_EDUCATION"
            for item in result["requirements"]
        )


def test_current_unit_3740_satisfies_chief_ce_and_3189(app):
    with app.app_context():
        agency, officer = make_chief(
            date(2020, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3780",
            date(2020, 6, 1),
            40,
        )
        add_course(
            agency,
            officer,
            "3740",
            date(2021, 6, 1),
            40,
        )
        add_course(
            agency,
            officer,
            "3740",
            date(2026, 1, 1),
            40,
        )

        db.session.commit()

        result = evaluate_police_chief(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["current_unit_3740_completed"] is True

        assert (
            result[
                "state_federal_law_update_satisfied_by_3740"
            ]
            is True
        )

        assert (
            result[
                "supervisor_requirement_satisfied_by_3740"
            ]
            is True
        )

        course_3189 = next(
            item
            for item
            in result["peace_officer"]["required_courses"]
            if item["course_number"] == "3189"
        )

        assert course_3189["completed"] is True
        assert course_3189["status"] == "COMPLETE"
        assert (
            course_3189["satisfaction_basis"]
            == "EQUIVALENCY"
        )


def test_3740_does_not_automatically_add_alerrt_hours(app):
    with app.app_context():
        agency, officer = make_chief(
            date(2020, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3780",
            date(2020, 6, 1),
            40,
        )
        add_course(
            agency,
            officer,
            "3740",
            date(2021, 6, 1),
            40,
        )
        add_course(
            agency,
            officer,
            "3740",
            date(2026, 1, 1),
            40,
        )

        db.session.commit()

        result = evaluate_police_chief(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["peace_officer"]["alerrt_hours"] == 0.0
        assert (
            result["peace_officer"][
                "remaining_alerrt_hours"
            ]
            == 16.0
        )


def test_direct_3189_remains_direct_even_when_3740_exists(app):
    with app.app_context():
        agency, officer = make_chief(
            date(2020, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3780",
            date(2020, 6, 1),
            40,
        )
        add_course(
            agency,
            officer,
            "3740",
            date(2021, 6, 1),
            40,
        )
        add_course(
            agency,
            officer,
            "3740",
            date(2026, 1, 1),
            40,
        )
        add_course(
            agency,
            officer,
            "3189",
            date(2026, 2, 1),
            8,
        )

        db.session.commit()

        result = evaluate_police_chief(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        course_3189 = next(
            item
            for item
            in result["peace_officer"]["required_courses"]
            if item["course_number"] == "3189"
        )

        assert course_3189["completed"] is True
        assert (
            course_3189["satisfaction_basis"]
            == "DIRECT"
        )
