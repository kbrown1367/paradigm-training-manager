from datetime import date

from app import create_app
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAssignment,
)


def make_app():
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )


def seed_officer(app):
    with app.app_context():
        db.create_all()

        agency = Agency(
            name="Test Police Department"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="123456",
            first_name="JOHN",
            last_name="SMITH",
        )
        db.session.add(officer)
        db.session.commit()

        return agency.id, officer.id


def test_assignment_types_endpoint():
    app = make_app()

    with app.app_context():
        db.create_all()

    client = app.test_client()

    response = client.get(
        "/api/assignment-types"
    )

    assert response.status_code == 200

    data = response.get_json()

    values = {
        item["assignment_type"]
        for item in data
    }

    assert "POLICE_CHIEF" in values
    assert "SUPERVISOR" in values
    assert (
        "PUBLIC_INFORMATION_OFFICER"
        in values
    )


def test_officer_list_excludes_archived_by_default():
    app = make_app()

    with app.app_context():
        db.create_all()

        agency = Agency(
            name="Test Police Department"
        )
        db.session.add(agency)
        db.session.flush()

        active = Officer(
            agency_id=agency.id,
            tcole_pid="111111",
            first_name="ACTIVE",
            last_name="OFFICER",
        )

        archived = Officer(
            agency_id=agency.id,
            tcole_pid="222222",
            first_name="ARCHIVED",
            last_name="OFFICER",
            employment_status="archived",
        )

        db.session.add_all(
            [active, archived]
        )
        db.session.commit()

        agency_id = agency.id

    client = app.test_client()

    response = client.get(
        f"/api/agencies/{agency_id}/officers"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["tcole_pid"] == "111111"


def test_officer_list_can_include_archived():
    app = make_app()

    with app.app_context():
        db.create_all()

        agency = Agency(
            name="Test Police Department"
        )
        db.session.add(agency)
        db.session.flush()

        db.session.add_all(
            [
                Officer(
                    agency_id=agency.id,
                    tcole_pid="111111",
                    first_name="ACTIVE",
                    last_name="OFFICER",
                ),
                Officer(
                    agency_id=agency.id,
                    tcole_pid="222222",
                    first_name="ARCHIVED",
                    last_name="OFFICER",
                    employment_status="archived",
                ),
            ]
        )

        db.session.commit()
        agency_id = agency.id

    client = app.test_client()

    response = client.get(
        f"/api/agencies/{agency_id}"
        "/officers?include_archived=true"
    )

    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_assignment_can_be_activated():
    app = make_app()
    agency_id, officer_id = seed_officer(
        app
    )

    client = app.test_client()

    response = client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/POLICE_CHIEF",
        json={
            "effective_date": "2020-10-01"
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["active"] is True
    assert (
        data["assignment_type"]
        == "POLICE_CHIEF"
    )
    assert (
        data["effective_date"]
        == "2020-10-01"
    )

    with app.app_context():
        assert (
            OfficerAssignment.query.count()
            == 1
        )


def test_duplicate_active_assignment_is_rejected():
    app = make_app()
    agency_id, officer_id = seed_officer(
        app
    )

    client = app.test_client()

    first = client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/POLICE_CHIEF",
        json={
            "effective_date": "2020-10-01"
        },
    )

    second = client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/POLICE_CHIEF",
        json={
            "effective_date": "2021-01-01"
        },
    )

    assert first.status_code == 201
    assert second.status_code == 400

    with app.app_context():
        assert (
            OfficerAssignment.query.count()
            == 1
        )


def test_assignment_can_be_ended():
    app = make_app()
    agency_id, officer_id = seed_officer(
        app
    )

    client = app.test_client()

    client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/PUBLIC_INFORMATION_OFFICER",
        json={
            "effective_date": "2024-01-01"
        },
    )

    response = client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/PUBLIC_INFORMATION_OFFICER",
        json={
            "end_date": "2026-08-08"
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["active"] is False
    assert data["end_date"] == "2026-08-08"


def test_assignment_history_is_preserved():
    app = make_app()
    agency_id, officer_id = seed_officer(
        app
    )

    client = app.test_client()

    client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/SUPERVISOR",
        json={
            "effective_date": "2020-01-01"
        },
    )

    client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/SUPERVISOR",
        json={
            "end_date": "2022-01-01"
        },
    )

    client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/SUPERVISOR",
        json={
            "effective_date": "2025-01-01"
        },
    )

    response = client.get(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 2
    assert data[0]["active"] is False
    assert data[1]["active"] is True


def test_assignment_summary_returns_switch_states():
    app = make_app()
    agency_id, officer_id = seed_officer(
        app
    )

    client = app.test_client()

    client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/POLICE_CHIEF",
        json={
            "effective_date": "2020-10-01"
        },
    )

    response = client.get(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignment-summary"
    )

    assert response.status_code == 200

    data = response.get_json()

    chief = next(
        item
        for item
        in data["assignment_types"]
        if item["assignment_type"]
        == "POLICE_CHIEF"
    )

    pio = next(
        item
        for item
        in data["assignment_types"]
        if item["assignment_type"]
        == "PUBLIC_INFORMATION_OFFICER"
    )

    assert chief["active"] is True
    assert (
        chief["effective_date"]
        == "2020-10-01"
    )
    assert pio["active"] is False
