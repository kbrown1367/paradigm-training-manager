from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.public_information_officer import (
    evaluate_public_information_officer,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAssignment,
    OfficerCredentialVerification,
    TrainingRecord,
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


def seed_pio(app):
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
            last_name="SMITH",
        )
        db.session.add(officer)
        db.session.flush()

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type=(
                    "PUBLIC_INFORMATION_OFFICER"
                ),
                effective_date=date(2026, 1, 1),
            )
        )

        db.session.add(
            TrainingRecord(
                agency_id=agency.id,
                officer_id=officer.id,
                course_number="666038",
                course_title="PIO Course",
                course_date=date(2026, 6, 1),
                credited_hours=Decimal("8"),
                hours_source="TCOLE_CYCLE_REPORT",
            )
        )

        db.session.commit()

        return agency.id, officer.id


def test_tdem_verification_can_be_created(app):
    agency_id, officer_id = seed_pio(app)

    client = app.test_client()

    response = client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/credential-verifications/"
        "TDEM_PIO_CERTIFICATION",
        json={
            "effective_date": "2026-06-15",
            "verified_by": "Training Coordinator",
            "reference": "TDEM Certificate 12345",
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["status"] == "VERIFIED"
    assert data["active"] is True
    assert (
        data["effective_date"]
        == "2026-06-15"
    )


def test_duplicate_active_verification_rejected(app):
    agency_id, officer_id = seed_pio(app)

    client = app.test_client()

    url = (
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/credential-verifications/"
        "TDEM_PIO_CERTIFICATION"
    )

    first = client.post(
        url,
        json={
            "effective_date": "2026-06-15"
        },
    )

    second = client.post(
        url,
        json={
            "effective_date": "2026-07-01"
        },
    )

    assert first.status_code == 201
    assert second.status_code == 400

    with app.app_context():
        assert (
            OfficerCredentialVerification.query.count()
            == 1
        )


def test_verification_can_be_revoked(app):
    agency_id, officer_id = seed_pio(app)

    client = app.test_client()

    base = (
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/credential-verifications/"
        "TDEM_PIO_CERTIFICATION"
    )

    client.post(
        base,
        json={
            "effective_date": "2026-06-15"
        },
    )

    response = client.patch(
        base + "/revoke"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["active"] is False
    assert data["status"] == "REVOKED"
    assert data["revoked_at"] is not None


def test_pio_training_plus_tdem_is_compliant(app):
    agency_id, officer_id = seed_pio(app)

    with app.app_context():
        officer = db.session.get(
            Officer,
            officer_id,
        )

        db.session.add(
            OfficerCredentialVerification(
                agency_id=agency_id,
                officer_id=officer_id,
                credential_type=(
                    "TDEM_PIO_CERTIFICATION"
                ),
                status="VERIFIED",
                effective_date=date(2026, 6, 15),
                verified_by="Training Coordinator",
            )
        )

        db.session.commit()

        result = (
            evaluate_public_information_officer(
                officer,
                evaluation_date=date(2026, 8, 8),
            )
        )

        assert result["training_completed"] is True
        assert (
            result[
                "tdem_certification_verified"
            ]
            is True
        )
        assert (
            result[
                "tdem_certification_status"
            ]
            == "VERIFIED"
        )
        assert result["status"] == "COMPLIANT"
        assert result["deficiencies"] == []


def test_revoked_tdem_returns_pio_to_pending(app):
    agency_id, officer_id = seed_pio(app)

    with app.app_context():
        officer = db.session.get(
            Officer,
            officer_id,
        )

        db.session.add(
            OfficerCredentialVerification(
                agency_id=agency_id,
                officer_id=officer_id,
                credential_type=(
                    "TDEM_PIO_CERTIFICATION"
                ),
                status="REVOKED",
                effective_date=date(2026, 6, 15),
            )
        )

        db.session.commit()

        result = (
            evaluate_public_information_officer(
                officer,
                evaluation_date=date(2026, 8, 8),
            )
        )

        assert result["training_completed"] is True
        assert (
            result[
                "tdem_certification_verified"
            ]
            is False
        )
        assert result["status"] == "PENDING"
