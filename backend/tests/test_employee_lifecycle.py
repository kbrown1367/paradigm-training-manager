from datetime import date
from uuid import UUID

import pytest

from app import create_app
from app.auth import (
    ROLE_AGENCY_ADMIN,
    hash_password,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAward,
    TrainingRecord,
    User,
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY":
                "employee-lifecycle-test-secret",
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def seed_two_agencies(app):
    with app.app_context():
        agency_a = Agency(
            name="Alpha Police Department",
        )
        agency_b = Agency(
            name="Bravo Police Department",
        )

        db.session.add_all([
            agency_a,
            agency_b,
        ])
        db.session.flush()

        officer_a = Officer(
            agency_id=agency_a.id,
            tcole_pid="100001",
            first_name="ALPHA",
            last_name="OFFICER",
        )

        officer_b = Officer(
            agency_id=agency_b.id,
            tcole_pid="200001",
            first_name="BRAVO",
            last_name="OFFICER",
        )

        db.session.add_all([
            officer_a,
            officer_b,
        ])
        db.session.flush()

        db.session.add(
            OfficerAward(
                agency_id=agency_a.id,
                officer_id=officer_a.id,
                award_type="License",
                award_name="Peace Officer License",
                award_date=date(2020, 1, 1),
            )
        )

        db.session.add(
            TrainingRecord(
                agency_id=agency_a.id,
                officer_id=officer_a.id,
                course_number="3189",
                course_title=(
                    "State and Federal Law Update"
                ),
                course_date=date(2026, 1, 1),
                credited_hours=4,
                source="TCOLE",
            )
        )

        admin_a = User(
            agency_id=agency_a.id,
            email="admin@alpha.gov",
            password_hash=hash_password(
                "PilotPassword123!"
            ),
            first_name="Alpha",
            last_name="Admin",
            role=ROLE_AGENCY_ADMIN,
            status="active",
        )

        db.session.add(admin_a)
        db.session.commit()

        return {
            "agency_a_id": str(agency_a.id),
            "agency_b_id": str(agency_b.id),
            "officer_a_id": str(officer_a.id),
            "officer_b_id": str(officer_b.id),
        }


def login_alpha(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@alpha.gov",
            "password": "PilotPassword123!",
        },
    )

    assert response.status_code == 200


def test_archive_employee_sets_lifecycle_fields(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    response = client.post(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/archive",
        json={
            "reason": "Separated from agency.",
        },
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert (
        payload["employment_status"]
        == "archived"
    )
    assert payload["archived_at"] is not None
    assert (
        payload["archived_reason"]
        == "Separated from agency."
    )

    with app.app_context():
        officer = db.session.get(
            Officer,
            UUID(data["officer_a_id"]),
        )

        assert (
            officer.employment_status
            == "archived"
        )
        assert officer.archived_at is not None
        assert (
            officer.archived_reason
            == "Separated from agency."
        )


def test_archive_reason_is_optional(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    response = client.post(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/archive",
        json={},
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["archived_reason"] is None


def test_archive_preserves_history(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    response = client.post(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/archive",
        json={
            "reason": "Separated.",
        },
    )

    assert response.status_code == 200

    with app.app_context():
        assert Officer.query.count() == 2
        assert OfficerAward.query.count() == 1
        assert TrainingRecord.query.count() == 1


def test_archived_employee_removed_from_default_list(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    client.post(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/archive",
        json={},
    )

    response = client.get(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers"
    )

    assert response.status_code == 200
    assert response.get_json() == []


def test_archived_employee_available_in_archived_list(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    client.post(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/archive",
        json={
            "reason": "Retired.",
        },
    )

    response = client.get(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers?include_archived=true"
    )

    assert response.status_code == 200

    archived = [
        officer
        for officer in response.get_json()
        if (
            officer["employment_status"]
            == "archived"
        )
    ]

    assert len(archived) == 1
    assert (
        archived[0]["id"]
        == data["officer_a_id"]
    )


def test_archived_workspace_exposes_status(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    client.post(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/archive",
        json={
            "reason": "Retired.",
        },
    )

    response = client.get(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/workspace"
    )

    assert response.status_code == 200

    officer = response.get_json()["officer"]

    assert (
        officer["employment_status"]
        == "archived"
    )
    assert officer["archived_at"] is not None
    assert officer["archived_reason"] == "Retired."


def test_restore_employee_returns_employee_to_active(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    client.post(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/archive",
        json={
            "reason": "Temporary separation.",
        },
    )

    response = client.post(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/restore",
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["employment_status"] == "active"
    assert payload["archived_at"] is None
    assert payload["archived_reason"] is None


def test_restored_employee_returns_to_default_list(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    base = (
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
    )

    client.post(
        base + "/archive",
        json={},
    )

    client.post(
        base + "/restore",
    )

    response = client.get(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers"
    )

    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_agency_admin_cannot_archive_other_agency_employee(
    app,
):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    response = client.post(
        "/api/agencies/"
        f"{data['agency_b_id']}"
        "/officers/"
        f"{data['officer_b_id']}"
        "/archive",
        json={},
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Resource not found.",
    }


def test_agency_admin_cannot_restore_other_agency_employee(
    app,
):
    data = seed_two_agencies(app)

    with app.app_context():
        officer = db.session.get(
            Officer,
            UUID(data["officer_b_id"]),
        )

        officer.employment_status = "archived"
        db.session.commit()

    client = app.test_client()
    login_alpha(client)

    response = client.post(
        "/api/agencies/"
        f"{data['agency_b_id']}"
        "/officers/"
        f"{data['officer_b_id']}"
        "/restore",
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Resource not found.",
    }


def test_archive_rejects_already_archived_employee(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    url = (
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/archive"
    )

    first = client.post(
        url,
        json={},
    )
    second = client.post(
        url,
        json={},
    )

    assert first.status_code == 200
    assert second.status_code == 400


def test_restore_rejects_active_employee(app):
    data = seed_two_agencies(app)
    client = app.test_client()
    login_alpha(client)

    response = client.post(
        "/api/agencies/"
        f"{data['agency_a_id']}"
        "/officers/"
        f"{data['officer_a_id']}"
        "/restore",
    )

    assert response.status_code == 400
