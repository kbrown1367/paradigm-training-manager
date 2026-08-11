from datetime import date
import uuid

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
            tcole_pid="123456",
            first_name="Jane",
            last_name="Smith",
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


def test_bulk_preflight_endpoint(app, client):
    agency_id, _ = seed(app)

    response = client.get(
        f"/api/agencies/{agency_id}"
        "/compliance/communications/preflight"
        "?evaluation_date=2026-08-11"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["evaluation_date"] == "2026-08-11"
    assert data["summary"]["total_employees"] == 1
    assert len(data["recipients"]) == 1

    recipient = data["recipients"][0]

    assert recipient["tcole_pid"] == "123456"
    assert recipient["agency_id"] == agency_id
    assert recipient["preflight_status"] == "READY"
    assert (
        recipient["communication_track"]
        == "peace_officer"
    )


def test_bulk_preflight_endpoint_rejects_bad_date(
    app,
    client,
):
    agency_id, _ = seed(app)

    response = client.get(
        f"/api/agencies/{agency_id}"
        "/compliance/communications/preflight"
        "?evaluation_date=08-11-2026"
    )

    assert response.status_code == 400

    data = response.get_json()

    assert (
        data["error"]
        == "evaluation_date must use YYYY-MM-DD format."
    )


def test_bulk_preflight_endpoint_missing_agency(
    app,
    client,
):
    response = client.get(
        f"/api/agencies/{uuid.uuid4()}"
        "/compliance/communications/preflight"
        "?evaluation_date=2026-08-11"
    )

    assert response.status_code == 404


def test_bulk_preflight_endpoint_is_tenant_scoped(
    app,
    client,
):
    agency_a_id, _ = seed(app)

    with app.app_context():
        agency_b = Agency(
            name="Other Department",
            email_domain="other.gov",
            email_pattern="FIRST_INITIAL_LAST",
        )

        db.session.add(agency_b)
        db.session.flush()

        officer_b = Officer(
            agency_id=agency_b.id,
            tcole_pid="999999",
            first_name="Other",
            last_name="Officer",
        )

        db.session.add(officer_b)
        db.session.flush()

        db.session.add(
            OfficerAward(
                agency_id=agency_b.id,
                officer_id=officer_b.id,
                award_type="License",
                award_name="Peace Officer License",
                award_date=date(2020, 1, 1),
            )
        )

        db.session.commit()

    response = client.get(
        f"/api/agencies/{agency_a_id}"
        "/compliance/communications/preflight"
        "?evaluation_date=2026-08-11"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert {
        item["tcole_pid"]
        for item in data["recipients"]
    } == {"123456"}
