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
            "AUTHORIZATION_DISABLED": True,
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


def add_peace_officer(agency):
    officer = Officer(
        agency_id=agency.id,
        tcole_pid="500500",
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

    return officer


def test_compliance_report_endpoint_returns_pdf(
    app,
    client,
):
    with app.app_context():
        agency = Agency(
            name="Example Police Department",
        )

        db.session.add(agency)
        db.session.flush()

        add_peace_officer(agency)

        db.session.commit()

        agency_id = agency.id

    response = client.get(
        f"/api/agencies/{agency_id}"
        "/reports/compliance.pdf"
    )

    assert response.status_code == 200

    assert (
        response.content_type
        == "application/pdf"
    )

    assert response.data.startswith(
        b"%PDF"
    )

    disposition = response.headers.get(
        "Content-Disposition",
        "",
    )

    assert "attachment" in disposition
    assert "compliance-report.pdf" in disposition


def test_unknown_agency_report_returns_404(
    client,
):
    import uuid

    response = client.get(
        f"/api/agencies/{uuid.uuid4()}"
        "/reports/compliance.pdf"
    )

    assert response.status_code == 404
