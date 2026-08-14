from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.telecommunicator_proficiency import (
    evaluate_basic_telecommunicator_proficiency,
    get_highest_telecommunicator_certificate,
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

    db.session.commit()

    return agency, officer


def add_training(
    agency,
    officer,
    course_number,
    course_date,
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=str(course_number),
            course_title=f"Course {course_number}",
            course_date=course_date,
            credited_hours=Decimal("8"),
            hours_source="TCOLE",
            source="TCOLE",
        )
    )


def add_certificate(
    agency,
    officer,
    name,
    award_date=date(2025, 1, 1),
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


def add_current_basic_requirements(
    agency,
    officer,
    evaluation_date=date(2026, 8, 11),
):
    add_training(
        agency,
        officer,
        "1080",
        date(2025, 1, 1),
    )
    add_training(
        agency,
        officer,
        "1999",
        date(2025, 1, 2),
    )
    add_training(
        agency,
        officer,
        "3720",
        date(2025, 1, 3),
    )
    add_training(
        agency,
        officer,
        "3812",
        date(2026, 5, 1),
    )


def test_non_telecommunicator_is_not_applicable(app):
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
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "NOT_APPLICABLE"


def test_basic_requires_one_year_service(app):
    with app.app_context():
        agency, officer = make_telecommunicator(
            date(2026, 1, 1)
        )

        add_current_basic_requirements(
            agency,
            officer,
        )
        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert result["service_years"] == 0
        assert (
            "1 year of qualifying Telecommunicator service"
            in result["missing_requirements"]
        )


def test_1080_satisfies_basic_and_crisis(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_current_basic_requirements(
            agency,
            officer,
        )
        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        statuses = {
            item["id"]: item["status"]
            for item in result["course_requirements"]
        }

        assert statuses[
            "BASIC_TELECOMMUNICATOR"
        ] == "COMPLETE"
        assert statuses[
            "CRISIS_COMMUNICATIONS"
        ] == "COMPLETE"


def test_post_2014_appointment_requires_orientation(app):
    with app.app_context():
        agency, officer = make_telecommunicator(
            date(2020, 1, 1)
        )

        add_training(
            agency,
            officer,
            "1080",
            date(2025, 1, 1),
        )
        add_training(
            agency,
            officer,
            "3720",
            date(2025, 1, 3),
        )
        add_training(
            agency,
            officer,
            "3812",
            date(2026, 5, 1),
        )
        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert (
            "Personnel Orientation"
            in result["missing_requirements"]
        )


def test_pre_2014_appointment_orientation_not_applicable(app):
    with app.app_context():
        agency, officer = make_telecommunicator(
            date(2013, 1, 1)
        )

        add_training(
            agency,
            officer,
            "1080",
            date(2015, 1, 1),
        )
        add_training(
            agency,
            officer,
            "3720",
            date(2015, 1, 2),
        )
        add_training(
            agency,
            officer,
            "3812",
            date(2026, 5, 1),
        )
        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        orientation = next(
            item
            for item in result["course_requirements"]
            if item["id"] == "PERSONNEL_ORIENTATION"
        )

        assert (
            orientation["status"]
            == "NOT_APPLICABLE"
        )


def test_pre_2011_appointment_crisis_not_applicable(app):
    with app.app_context():
        agency, officer = make_telecommunicator(
            date(2010, 1, 1)
        )

        add_training(
            agency,
            officer,
            "1013",
            date(2010, 1, 2),
        )
        add_training(
            agency,
            officer,
            "3720",
            date(2010, 1, 3),
        )
        add_training(
            agency,
            officer,
            "3812",
            date(2026, 5, 1),
        )
        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        crisis = next(
            item
            for item in result["course_requirements"]
            if item["id"] == "CRISIS_COMMUNICATIONS"
        )

        assert crisis["status"] == "NOT_APPLICABLE"


def test_field_training_required_for_current_evaluation(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "1080",
            date(2025, 1, 1),
        )
        add_training(
            agency,
            officer,
            "1999",
            date(2025, 1, 2),
        )
        add_training(
            agency,
            officer,
            "3812",
            date(2026, 5, 1),
        )
        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert (
            "Telecommunications Field Training"
            in result["missing_requirements"]
        )


def test_recent_tdd_tty_is_required(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "1080",
            date(2025, 1, 1),
        )
        add_training(
            agency,
            officer,
            "1999",
            date(2025, 1, 2),
        )
        add_training(
            agency,
            officer,
            "3720",
            date(2025, 1, 3),
        )

        # Outside the six-month window.
        add_training(
            agency,
            officer,
            "3812",
            date(2025, 12, 1),
        )

        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert (
            "TDD/TTY for Telecommunicators"
            in result["missing_requirements"]
        )


def test_tdd_tty_equivalent_satisfies_recent_requirement(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "1080",
            date(2025, 1, 1),
        )
        add_training(
            agency,
            officer,
            "1999",
            date(2025, 1, 2),
        )
        add_training(
            agency,
            officer,
            "3720",
            date(2025, 1, 3),
        )
        add_training(
            agency,
            officer,
            "412",
            date(2026, 3, 1),
        )

        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "ELIGIBLE"


def test_complete_current_requirements_are_eligible(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_current_basic_requirements(
            agency,
            officer,
        )

        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "ELIGIBLE"
        assert result["missing_requirements"] == []


def test_existing_basic_certificate_is_awarded(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Basic Telecommunicator",
        )
        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "AWARDED"
        assert (
            result["current_certificate"]
            == "Basic Telecommunicator"
        )


def test_higher_certificate_satisfies_basic_award(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Master Telecommunicator",
        )
        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 11),
            )
        )

        assert result["status"] == "AWARDED"
        assert (
            result["current_certificate"]
            == "Master Telecommunicator"
        )


