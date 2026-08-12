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
            "AUTHORIZATION_DISABLED": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def seed_officer(app):
    with app.app_context():
        agency = Agency(
            name="Test Police Department"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="123456",
            first_name="JANE",
            middle_name="A",
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

        return agency.id, officer.id


def test_officer_compliance_profile_endpoint(app):
    agency_id, officer_id = seed_officer(app)

    client = app.test_client()

    response = client.get(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/compliance/profile"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["officer"]["tcole_pid"] == "123456"
    assert "overall_status" in data
    assert "components" in data
    assert set(data["components"]) == {
        "PEACE_OFFICER",
        "COUNTY_JAILER",
        "TELECOMMUNICATOR",
        "POLICE_CHIEF",
        "SUPERVISOR",
        "PUBLIC_INFORMATION_OFFICER",
    }


def test_officer_compliance_profile_endpoint_is_tenant_scoped(app):
    with app.app_context():
        agency_one = Agency(
            name="Agency One"
        )
        agency_two = Agency(
            name="Agency Two"
        )

        db.session.add_all([
            agency_one,
            agency_two,
        ])
        db.session.flush()

        officer = Officer(
            agency_id=agency_one.id,
            tcole_pid="123456",
            first_name="JANE",
            last_name="SMITH",
        )

        db.session.add(officer)
        db.session.commit()

        agency_one_id = agency_one.id
        agency_two_id = agency_two.id
        officer_id = officer.id

    client = app.test_client()

    response = client.get(
        f"/api/agencies/{agency_two_id}"
        f"/officers/{officer_id}"
        "/compliance/profile"
    )

    assert response.status_code == 404
