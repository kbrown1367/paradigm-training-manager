from datetime import date

import pytest

from app import create_app
from app.compliance.proficiency_tracks import (
    build_proficiency_advancement,
)
from app.extensions import db
from app.models import Agency, Officer, OfficerAward


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


def make_officer():
    agency = Agency(
        name="Test Department"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="TEST",
        last_name="EMPLOYEE",
    )
    db.session.add(officer)
    db.session.flush()

    return agency, officer


def add_award(
    agency,
    officer,
    award_type,
    award_name,
    award_date,
):
    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type=award_type,
            award_name=award_name,
            award_date=award_date,
        )
    )


def test_telecommunicator_only_track(app):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "License",
            "Telecommunications Operator License",
            date(2014, 1, 1),
        )

        add_award(
            agency,
            officer,
            "Certificate",
            "Master Telecommunicator",
            date(2024, 1, 1),
        )

        db.session.commit()

        result = build_proficiency_advancement(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["peace_officer"] is None
        assert result["jailer"] is None
        assert (
            result["telecommunicator"][
                "current_certificate"
            ]
            == "Master Telecommunicator"
        )


def test_dual_peace_officer_telecommunicator_tracks(
    app,
):
    with app.app_context():
        agency, officer = make_officer()

        officer.peace_officer_service_start_date = (
            date(2015, 1, 1)
        )

        add_award(
            agency,
            officer,
            "License",
            "Peace Officer License",
            date(2015, 1, 1),
        )

        add_award(
            agency,
            officer,
            "Certificate",
            "Advanced Peace Officer",
            date(2023, 1, 1),
        )

        add_award(
            agency,
            officer,
            "License",
            "Telecommunications Operator License",
            date(2017, 1, 1),
        )

        add_award(
            agency,
            officer,
            "Certificate",
            "Basic Telecommunicator",
            date(2018, 1, 1),
        )

        db.session.commit()

        result = build_proficiency_advancement(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert (
            result["peace_officer"][
                "current_certificate"
            ]
            == "Advanced Peace Officer"
        )

        assert (
            result["telecommunicator"][
                "current_certificate"
            ]
            == "Basic Telecommunicator"
        )
