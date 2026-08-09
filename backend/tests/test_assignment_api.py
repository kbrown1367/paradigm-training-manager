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
            "inactive_date": "2026-08-08"
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["active"] is False
    assert data["end_date"] == "2026-08-07"


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
            "inactive_date": "2022-01-01"
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


def test_only_one_active_police_chief_per_agency():
    app = make_app()

    with app.app_context():
        db.create_all()

        agency = Agency(
            name="Test Police Department"
        )
        db.session.add(agency)
        db.session.flush()

        first = Officer(
            agency_id=agency.id,
            tcole_pid="111111",
            first_name="FIRST",
            last_name="CHIEF",
        )
        second = Officer(
            agency_id=agency.id,
            tcole_pid="222222",
            first_name="SECOND",
            last_name="OFFICER",
        )

        db.session.add_all([first, second])
        db.session.commit()

        agency_id = agency.id
        first_id = first.id
        second_id = second.id

    client = app.test_client()

    response = client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{first_id}"
        "/assignments/POLICE_CHIEF",
        json={
            "effective_date": "2020-10-01"
        },
    )

    assert response.status_code == 201

    response = client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{second_id}"
        "/assignments/POLICE_CHIEF",
        json={
            "effective_date": "2026-01-01"
        },
    )

    assert response.status_code == 400
    assert (
        "already assigned"
        in response.get_json()["error"]
    )

    with app.app_context():
        active_chiefs = (
            OfficerAssignment.query
            .filter_by(
                agency_id=agency_id,
                assignment_type="POLICE_CHIEF",
                end_date=None,
            )
            .count()
        )

        assert active_chiefs == 1


def test_police_chief_slot_reopens_after_assignment_ends():
    app = make_app()

    with app.app_context():
        db.create_all()

        agency = Agency(
            name="Test Police Department"
        )
        db.session.add(agency)
        db.session.flush()

        first = Officer(
            agency_id=agency.id,
            tcole_pid="111111",
            first_name="FIRST",
            last_name="CHIEF",
        )
        second = Officer(
            agency_id=agency.id,
            tcole_pid="222222",
            first_name="SECOND",
            last_name="CHIEF",
        )

        db.session.add_all([first, second])
        db.session.commit()

        agency_id = agency.id
        first_id = first.id
        second_id = second.id

    client = app.test_client()

    client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{first_id}"
        "/assignments/POLICE_CHIEF",
        json={
            "effective_date": "2020-10-01"
        },
    )

    ended = client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{first_id}"
        "/assignments/POLICE_CHIEF",
        json={
            "inactive_date": "2026-07-31"
        },
    )

    assert ended.status_code == 200

    response = client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{second_id}"
        "/assignments/POLICE_CHIEF",
        json={
            "effective_date": "2026-08-01"
        },
    )

    assert response.status_code == 201


def test_assignment_summary_identifies_current_chief():
    app = make_app()
    agency_id, officer_id = seed_officer(app)

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

    assert data["chief_holder"] is not None
    assert (
        data["chief_holder"]["officer_id"]
        == str(officer_id)
    )
    assert data["chief_holder"]["name"] == "JOHN SMITH"


def test_ended_assignment_is_not_active_on_inactive_date():
    app = make_app()
    agency_id, officer_id = seed_officer(app)

    client = app.test_client()

    activated = client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/PUBLIC_INFORMATION_OFFICER",
        json={
            "effective_date": "2026-05-01"
        },
    )

    assert activated.status_code == 201

    ended = client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/PUBLIC_INFORMATION_OFFICER",
        json={
            "inactive_date": "2026-08-09"
        },
    )

    assert ended.status_code == 200
    assert (
        ended.get_json()["end_date"]
        == "2026-08-08"
    )

    with app.app_context():
        from app.compliance.public_information_officer import (
            evaluate_public_information_officer,
        )

        officer = db.session.get(
            Officer,
            officer_id,
        )

        result = evaluate_public_information_officer(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["applicable"] is False
        assert result["status"] == "NOT_APPLICABLE"


def test_same_day_assignment_toggle_removes_assignment():
    app = make_app()
    agency_id, officer_id = seed_officer(app)

    client = app.test_client()

    activated = client.post(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/PUBLIC_INFORMATION_OFFICER",
        json={
            "effective_date": "2026-08-09"
        },
    )

    assert activated.status_code == 201

    ended = client.patch(
        f"/api/agencies/{agency_id}"
        f"/officers/{officer_id}"
        "/assignments/PUBLIC_INFORMATION_OFFICER",
        json={
            "inactive_date": "2026-08-09"
        },
    )

    assert ended.status_code == 200
    assert (
        ended.get_json()["removed_same_day"]
        is True
    )

    with app.app_context():
        assert (
            OfficerAssignment.query
            .filter_by(
                agency_id=agency_id,
                officer_id=officer_id,
                assignment_type=(
                    "PUBLIC_INFORMATION_OFFICER"
                ),
            )
            .count()
            == 0
        )
