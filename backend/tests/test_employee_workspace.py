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


def test_workspace_contains_peace_officer_proficiency(app):
    with app.app_context():
        _, officer = make_officer()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        tracks = result["proficiency_advancement"]

        assert set(tracks) == {
            "peace_officer",
            "jailer",
            "telecommunicator",
        }

        advancement = tracks["peace_officer"]

        assert advancement is not None
        assert (
            advancement["current_certificate"]
            == "Intermediate Peace Officer"
        )
        assert (
            advancement["next_certificate"]
            == "Advanced Peace Officer"
        )
        assert "service_years" in advancement
        assert "training_hours" in advancement
        assert "course_requirements" in advancement

        assert tracks["jailer"] is None


def test_workspace_contains_jailer_proficiency(app):
    with app.app_context():
        agency = Agency(
            name="Jailer Test Agency",
            email_domain="example.gov",
            email_pattern="FIRST_INITIAL_LAST",
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="654321",
            first_name="John",
            last_name="Doe",
            jailer_service_start_date=date(
                2020,
                1,
                30,
            ),
        )
        db.session.add(officer)
        db.session.flush()

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Jailer License",
                award_date=date(2020, 1, 30),
            )
        )

        db.session.commit()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        tracks = result["proficiency_advancement"]

        assert tracks["peace_officer"] is None
        assert tracks["jailer"] is not None
        assert (
            tracks["jailer"]["certificate"]
            == "Basic Jailer"
        )
        assert tracks["jailer"][
            "has_jailer_license"
        ] is True


def test_workspace_preserves_dual_license_proficiency(app):
    with app.app_context():
        agency, officer = make_officer()

        officer.jailer_service_start_date = date(
            2020,
            1,
            30,
        )

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="County Jailer License",
                award_date=date(2020, 1, 30),
            )
        )

        db.session.commit()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        tracks = result["proficiency_advancement"]

        assert tracks["peace_officer"] is not None
        assert tracks["jailer"] is not None

        assert (
            tracks["peace_officer"][
                "current_certificate"
            ]
            == "Intermediate Peace Officer"
        )

        assert (
            tracks["jailer"]["certificate"]
            == "Basic Jailer"
        )


def test_workspace_has_no_proficiency_tracks_without_license(
    app,
):
    with app.app_context():
        agency = Agency(
            name="No License Agency",
            email_domain="example.gov",
            email_pattern="FIRST_INITIAL_LAST",
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="654321",
            first_name="John",
            last_name="Doe",
        )
        db.session.add(officer)
        db.session.commit()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        tracks = result["proficiency_advancement"]

        assert tracks == {
            "peace_officer": None,
            "jailer": None,
            "telecommunicator": None,
        }


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


def test_workspace_advances_basic_jailer_to_intermediate(
    app,
):
    with app.app_context():
        agency = Agency(
            name="Jailer Progression Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="700001",
            first_name="John",
            last_name="Basic",
            jailer_service_start_date=date(
                2020,
                1,
                1,
            ),
        )
        db.session.add(officer)
        db.session.flush()

        db.session.add_all(
            [
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="License",
                    award_name="Jailer License",
                    award_date=date(2020, 1, 1),
                ),
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="Certificate",
                    award_name="Basic Jailer",
                    award_date=date(2021, 1, 1),
                ),
            ]
        )

        db.session.commit()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        advancement = result[
            "proficiency_advancement"
        ]["jailer"]

        assert advancement[
            "current_certificate"
        ] == "Basic Jailer"

        assert advancement[
            "next_certificate"
        ] == "Intermediate Jailer"

        assert advancement[
            "certificate"
        ] == "Intermediate Jailer"


