from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.county_jailer import (
    evaluate_agency_county_jailers,
    evaluate_county_jailer,
    has_county_jailer_license,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAward,
    TrainingRecord,
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


def make_jailer():
    agency = Agency(name="Test Sheriff's Office")
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
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Jailer License",
            award_date=date(2020, 1, 1),
        )
    )

    db.session.commit()

    return agency, officer


def add_training(
    agency,
    officer,
    course_number,
    course_date,
    hours=8,
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=course_number,
            course_title=f"Course {course_number}",
            course_date=course_date,
            credited_hours=Decimal(str(hours)),
            hours_source="TCOLE_CYCLE_REPORT",
        )
    )


def test_jailer_license_detected(app):
    with app.app_context():
        _, officer = make_jailer()

        assert has_county_jailer_license(officer)


def test_missing_jailer_courses_are_outstanding(app):
    with app.app_context():
        _, officer = make_jailer()

        result = evaluate_county_jailer(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["status"] == "OUTSTANDING"
        assert (
            result["unit_results"][0]["status"]
            == "OUTSTANDING"
        )
        assert result["cycle_status"] == "OUTSTANDING"

        course_numbers = {
            item["course_number"]
            for item in result["requirements"]
        }

        assert course_numbers == {"4902", "3939"}


def test_4902_satisfies_unit_requirement(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            "4902",
            date(2026, 2, 1),
        )
        db.session.commit()

        result = evaluate_county_jailer(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert (
            result["unit_results"][0]["status"]
            == "COMPLETE"
        )
        assert result["cycle_status"] == "OUTSTANDING"


def test_3939_satisfies_cycle_requirement(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            "3939",
            date(2026, 3, 1),
        )
        db.session.commit()

        result = evaluate_county_jailer(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["cycle_status"] == "COMPLETE"
        assert (
            result["cycle_required_courses"][0][
                "status"
            ]
            == "COMPLETE"
        )


def test_verified_exemption_satisfies_3939(app):
    with app.app_context():
        _, officer = make_jailer()

        officer.verified_jailer_cultural_diversity_exemption = (
            True
        )
        db.session.commit()

        result = evaluate_county_jailer(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        course = result["cycle_required_courses"][0]

        assert result["cycle_status"] == "COMPLETE"
        assert course["status"] == "EXEMPT"
        assert (
            course["satisfaction_basis"]
            == "VERIFIED_EXEMPTION"
        )


def test_complete_jailer_is_complete(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            "4902",
            date(2026, 2, 1),
        )
        add_training(
            agency,
            officer,
            "3939",
            date(2026, 3, 1),
        )
        db.session.commit()

        result = evaluate_county_jailer(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["status"] == "COMPLETE"
        assert result["requirements"] == []


def test_training_before_current_period_does_not_count(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            "4902",
            date(2024, 1, 1),
        )
        add_training(
            agency,
            officer,
            "3939",
            date(2024, 1, 1),
        )
        db.session.commit()

        result = evaluate_county_jailer(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["status"] == "OUTSTANDING"


def test_non_jailer_excluded_from_agency_results(app):
    with app.app_context():
        agency = Agency(name="Test Sheriff's Office")
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="999999",
            first_name="JANE",
            last_name="DOE",
        )
        db.session.add(officer)
        db.session.commit()

        result = evaluate_agency_county_jailers(
            agency.id,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["officer_count"] == 0
        assert result["officers"] == []


def test_jailer_unit_requirement_resets_in_unit_two(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            "4902",
            date(2026, 2, 1),
        )
        add_training(
            agency,
            officer,
            "3939",
            date(2026, 3, 1),
        )
        db.session.commit()

        first_unit = evaluate_county_jailer(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        second_unit = evaluate_county_jailer(
            officer,
            evaluation_date=date(2027, 9, 1),
        )

        assert first_unit["unit_number"] == 1
        assert first_unit["unit_status"] == "COMPLETE"

        assert second_unit["unit_number"] == 2
        assert (
            second_unit["unit_start"]
            == "2027-09-01"
        )
        assert (
            second_unit["unit_end"]
            == "2029-08-31"
        )

        assert (
            second_unit["unit_status"]
            == "OUTSTANDING"
        )

        assert (
            second_unit[
                "cycle_required_courses"
            ][0]["status"]
            == "COMPLETE"
        )


def test_jailer_engine_moves_into_next_cycle(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            "4902",
            date(2028, 1, 1),
        )
        add_training(
            agency,
            officer,
            "3939",
            date(2028, 1, 2),
        )
        db.session.commit()

        result = evaluate_county_jailer(
            officer,
            evaluation_date=date(2030, 1, 1),
        )

        assert (
            result["cycle_start"]
            == "2029-09-01"
        )
        assert (
            result["cycle_end"]
            == "2033-08-31"
        )
        assert result["unit_number"] == 1
        assert (
            result["unit_start"]
            == "2029-09-01"
        )
        assert (
            result["unit_end"]
            == "2031-08-31"
        )

        assert result["status"] == "OUTSTANDING"

        course_numbers = {
            item["course_number"]
            for item in result["requirements"]
        }

        assert course_numbers == {"4902", "3939"}


def test_jailer_cycle_course_survives_unit_boundary(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            "3939",
            date(2026, 3, 1),
        )
        db.session.commit()

        result = evaluate_county_jailer(
            officer,
            evaluation_date=date(2028, 1, 1),
        )

        assert result["unit_number"] == 2

        cycle_course = (
            result["cycle_required_courses"][0]
        )

        assert cycle_course["status"] == "COMPLETE"
        assert (
            cycle_course["satisfaction_basis"]
            == "DIRECT"
        )
