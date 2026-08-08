from datetime import date

from app import create_app
from app.extensions import db
from app.models import Agency, Officer, OfficerAward


def test_peace_officer_compliance_endpoint():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()

        agency = Agency(name="Test Police Department")
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
        agency_id = agency.id

    client = app.test_client()

    response = client.get(
        f"/api/agencies/{agency_id}/compliance/peace-officer-unit"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["rule_set_id"] == "PO-UNIT"
    assert data["cycle_start"] == "2025-09-01"
    assert data["cycle_end"] == "2029-08-31"
    assert data["unit_number"] == 1
    assert data["unit_start"] == "2025-09-01"
    assert data["unit_end"] == "2027-08-31"
    assert data["due_date"] == "2027-08-31"
    assert data["officer_count"] == 1
    assert data["complete_count"] == 0
    assert data["outstanding_count"] == 1
    assert data["overdue_count"] == 0
    assert data["applicability_status"] == "PROVISIONAL"
    assert len(data["officers"]) == 1