def test_workspace_advances_intermediate_jailer_to_advanced(
    app,
):
    with app.app_context():
        agency = Agency(
            name="Jailer Progression Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="700002",
            first_name="John",
            last_name="Intermediate",
            jailer_service_start_date=date(
                2015,
                1,
                1,
            ),
        )
        db.session.add(officer)
        db.session.flush()

        db.session.add_all(
            [
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="License",
                    award_name="Jailer License",
                    award_date=date(2015, 1, 1),
                ),
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="Certificate",
                    award_name="Basic Jailer",
                    award_date=date(2016, 1, 1),
                ),
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="Certificate",
                    award_name=(
                        "Intermediate Jailer Proficiency"
                    ),
                    award_date=date(2020, 1, 1),
                ),
            ]
        )

        db.session.commit()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        advancement = result[
            "proficiency_advancement"
        ]["jailer"]

        assert advancement[
            "current_certificate"
        ] == "Intermediate Jailer"

        assert advancement[
            "next_certificate"
        ] == "Advanced Jailer"

        assert advancement[
            "certificate"
        ] == "Advanced Jailer"


def test_workspace_advances_advanced_jailer_to_master(
    app,
):
    with app.app_context():
        agency = Agency(
            name="Jailer Progression Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="700003",
            first_name="John",
            last_name="Advanced",
            jailer_service_start_date=date(
                2005,
                1,
                1,
            ),
        )
        db.session.add(officer)
        db.session.flush()

        db.session.add_all(
            [
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="License",
                    award_name="Jailer License",
                    award_date=date(2005, 1, 1),
                ),
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="Certificate",
                    award_name="Basic Jailer",
                    award_date=date(2006, 1, 1),
                ),
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="Certificate",
                    award_name=(
                        "Intermediate Jailer Proficiency"
                    ),
                    award_date=date(2010, 1, 1),
                ),
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="Certificate",
                    award_name=(
                        "Advanced Jailer Proficiency"
                    ),
                    award_date=date(2015, 1, 1),
                ),
            ]
        )

        db.session.commit()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        advancement = result[
            "proficiency_advancement"
        ]["jailer"]

        assert advancement[
            "current_certificate"
        ] == "Advanced Jailer"

        assert advancement[
            "next_certificate"
        ] == "Master Jailer"

        assert advancement[
            "certificate"
        ] == "Master Jailer"


def test_workspace_marks_master_jailer_as_highest(
    app,
):
    with app.app_context():
        agency = Agency(
            name="Jailer Progression Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="700004",
            first_name="John",
            last_name="Master",
            jailer_service_start_date=date(
                2000,
                1,
                1,
            ),
        )
        db.session.add(officer)
        db.session.flush()

        db.session.add_all(
            [
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="License",
                    award_name="Jailer License",
                    award_date=date(2000, 1, 1),
                ),
                OfficerAward(
                    agency_id=agency.id,
                    officer_id=officer.id,
                    award_type="Certificate",
                    award_name=(
                        "Master Jailer Proficiency"
                    ),
                    award_date=date(2020, 1, 1),
                ),
            ]
        )

        db.session.commit()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        advancement = result[
            "proficiency_advancement"
        ]["jailer"]

        assert advancement[
            "current_certificate"
        ] == "Master Jailer"

        assert advancement[
            "next_certificate"
        ] is None

        assert advancement[
            "status"
        ] == "HIGHEST_CERTIFICATE"



def test_workspace_contains_telecommunicator_proficiency(
    app,
):
    with app.app_context():
        agency = Agency(
            name="Test Communications Center"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="555555",
            first_name="Jane",
            last_name="Dispatcher",
            telecommunicator_service_start_date=
                date(2020, 1, 1),
        )

        db.session.add(officer)
        db.session.flush()

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Telecommunicator License",
                award_date=date(2020, 1, 1),
            )
        )

        db.session.commit()

        result = build_employee_workspace(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        advancement = result[
            "proficiency_advancement"
        ]["telecommunicator"]

        assert advancement is not None
        assert (
            advancement["next_certificate"]
            == "Basic Telecommunicator"
        )
