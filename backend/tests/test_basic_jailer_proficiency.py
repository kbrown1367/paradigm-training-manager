from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.jailer_proficiency import (
    evaluate_basic_jailer_proficiency,
    get_highest_jailer_certificate,
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


def make_jailer(
    license_date=date(2020, 1, 30),
):
    agency = Agency(
        name="Test Sheriff's Office"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="JOHN",
        last_name="SMITH",
        jailer_service_start_date=license_date,
    )
    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Jailer License",
            award_date=license_date,
        )
    )

    db.session.commit()

    return agency, officer


def add_training(
    agency,
    officer,
    course_number,
    course_date=date(2020, 1, 1),
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=course_number,
            course_title=f"Course {course_number}",
            course_date=course_date,
            credited_hours=Decimal("8"),
            hours_source="TCOLE_CYCLE_REPORT",
        )
    )


def add_certificate(
    agency,
    officer,
    name,
    award_date=date(2021, 1, 1),
):
    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="Certificate",
            award_name=name,
            award_date=award_date,
        )
    )


def test_basic_jailer_requires_one_year_service(app):
    with app.app_context():
        agency, officer = make_jailer(
            date(2026, 1, 1)
        )

        add_training(
            agency,
            officer,
            "1999",
        )
        add_training(
            agency,
            officer,
            "3721",
        )
        db.session.commit()

        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert result["service_years"] == 0
        assert (
            "1 year of qualifying County Jailer service"
            in result["missing_requirements"]
        )


def test_pre_1998_license_requires_no_basic_courses(app):
    with app.app_context():
        _, officer = make_jailer(
            date(1987, 1, 15)
        )

        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=date(1988, 1, 15),
        )

        assert result["status"] == "ELIGIBLE"

        statuses = {
            item["course_number"]: item["status"]
            for item in result["course_requirements"]
        }

        assert statuses["1999"] == "NOT_APPLICABLE"
        assert statuses["3721"] == "NOT_APPLICABLE"


def test_1998_to_2004_license_requires_only_1999(app):
    with app.app_context():
        agency, officer = make_jailer(
            date(2000, 1, 1)
        )

        add_training(
            agency,
            officer,
            "1999",
            date(1999, 12, 1),
        )
        db.session.commit()

        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=date(2001, 1, 1),
        )

        assert result["status"] == "ELIGIBLE"

        statuses = {
            item["course_number"]: item["status"]
            for item in result["course_requirements"]
        }

        assert statuses["1999"] == "COMPLETE"
        assert statuses["3721"] == "NOT_APPLICABLE"


def test_post_2004_license_requires_1999_and_3721(app):
    with app.app_context():
        agency, officer = make_jailer(
            date(2020, 1, 30)
        )

        add_training(
            agency,
            officer,
            "1999",
            date(2019, 11, 12),
        )
        db.session.commit()

        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=date(2021, 1, 30),
        )

        assert result["status"] == "NOT_ELIGIBLE"

        statuses = {
            item["course_number"]: item["status"]
            for item in result["course_requirements"]
        }

        assert statuses["1999"] == "COMPLETE"
        assert statuses["3721"] == "MISSING"

        assert (
            "County Correction Officer Field Training "
            "(#3721)"
            in result["missing_requirements"]
        )


def test_post_2004_license_is_eligible_with_both_courses(app):
    with app.app_context():
        agency, officer = make_jailer(
            date(2020, 1, 30)
        )

        add_training(
            agency,
            officer,
            "1999",
            date(2019, 11, 12),
        )
        add_training(
            agency,
            officer,
            "3721",
            date(2019, 12, 13),
        )
        db.session.commit()

        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=date(2021, 1, 30),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["missing_requirements"] == []


def test_missing_jailer_service_date_is_insufficient_data(app):
    with app.app_context():
        agency, officer = make_jailer(
            date(2020, 1, 30)
        )

        officer.jailer_service_start_date = None
        db.session.commit()

        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["status"] == "INSUFFICIENT_DATA"

        assert (
            "County Jailer license/service start date"
            in result[
                "insufficient_data_requirements"
            ]
        )


def test_non_jailer_is_not_applicable(app):
    with app.app_context():
        agency = Agency(
            name="Test Police Department"
        )
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

        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["status"] == "NOT_APPLICABLE"


def test_basic_jailer_award_name_is_normalized(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_certificate(
            agency,
            officer,
            "Basic Jailer ",
        )
        db.session.commit()

        credential = get_highest_jailer_certificate(
            officer
        )

        assert (
            credential["highest_certificate"]
            == "Basic Jailer"
        )
        assert credential["certificate_level"] == "BASIC"


def test_higher_jailer_certificate_satisfies_basic_award(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_certificate(
            agency,
            officer,
            "Intermediate Jailer Proficiency",
        )
        db.session.commit()

        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["status"] == "AWARDED"
        assert (
            result["current_certificate"]
            == "Intermediate Jailer"
        )


def test_course_evidence_is_returned(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            "1999",
            date(2019, 11, 12),
        )
        add_training(
            agency,
            officer,
            "3721",
            date(2019, 12, 13),
        )
        db.session.commit()

        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        course = next(
            item
            for item in result["course_requirements"]
            if item["course_number"] == "3721"
        )

        assert course["status"] == "COMPLETE"
        assert (
            course["matched_course"]["course_date"]
            == "2019-12-13"
        )