def test_highest_certificate_detection(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Basic Telecommunicator",
            date(2020, 1, 1),
        )
        add_certificate(
            agency,
            officer,
            "Intermediate Telecommunicator",
            date(2022, 1, 1),
        )
        add_certificate(
            agency,
            officer,
            "Advanced Telecommunicator",
            date(2024, 1, 1),
        )

        db.session.commit()

        credential = (
            get_highest_telecommunicator_certificate(
                officer
            )
        )

        assert (
            credential["highest_certificate"]
            == "Advanced Telecommunicator"
        )
        assert (
            credential["certificate_level"]
            == "ADVANCED"
        )


def test_basic_reports_all_imported_training_hours(app):
    with app.app_context():
        agency = Agency(
            name="Basic Training Hours Agency"
        )

        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="777001",
            first_name="Basic",
            last_name="Dispatcher",
            telecommunicator_service_start_date=
                date(2020, 1, 1),
        )

        db.session.add(officer)
        db.session.flush()

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Telecommunicator License",
                award_date=date(2020, 1, 1),
            )
        )

        db.session.add_all(
            [
                TrainingRecord(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    course_number="3854",
                    course_title="Computer Operations",
                    course_date=date(2026, 2, 22),
                    credited_hours=Decimal("2"),
                ),
                TrainingRecord(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    course_number="4100",
                    course_title="Information Technology",
                    course_date=date(2026, 2, 18),
                    credited_hours=Decimal("4"),
                ),
                TrainingRecord(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    course_number="2110",
                    course_title="Spanish",
                    course_date=date(2025, 9, 17),
                    credited_hours=Decimal("22"),
                ),
                TrainingRecord(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    course_number="9998",
                    course_title="Older Training",
                    course_date=date(2024, 1, 15),
                    credited_hours=Decimal("12"),
                ),
            ]
        )

        db.session.commit()

        result = (
            evaluate_basic_telecommunicator_proficiency(
                officer,
                evaluation_date=date(2026, 8, 14),
            )
        )

        assert result["training_hours"] == 40.0
        assert result["minimum_training_hours"] is None
