from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.telecommunicator_proficiency import (
    evaluate_advanced_telecommunicator_proficiency,
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


def make_telecommunicator(
    service_start=date(2020, 1, 1),
    basic=True,
    intermediate=True,
):
    agency = Agency(
        name="Test Communications Center"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="555555",
        first_name="JANE",
        last_name="DISPATCHER",
        telecommunicator_service_start_date=
            service_start,
    )

    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Telecommunicator License",
            award_date=service_start,
        )
    )

    if basic:
        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Basic Telecommunicator",
                award_date=date(2021, 1, 1),
            )
        )

    if intermediate:
        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Intermediate Telecommunicator",
                award_date=date(2022, 1, 1),
            )
        )

    db.session.commit()

    return agency, officer


def add_training(
    agency,
    officer,
    course_number,
    hours,
    course_date=date(2025, 1, 1),
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=str(course_number),
            course_title=f"Course {course_number}",
            course_date=course_date,
            credited_hours=Decimal(str(hours)),
            hours_source="TCOLE",
            source="TCOLE",
        )
    )


def add_required_courses(
    agency,
    officer,
    tdd_date=date(2026, 5, 1),
):
    add_training(
        agency,
        officer,
        "3939",
        8,
        date(2024, 1, 1),
    )
    add_training(
        agency,
        officer,
        "3920",
        8,
        date(2024, 2, 1),
    )
    add_training(
        agency,
        officer,
        "420",
        8,
        date(2024, 3, 1),
    )
    add_training(
        agency,
        officer,
        "22109",
        8,
        date(2024, 4, 1),
    )
    add_training(
        agency,
        officer,
        "3812",
        8,
        tdd_date,
    )


def add_general_hours(
    agency,
    officer,
    hours,
):
    add_training(
        agency,
        officer,
        "9000",
        hours,
        date(2025, 6, 1),
    )


def add_certificate(
    agency,
    officer,
    name,
):
    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="Certificate",
            award_name=name,
            award_date=date(2025, 1, 1),
        )
    )


def test_non_telecommunicator_not_applicable(app):
    with app.app_context():
        agency = Agency(
            name="Test Police Department"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="999999",
            first_name="JOHN",
            last_name="DOE",
        )

        db.session.add(officer)
        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "NOT_APPLICABLE"


def test_basic_certificate_required(app):
    with app.app_context():
        agency, officer = make_telecommunicator(
            basic=False,
            intermediate=False,
        )

        add_required_courses(
            agency,
            officer,
        )
        add_general_hours(
            agency,
            officer,
            200,
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert (
            "Basic Telecommunicator Certificate"
            in result["missing_requirements"]
        )


def test_intermediate_certificate_required(app):
    with app.app_context():
        agency, officer = make_telecommunicator(
            intermediate=False,
        )

        add_required_courses(
            agency,
            officer,
        )
        add_general_hours(
            agency,
            officer,
            200,
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "NOT_ELIGIBLE"

        assert (
            "Intermediate Telecommunicator Certificate"
            in result["missing_requirements"]
        )


def test_four_year_service_requirement(app):
    with app.app_context():
        agency, officer = make_telecommunicator(
            service_start=date(2023, 1, 1),
        )

        add_required_courses(
            agency,
            officer,
        )
        add_general_hours(
            agency,
            officer,
            200,
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["service_years"] == 3
        assert result["status"] == "NOT_ELIGIBLE"

        assert (
            "1 additional year of qualifying "
            "Telecommunicator service"
            in result["missing_requirements"]
        )


def test_240_training_hours_required(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        # Required courses = 40 hours.
        add_required_courses(
            agency,
            officer,
        )

        # 190 more = 230 total.
        add_general_hours(
            agency,
            officer,
            190,
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["training_hours"] == 230
        assert result["status"] == "NOT_ELIGIBLE"

        assert (
            "10 additional TCOLE training hours"
            in result["missing_requirements"]
        )


def test_cultural_diversity_equivalent_accepted(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "394",
            8,
            date(2024, 1, 1),
        )
        add_training(
            agency,
            officer,
            "3925",
            8,
            date(2024, 2, 1),
        )
        add_training(
            agency,
            officer,
            "1080",
            8,
            date(2024, 3, 1),
        )
        add_training(
            agency,
            officer,
            "34003",
            8,
            date(2024, 4, 1),
        )
        add_training(
            agency,
            officer,
            "412",
            8,
            date(2026, 5, 1),
        )
        add_general_hours(
            agency,
            officer,
            200,
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "ELIGIBLE"


def test_missing_ethics_blocks_eligibility(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "3939",
            8,
            date(2024, 1, 1),
        )
        add_training(
            agency,
            officer,
            "420",
            8,
            date(2024, 3, 1),
        )
        add_training(
            agency,
            officer,
            "22109",
            8,
            date(2024, 4, 1),
        )
        add_training(
            agency,
            officer,
            "3812",
            8,
            date(2026, 5, 1),
        )
        add_general_hours(
            agency,
            officer,
            220,
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert (
            "Ethics"
            in result["missing_requirements"]
        )


def test_missing_spanish_blocks_eligibility(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "3939",
            8,
            date(2024, 1, 1),
        )
        add_training(
            agency,
            officer,
            "3920",
            8,
            date(2024, 2, 1),
        )
        add_training(
            agency,
            officer,
            "420",
            8,
            date(2024, 3, 1),
        )
        add_training(
            agency,
            officer,
            "3812",
            8,
            date(2026, 5, 1),
        )
        add_general_hours(
            agency,
            officer,
            220,
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert (
            "Spanish"
            in result["missing_requirements"]
        )


def test_recent_tdd_tty_required(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_required_courses(
            agency,
            officer,
            tdd_date=date(2025, 12, 1),
        )
        add_general_hours(
            agency,
            officer,
            200,
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "NOT_ELIGIBLE"

        assert (
            "TDD/TTY for Telecommunicators"
            in result["missing_requirements"]
        )


def test_all_requirements_establish_eligibility(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_required_courses(
            agency,
            officer,
        )
        add_general_hours(
            agency,
            officer,
            200,
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "ELIGIBLE"
        assert result["service_years"] >= 4
        assert result["training_hours"] == 240
        assert result["missing_requirements"] == []


def test_advanced_certificate_reports_awarded(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Advanced Telecommunicator",
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "AWARDED"

        assert (
            result["current_certificate"]
            == "Advanced Telecommunicator"
        )


def test_master_certificate_satisfies_advanced(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Master Telecommunicator",
        )

        db.session.commit()

        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "AWARDED"

        assert (
            result["current_certificate"]
            == "Master Telecommunicator"
        )
