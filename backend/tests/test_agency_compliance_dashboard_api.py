from datetime import date

import pytest

from app import create_app
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
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def seed_agency():
    agency = Agency(
        name="Dashboard API Agency"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="900001",
        first_name="JANE",
        last_name="SMITH",
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

    db.session.commit()

    return agency.id


def test_dashboard_endpoint_returns_agency_dashboard(app):
    with app.app_context():
        agency_id = seed_agency()

    client = app.test_client()

    response = client.get(
        f"/api/agencies/{agency_id}"
        "/compliance/dashboard"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["agency"]["id"] == str(agency_id)
    assert (
        data["summary"]["active_employee_count"]
        == 1
    )
    assert len(data["employees"]) == 1
    assert (
        data["employees"][0]["tcole_pid"]
        == "900001"
    )


def test_dashboard_endpoint_returns_404_for_unknown_agency(app):
    import uuid

    client = app.test_client()

    response = client.get(
        f"/api/agencies/{uuid.uuid4()}"
        "/compliance/dashboard"
    )

    assert response.status_code == 404
