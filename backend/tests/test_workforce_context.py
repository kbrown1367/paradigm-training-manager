from datetime import date, datetime, timezone

from app import create_app
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAssignment,
)
from app.compliance.training_calendar import (
    get_cycle,
    get_unit,
)


def make_app():
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )


def test_officer_can_have_multiple_assignments():
    app = make_app()

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
        db.session.flush()

        db.session.add_all(
            [
                OfficerAssignment(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    assignment_type="POLICE_CHIEF",
                    effective_date=date(2025, 1, 1),
                ),
                OfficerAssignment(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    assignment_type="PUBLIC_INFORMATION_OFFICER",
                    effective_date=date(2026, 1, 1),
                ),
            ]
        )

        db.session.commit()

        assert len(officer.assignments) == 2


def test_officer_can_be_archived_without_deletion():
    app = make_app()

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

        officer_id = officer.id

        officer.employment_status = "archived"
        officer.archived_at = datetime.now(
            timezone.utc
        )
        officer.archived_reason = (
            "No longer employed by agency."
        )

        db.session.commit()

        archived = db.session.get(
            Officer,
            officer_id,
        )

        assert archived is not None
        assert archived.employment_status == "archived"
        assert archived.archived_at is not None


def test_current_training_cycle():
    cycle = get_cycle(
        date(2026, 8, 8)
    )

    assert cycle["start"] == date(2025, 9, 1)
    assert cycle["end"] == date(2029, 8, 31)


def test_current_first_training_unit():
    unit = get_unit(
        date(2026, 8, 8)
    )

    assert unit["unit_number"] == 1
    assert unit["start"] == date(2025, 9, 1)
    assert unit["end"] == date(2027, 8, 31)


def test_current_second_training_unit():
    unit = get_unit(
        date(2028, 1, 1)
    )

    assert unit["unit_number"] == 2
    assert unit["start"] == date(2027, 9, 1)
    assert unit["end"] == date(2029, 8, 31)


def test_next_training_cycle():
    cycle = get_cycle(
        date(2030, 1, 1)
    )

    assert cycle["start"] == date(2029, 9, 1)
    assert cycle["end"] == date(2033, 8, 31)


def test_future_training_cycle_repeats_indefinitely():
    unit = get_unit(
        date(2040, 5, 1)
    )

    assert unit["start"] == date(2039, 9, 1)
    assert unit["end"] == date(2041, 8, 31)
    assert unit["unit_number"] == 2
