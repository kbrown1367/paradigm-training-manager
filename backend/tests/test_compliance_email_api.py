from datetime import date

import pytest

from app import create_app
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


@pytest.fixture()
def client(app):
    return app.test_client()


def seed(app):
    with app.app_context():
        agency = Agency(
            name="Test Department",
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

        db.session.commit()

        return str(agency.id), str(officer.id)


def test_compliance_email_endpoint(app, client):
    agency_id, officer_id = seed(app)

    response = client.get(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/compliance-email"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["recipient"] == (
        "jdoe@example.gov"
    )
    assert data["can_email"] is True
    assert "subject" in data
    assert "body" in data


def test_compliance_email_endpoint_is_tenant_scoped(
    app,
    client,
):
    _, officer_id = seed(app)

    with app.app_context():
        other = Agency(name="Other Department")
        db.session.add(other)
        db.session.commit()

        other_id = str(other.id)

    response = client.get(
        f"/api/agencies/{other_id}"
        f"/officers/{officer_id}"
        "/compliance-email"
    )

    assert response.status_code == 404


def test_compliance_email_endpoint_accepts_peace_officer_track(
    app,
    client,
):
    agency_id, officer_id = seed(app)

    response = client.get(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/compliance-email?track=peace_officer"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["subject"] == (
        "TCOLE Peace Officer Compliance Status"
    )


def test_compliance_email_endpoint_accepts_combined_track(
    app,
    client,
):
    agency_id, officer_id = seed(app)

    response = client.get(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/compliance-email?track=combined"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["subject"] == (
        "TCOLE Compliance Status"
    )


def test_compliance_email_endpoint_rejects_invalid_track(
    app,
    client,
):
    agency_id, officer_id = seed(app)

    response = client.get(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/compliance-email?track=invalid"
    )

    assert response.status_code == 400

    data = response.get_json()

    assert "Invalid compliance email track" in data["error"]
