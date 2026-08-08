from datetime import date

import pytest

from app import create_app
from app.compliance.agency_dashboard import (
    evaluate_agency_compliance_dashboard,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAssignment,
    OfficerAward,
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


def add_peace_officer(
    agency,
    pid,
    first_name,
    last_name,
):
    officer = Officer(
        agency_id=agency.id,
        tcole_pid=pid,
        first_name=first_name,
        last_name=last_name,
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


def test_dashboard_returns_active_employees(app):
    with app.app_context():
        agency = Agency(
            name="Dashboard Test Agency"
        )
        db.session.add(agency)
        db.session.flush()

        active = add_peace_officer(
            agency,
            "100001",
            "JANE",
            "SMITH",
        )

        archived = add_peace_officer(
            agency,
            "100002",
            "JOHN",
            "DOE",
        )
        archived.employment_status = "archived"

        db.session.commit()

        result = evaluate_agency_compliance_dashboard(
            agency.id,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["summary"][
            "active_employee_count"
        ] == 1

        assert len(result["employees"]) == 1

        assert (
            result["employees"][0]["tcole_pid"]
            == "100001"
        )


def test_dashboard_summary_counts_statuses(app):
    with app.app_context():
        agency = Agency(
            name="Summary Test Agency"
        )
        db.session.add(agency)
        db.session.flush()

        due_officer = add_peace_officer(
            agency,
            "200001",
            "JANE",
            "SMITH",
        )

        noncompliant_officer = add_peace_officer(
            agency,
            "200002",
            "CHRIS",
            "THAI",
        )

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=noncompliant_officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2023, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_agency_compliance_dashboard(
            agency.id,
            evaluation_date=date(2026, 8, 8),
        )

        summary = result["summary"]

        assert summary["active_employee_count"] == 2
        assert summary["due_count"] == 1
        assert summary["noncompliant_count"] == 1
        assert summary["compliant_count"] == 0


def test_dashboard_sorts_noncompliant_before_due(app):
    with app.app_context():
        agency = Agency(
            name="Sort Test Agency"
        )
        db.session.add(agency)
        db.session.flush()

        due_officer = add_peace_officer(
            agency,
            "300001",
            "ALPHA",
            "ABLE",
        )

        noncompliant_officer = add_peace_officer(
            agency,
            "300002",
            "ZULU",
            "ZEBRA",
        )

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=noncompliant_officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2023, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_agency_compliance_dashboard(
            agency.id,
            evaluation_date=date(2026, 8, 8),
        )

        employees = result["employees"]

        assert (
            employees[0]["overall_status"]
            == "NONCOMPLIANT"
        )

        assert (
            employees[1]["overall_status"]
            == "DUE"
        )


def test_dashboard_returns_active_assignments(app):
    with app.app_context():
        agency = Agency(
            name="Assignment Dashboard Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = add_peace_officer(
            agency,
            "400001",
            "JANE",
            "SMITH",
        )

        db.session.add_all(
            [
                OfficerAssignment(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    assignment_type="SUPERVISOR",
                    effective_date=date(2026, 1, 1),
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

        result = evaluate_agency_compliance_dashboard(
            agency.id,
            evaluation_date=date(2026, 8, 8),
        )

        assignments = result["employees"][0][
            "assignments"
        ]

        assert assignments == [
            "PUBLIC_INFORMATION_OFFICER",
            "SUPERVISOR",
        ]


def test_dashboard_limits_priority_findings_to_three(app):
    with app.app_context():
        agency = Agency(
            name="Priority Findings Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = add_peace_officer(
            agency,
            "500001",
            "JANE",
            "SMITH",
        )

        db.session.commit()

        result = evaluate_agency_compliance_dashboard(
            agency.id,
            evaluation_date=date(2026, 8, 8),
        )

        findings = result["employees"][0][
            "priority_findings"
        ]

        assert len(findings) <= 3


def test_dashboard_includes_non_peace_officer(app):
    with app.app_context():
        agency = Agency(
            name="Mixed Workforce Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="600001",
            first_name="ALEX",
            last_name="DISPATCHER",
        )

        db.session.add(officer)
        db.session.commit()

        result = evaluate_agency_compliance_dashboard(
            agency.id,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["summary"][
            "active_employee_count"
        ] == 1

        assert (
            result["employees"][0]["tcole_pid"]
            == "600001"
        )


def test_dashboard_returns_none_for_unknown_agency(app):
    with app.app_context():
        import uuid

        result = evaluate_agency_compliance_dashboard(
            uuid.uuid4(),
            evaluation_date=date(2026, 8, 8),
        )

        assert result is None


def test_dashboard_treats_future_pio_requirement_as_due(app):
    with app.app_context():
        agency = Agency(
            name="PIO Dashboard Test Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = add_peace_officer(
            agency,
            "700001",
            "LEE",
            "ROGERS",
        )

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type=
                    "PUBLIC_INFORMATION_OFFICER",
                effective_date=date(2026, 5, 1),
            )
        )

        db.session.commit()

        result = evaluate_agency_compliance_dashboard(
            agency.id,
            evaluation_date=date(2026, 8, 8),
        )

        employee = result["employees"][0]

        assert employee["overall_status"] == "DUE"
        assert (
            result["summary"]["due_count"]
            == 1
        )
        assert (
            result["summary"][
                "pending_review_count"
            ]
            == 0
        )


def test_dashboard_counts_noncovered_employee_as_not_evaluated(app):
    with app.app_context():
        agency = Agency(
            name="Coverage Dashboard Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="999002",
            first_name="ALEX",
            last_name="DISPATCHER",
        )

        db.session.add(officer)
        db.session.commit()

        result = evaluate_agency_compliance_dashboard(
            agency.id,
            evaluation_date=date(2026, 8, 8),
        )

        employee = result["employees"][0]

        assert (
            employee["overall_status"]
            == "NOT_EVALUATED"
        )
        assert (
            result["summary"]["not_evaluated_count"]
            == 1
        )
        assert (
            result["summary"]["compliant_count"]
            == 0
        )
