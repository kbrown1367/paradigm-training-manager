from datetime import date

import pytest

from app import create_app
from app.compliance.telecommunicator_proficiency import (
    evaluate_telecommunicator_proficiency,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAward,
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
            date(2010, 1, 1),
    )

    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Telecommunicator License",
            award_date=date(2010, 1, 1),
        )
    )

    db.session.commit()

    return agency, officer


def add_certificate(
    agency,
    officer,
    name,
    award_date,
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
    db.session.commit()


def test_no_certificate_advances_to_basic(app):
    with app.app_context():
        _, officer = make_telecommunicator()

        result = evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert (
            result["next_certificate"]
            == "Basic Telecommunicator"
        )


def test_basic_advances_to_intermediate(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Basic Telecommunicator",
            date(2011, 1, 1),
        )

        result = evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert (
            result["next_certificate"]
            == "Intermediate Telecommunicator"
        )


def test_intermediate_advances_to_advanced(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Intermediate Telecommunicator",
            date(2014, 1, 1),
        )

        result = evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert (
            result["next_certificate"]
            == "Advanced Telecommunicator"
        )


def test_advanced_advances_to_master(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Advanced Telecommunicator",
            date(2018, 1, 1),
        )

        result = evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert (
            result["next_certificate"]
            == "Master Telecommunicator"
        )


def test_master_is_terminal(app):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Master Telecommunicator",
            date(2024, 1, 1),
        )

        result = evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "TERMINAL"
        assert result["next_certificate"] is None

        assert (
            result["current_certificate"]
            == "Master Telecommunicator"
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

        result = evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "NOT_APPLICABLE"
        assert result["next_certificate"] is None


def test_telecommunicator_advancement_uses_verified_education(
    app,
):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Intermediate Telecommunicator",
            date(2024, 1, 1),
        )

        officer.verified_education_level = "BACHELOR"
        officer.verified_college_credit_hours = 120

        db.session.commit()

        result = evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        assert result["education_level"] == "BACHELOR"
        assert result["college_credit_hours"] == 120


def test_telecommunicator_education_does_not_change_eligibility(
    app,
):
    with app.app_context():
        agency, officer = make_telecommunicator()

        add_certificate(
            agency,
            officer,
            "Intermediate Telecommunicator",
            date(2024, 1, 1),
        )

        officer.telecommunicator_service_start_date = (
            date(2023, 8, 14)
        )

        officer.verified_education_level = "BACHELOR"
        officer.verified_college_credit_hours = 120

        db.session.commit()

        result = evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        assert result["education_level"] == "BACHELOR"
        assert result["college_credit_hours"] == 120

        # Education is informational for the
        # Telecommunicator proficiency track and must
        # not replace published service/training rules.
        assert result["status"] != "ELIGIBLE"
        assert result["minimum_service_years"] == 4


def test_tcole_education_takes_precedence_over_verified_fallback(
    app,
):
    with app.app_context():
        agency, officer = make_telecommunicator()

        officer.verified_education_level = "ASSOCIATE"
        officer.verified_college_credit_hours = 120

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name=(
                    "Academic Recognition Award - "
                    "Bachelor Degree"
                ),
                award_date=date(2025, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        assert result["education_level"] == "BACHELOR"
        assert result["college_credit_hours"] == 120
