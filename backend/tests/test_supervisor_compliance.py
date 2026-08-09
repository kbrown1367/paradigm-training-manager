from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.supervisor import (
    evaluate_supervisor,
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


def make_supervisor(
    appointment_date=date(2026, 1, 1),
):
    agency = Agency(
        name="Test Police Department"
    )
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
            assignment_type="SUPERVISOR",
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


def test_supervisor_not_applicable_without_assignment(app):
    with app.app_context():
        agency = Agency(
            name="Test Police Department"
        )
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

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["applicable"] is False
        assert result["status"] == "NOT_APPLICABLE"


def test_first_time_supervisor_window(app):
    with app.app_context():
        _, officer = make_supervisor(
            date(2026, 5, 1)
        )

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        first = result["first_time_supervisor"]

        assert (
            first["window_start"]
            == "2025-05-01"
        )
        assert first["due_date"] == "2027-05-01"
        assert first["completed"] is False


def test_3737_completed_before_appointment_counts(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2026, 5, 1)
        )

        add_course(
            agency,
            officer,
            "3737",
            date(2025, 10, 1),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert (
            result[
                "first_time_supervisor"
            ]["completed"]
            is True
        )


def test_3737_prior_career_completion_counts(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2026, 5, 1)
        )

        add_course(
            agency,
            officer,
            "3737",
            date(2020, 4, 30),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        first = result["first_time_supervisor"]

        assert first["completed"] is True
        assert (
            first["completion_timing"]
            == "PRIOR_COMPLETION"
        )
        assert (
            first["completed_within_window"]
            is False
        )
        assert first["repeat_required"] is False
        assert not any(
            item["type"]
            == "NEW_SUPERVISOR_TRAINING"
            for item in result["requirements"]
        )


@pytest.mark.parametrize(
    "course_number",
    [
        "3366",
        "3367",
        "3607",
        "33111",
        "3740",
        "3743",
        "3608",
        "3709",
        "3369",
    ],
)
def test_each_hb33_course_satisfies_requirement(
    app,
    course_number,
):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2026, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3737",
            date(2026, 2, 1),
        )

        add_course(
            agency,
            officer,
            course_number,
            date(2026, 3, 1),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["hb33"]["completed"] is True
        assert (
            result["hb33"][
                "completion_course_number"
            ]
            == course_number
        )
        assert result["status"] == "COMPLIANT"


def test_hb33_missing_is_due_before_deadline(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2026, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3737",
            date(2026, 2, 1),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["hb33"]["completed"] is False
        assert result["status"] == "DUE"

        requirement = next(
            item
            for item in result["requirements"]
            if (
                item["type"]
                == "HB33_SUPERVISOR_TRAINING"
            )
        )

        assert (
            requirement["status"]
            == "OUTSTANDING"
        )
        assert (
            requirement["due_date"]
            == "2027-08-31"
        )


def test_3737_overdue_causes_noncompliance(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2024, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3366",
            date(2026, 3, 1),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["status"] == "NONCOMPLIANT"

        requirement = next(
            item
            for item in result["requirements"]
            if (
                item["type"]
                == "NEW_SUPERVISOR_TRAINING"
            )
        )

        assert requirement["status"] == "OVERDUE"


def test_prior_supervisor_assignment_controls_first_time_window(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2026, 1, 1)
        )

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2020, 6, 1),
                end_date=date(2022, 6, 1),
            )
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert (
            result[
                "first_supervisor_appointment_date"
            ]
            == "2020-06-01"
        )


def test_missing_3737_reports_evidence_basis(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2024, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3366",
            date(2026, 3, 1),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        requirement = next(
            item
            for item in result["requirements"]
            if item["type"] == "NEW_SUPERVISOR_TRAINING"
        )

        assert requirement["status"] == "OVERDUE"
        assert requirement["agency_review_recommended"] is True
        assert (
            "No qualifying #3737 completion was found"
            in requirement["evidence_basis"]
        )
        assert (
            "Agency review recommended"
            in requirement["message"]
        )


def test_missing_hb33_reports_evidence_basis(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2026, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3737",
            date(2026, 2, 1),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        requirement = next(
            item
            for item in result["requirements"]
            if item["type"] == "HB33_SUPERVISOR_TRAINING"
        )

        assert requirement["status"] == "OUTSTANDING"
        assert requirement["agency_review_recommended"] is True
        assert (
            "No approved HB33 supervisor course was found"
            in requirement["evidence_basis"]
        )
        assert (
            "Agency review recommended"
            in requirement["message"]
        )


def test_3737_late_completion_clears_active_deficiency(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2023, 1, 1)
        )

        add_course(
            agency,
            officer,
            "3737",
            date(2026, 1, 15),
        )

        add_course(
            agency,
            officer,
            "3366",
            date(2026, 3, 1),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        first = result["first_time_supervisor"]

        assert first["completed"] is True
        assert (
            first["completion_timing"]
            == "LATE_COMPLETION"
        )
        assert (
            first["completed_within_window"]
            is False
        )
        assert first["repeat_required"] is False

        assert not any(
            item["type"]
            == "NEW_SUPERVISOR_TRAINING"
            for item in result["requirements"]
        )

        assert result["status"] == "COMPLIANT"


def test_3737_within_window_records_timely_completion(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2026, 5, 1)
        )

        add_course(
            agency,
            officer,
            "3737",
            date(2026, 6, 1),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        first = result["first_time_supervisor"]

        assert first["completed"] is True
        assert (
            first["completion_timing"]
            == "WITHIN_WINDOW"
        )
        assert (
            first["completed_within_window"]
            is True
        )
        assert first["repeat_required"] is False


def test_prior_3737_satisfies_later_supervisor_assignment(app):
    with app.app_context():
        agency, officer = make_supervisor(
            date(2026, 1, 1)
        )

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2018, 6, 1),
                end_date=date(2020, 6, 1),
            )
        )

        add_course(
            agency,
            officer,
            "3737",
            date(2018, 8, 1),
        )

        db.session.commit()

        result = evaluate_supervisor(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        first = result["first_time_supervisor"]

        assert (
            result[
                "first_supervisor_appointment_date"
            ]
            == "2018-06-01"
        )
        assert first["completed"] is True
        assert first["repeat_required"] is False

        assert not any(
            item["type"]
            == "NEW_SUPERVISOR_TRAINING"
            for item in result["requirements"]
        )
