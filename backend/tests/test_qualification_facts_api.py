import pytest

from app import create_app
from app.extensions import db
from app.models import Agency, Officer


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
    agency = Agency(name="Test Department")
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="Jane",
        last_name="Smith",
    )
    db.session.add(officer)
    db.session.commit()

    return agency, officer


def test_military_defaults_to_zero(app):
    with app.app_context():
        _, officer = make_officer()

        assert officer.verified_military_months == 0


def test_update_qualification_facts(app, client):
    with app.app_context():
        agency, officer = make_officer()
        agency_id = str(agency.id)
        officer_id = str(officer.id)

    response = client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/qualification-facts",
        json={
            "verified_education_level": "BACHELOR",
            "verified_military_months": 48,
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert (
        data["verified_education_level"]
        == "BACHELOR"
    )
    assert data["verified_military_months"] == 48


def test_invalid_education_rejected(app, client):
    with app.app_context():
        agency, officer = make_officer()
        agency_id = str(agency.id)
        officer_id = str(officer.id)

    response = client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/qualification-facts",
        json={
            "verified_education_level": "HIGH_SCHOOL"
        },
    )

    assert response.status_code == 400


def test_negative_military_rejected(app, client):
    with app.app_context():
        agency, officer = make_officer()
        agency_id = str(agency.id)
        officer_id = str(officer.id)

    response = client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/qualification-facts",
        json={
            "verified_military_months": -1
        },
    )

    assert response.status_code == 400


def test_qualification_facts_are_tenant_scoped(
    app,
    client,
):
    with app.app_context():
        _, officer = make_officer()

        other_agency = Agency(name="Other Department")
        db.session.add(other_agency)
        db.session.commit()

        agency_id = str(other_agency.id)
        officer_id = str(officer.id)

    response = client.get(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/qualification-facts"
    )

    assert response.status_code == 404
