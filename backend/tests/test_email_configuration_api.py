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


def seed(app):
    with app.app_context():
        agency = Agency(
            name="Test Police Department"
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
        db.session.commit()

        return str(agency.id), str(officer.id)


def test_agency_email_configuration(app, client):
    agency_id, _ = seed(app)

    response = client.patch(
        f"/api/agencies/{agency_id}"
        "/email-configuration",
        json={
            "email_domain": "@example.gov",
            "email_pattern": "FIRST_INITIAL_LAST",
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["email_domain"] == "example.gov"
    assert (
        data["email_pattern"]
        == "FIRST_INITIAL_LAST"
    )


def test_invalid_email_pattern(app, client):
    agency_id, _ = seed(app)

    response = client.patch(
        f"/api/agencies/{agency_id}"
        "/email-configuration",
        json={
            "email_domain": "example.gov",
            "email_pattern": "INVALID",
        },
    )

    assert response.status_code == 400


def test_officer_email_override(app, client):
    agency_id, officer_id = seed(app)

    client.patch(
        f"/api/agencies/{agency_id}"
        "/email-configuration",
        json={
            "email_domain": "example.gov",
            "email_pattern": "FIRST_INITIAL_LAST",
        },
    )

    response = client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}/email",
        json={
            "email_override":
                "special@example.gov"
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert (
        data["resolved_email"]["email"]
        == "special@example.gov"
    )
    assert (
        data["resolved_email"]["source"]
        == "OFFICER_OVERRIDE"
    )


def test_clear_override_returns_to_pattern(
    app,
    client,
):
    agency_id, officer_id = seed(app)

    client.patch(
        f"/api/agencies/{agency_id}"
        "/email-configuration",
        json={
            "email_domain": "example.gov",
            "email_pattern": "FIRST_INITIAL_LAST",
        },
    )

    client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}/email",
        json={
            "email_override":
                "special@example.gov"
        },
    )

    response = client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}/email",
        json={
            "email_override": ""
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["email_override"] is None
    assert (
        data["resolved_email"]["email"]
        == "jsmith@example.gov"
    )
    assert (
        data["resolved_email"]["source"]
        == "AGENCY_PATTERN"
    )


def test_officer_email_is_tenant_scoped(
    app,
    client,
):
    agency_id, officer_id = seed(app)

    with app.app_context():
        other = Agency(name="Other Department")
        db.session.add(other)
        db.session.commit()
        other_id = str(other.id)

    response = client.patch(
        f"/api/agencies/{other_id}"
        f"/officers/{officer_id}/email",
        json={
            "email_override":
                "wrong@example.gov"
        },
    )

    assert response.status_code == 404
