from datetime import date
from decimal import Decimal

import pytest

from app import create_app
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


@pytest.fixture()
def client(app):
    return app.test_client()


def make_officer():
    agency = Agency(
        name="Test Police Department",
        email_domain="example.gov",
        email_pattern="FIRST_INITIAL_LAST",
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="654321",
        first_name="John",
        last_name="Doe",
    )
    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Peace Officer License",
            award_date=date(2020, 1, 1),
        )
    )

    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="9999",
            course_title="Test Training",
            course_date=date(2026, 1, 10),
            credited_hours=Decimal("8.00"),
            hours_source="TCOLE",
            source="TCOLE",
        )
    )

    db.session.commit()

    return agency, officer


def test_employee_workspace_endpoint(
    app,
    client,
):
    with app.app_context():
        agency, officer = make_officer()

        agency_id = str(agency.id)
        officer_id = str(officer.id)

    response = client.get(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/workspace"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["officer"]["tcole_pid"] == (
        "654321"
    )
    assert data["resolved_email"]["email"] == (
        "jdoe@example.gov"
    )
    assert "training_unit" in data
    assert "training_summary" in data
    assert "current_unit_training" in data
    assert "requirements" in data
    assert "components" in data
    assert "proficiency_advancement" in data


def test_employee_workspace_endpoint_is_tenant_scoped(
    app,
    client,
):
    with app.app_context():
        _, officer = make_officer()

        other_agency = Agency(
            name="Other Department"
        )
        db.session.add(other_agency)
        db.session.commit()

        other_agency_id = str(other_agency.id)
        officer_id = str(officer.id)

    response = client.get(
        f"/api/agencies/{other_agency_id}"
        f"/officers/{officer_id}"
        "/workspace"
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Officer not found."
    }
