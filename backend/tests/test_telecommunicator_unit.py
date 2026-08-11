from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.telecommunicator_unit import (
    evaluate_telecommunicator_unit,
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


def make_telecommunicator():
    agency = Agency(
        name="Test Police Department"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="404933",
        first_name="CHRISTOPHER",
        last_name="CARINCI",
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

    db.session.commit()

    return agency, officer


def add_training(
    agency,
    officer,
    course_number,
    course_date,
    hours,
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


def test_telecommunicator_is_applicable(app):
    with app.app_context():
        _, officer = make_telecommunicator()

        result = evaluate_telecommunicator_unit(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["applicable"] is True
        assert result["unit_status"] == "OUTSTANDING"
        assert result["minimum_total_hours"] == 20.0


def test_six_hours_leaves_fourteen(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "1000",
            date(2026, 1, 1),
            6,
        )
        db.session.commit()

        result = evaluate_telecommunicator_unit(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["current_unit_hours"] == 6.0
        assert result["remaining_total_hours"] == 14.0


def test_course_786_is_independent_requirement(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "786",
            date(2026, 1, 1),
            4,
        )
        db.session.commit()

        result = evaluate_telecommunicator_unit(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        course = result["required_courses"][0]

        assert course["status"] == "COMPLETE"
        assert result["current_unit_hours"] == 4.0
        assert result["remaining_total_hours"] == 16.0
        assert result["unit_status"] == "OUTSTANDING"


def test_twenty_hours_without_786_is_outstanding(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "1000",
            date(2026, 1, 1),
            20,
        )
        db.session.commit()

        result = evaluate_telecommunicator_unit(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["remaining_total_hours"] == 0.0
        assert result["unit_status"] == "OUTSTANDING"

        assert {
            item.get("course_number")
            for item in result["requirements"]
        } == {"786"}


def test_twenty_hours_and_786_is_complete(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "786",
            date(2026, 1, 1),
            4,
        )

        add_training(
            agency,
            officer,
            "1000",
            date(2026, 2, 1),
            16,
        )

        db.session.commit()

        result = evaluate_telecommunicator_unit(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["current_unit_hours"] == 20.0
        assert result["remaining_total_hours"] == 0.0
        assert result["unit_status"] == "COMPLETE"
        assert result["requirements"] == []


def test_training_before_unit_does_not_count(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_training(
            agency,
            officer,
            "786",
            date(2025, 8, 31),
            20,
        )

        db.session.commit()

        result = evaluate_telecommunicator_unit(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["current_unit_hours"] == 0.0
        assert result["remaining_total_hours"] == 20.0
        assert result["unit_status"] == "OUTSTANDING"
