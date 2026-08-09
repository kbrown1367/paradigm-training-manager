from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAssignment,
    OfficerAward,
    TrainingRecord,
)
from app.services.employee_workspace import (
    build_employee_workspace,
    get_employee_workspace,
)


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


def make_officer():
    agency = Agency(
        name="Test Police Department",
        email_domain="example.gov",
        email_pattern="FIRST_INITIAL_LAST",
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="Jane",
        middle_name="A",
        last_name="Smith",
    )
    db.session.add(officer)
    db.session.flush()

    db.session.add_all(
        [
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Peace Officer License",
                award_date=date(2020, 1, 1),
            ),
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name=(
                    "Intermediate Peace Officer"
                ),
                award_date=date(2023, 1, 1),
            ),
            TrainingRecord(
                agency_id=agency.id,
                officer_id=officer.id,
                course_number="9999",
                course_title="Current Unit Course",
                course_date=date(2026, 1, 15),
                credited_hours=Decimal("8.00"),
                hours_source="TCOLE",
                source="TCOLE",
            ),
            TrainingRecord(
                agency_id=agency.id,
                officer_id=officer.id,
                course_number="8888",
                course_title="Prior Unit Course",
                course_date=date(2024, 1, 15),
                credited_hours=Decimal("12.00"),
                hours_source="TCOLE",
                source="TCOLE",
            ),
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2025, 10, 1),
            ),
        ]
    )

    db.session.commit()

    return agency, officer


def test_workspace_contains_identity_and_email(app):
    with app.app_context():
        _, officer = make_officer()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["officer"]["tcole_pid"] == (
            "123456"
        )
        assert result["officer"][
            "highest_certificate"
        ] == "Intermediate Peace Officer"
        assert result["resolved_email"]["email"] == (
            "jsmith@example.gov"
        )


def test_workspace_contains_training_unit(app):
    with app.app_context():
        _, officer = make_officer()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["training_unit"][
            "unit_number"
        ] == 1
        assert result["training_unit"][
            "unit_start"
        ] == "2025-09-01"
        assert result["training_unit"][
            "unit_end"
        ] == "2027-08-31"


def test_workspace_only_lists_current_unit_training(
    app,
):
    with app.app_context():
        _, officer = make_officer()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert len(
            result["current_unit_training"]
        ) == 1

        record = result[
            "current_unit_training"
        ][0]

        assert record["course_number"] == "9999"
        assert record["credited_hours"] == 8.0


def test_workspace_calculates_current_unit_hours(app):
    with app.app_context():
        _, officer = make_officer()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["training_summary"][
            "current_unit_hours"
        ] == 8.0
        assert result["training_summary"][
            "training_record_count"
        ] == 1


def test_workspace_contains_assignments(app):
    with app.app_context():
        _, officer = make_officer()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert len(result["assignments"]) == 1
        assert result["assignments"][0][
            "assignment_type"
        ] == "SUPERVISOR"
        assert result["assignments"][0][
            "active"
        ] is True


def test_workspace_contains_compliance_details(app):
    with app.app_context():
        _, officer = make_officer()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert "overall_status" in result
        assert "requirements" in result
        assert "outstanding_requirements" in result
        assert "overdue_requirements" in result
        assert "components" in result


def test_workspace_reserves_proficiency_section(app):
    with app.app_context():
        _, officer = make_officer()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        advancement = result[
            "proficiency_advancement"
        ]

        assert advancement["status"] == (
            "NOT_YET_IMPLEMENTED"
        )
        assert advancement[
            "current_certificate"
        ] == "Intermediate Peace Officer"


def test_workspace_lookup_is_tenant_scoped(app):
    with app.app_context():
        agency, officer = make_officer()

        other_agency = Agency(
            name="Other Department"
        )
        db.session.add(other_agency)
        db.session.commit()

        assert get_employee_workspace(
            agency.id,
            officer.id,
            evaluation_date=date(2026, 8, 9),
        ) is not None

        assert get_employee_workspace(
            other_agency.id,
            officer.id,
            evaluation_date=date(2026, 8, 9),
        ) is None
