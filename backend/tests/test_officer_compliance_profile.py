from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.officer_profile import (
    evaluate_officer_compliance_profile,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAssignment,
    OfficerAward,
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


def make_peace_officer():
    agency = Agency(
        name="Test Police Department"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="JANE",
        middle_name="A",
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

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="Certificate",
            award_name="Master Peace Officer",
            award_date=date(2024, 1, 1),
        )
    )

    db.session.commit()

    return agency, officer


def add_course(
    agency,
    officer,
    course_number,
    course_date,
    hours=8,
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=course_number,
            course_title=f"Course {course_number}",
            course_date=course_date,
            credited_hours=Decimal(str(hours)),
            hours_source="TCOLE_CYCLE_REPORT",
        )
    )


def test_profile_returns_officer_identity_and_certificate(app):
    with app.app_context():
        _, officer = make_peace_officer()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["officer"]["tcole_pid"] == "123456"
        assert (
            result["officer"]["highest_certificate"]
            == "Master Peace Officer"
        )
        assert (
            result["officer"]["certificate_level"]
            == "MASTER"
        )
        assert (
            result["officer"][
                "highest_certificate_date"
            ]
            == "2024-01-01"
        )


def test_profile_includes_all_four_components(app):
    with app.app_context():
        _, officer = make_peace_officer()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert set(result["components"]) == {
            "PEACE_OFFICER",
            "COUNTY_JAILER",
            "TELECOMMUNICATOR",
            "POLICE_CHIEF",
            "SUPERVISOR",
            "PUBLIC_INFORMATION_OFFICER",
        }

        assert (
            result["components"]["PEACE_OFFICER"][
                "applicable"
            ]
            is True
        )

        assert (
            result["components"]["POLICE_CHIEF"][
                "applicable"
            ]
            is False
        )


def test_outstanding_peace_officer_requirement_makes_profile_due(app):
    with app.app_context():
        _, officer = make_peace_officer()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["overall_status"] == "DUE"
        assert result["outstanding_count"] > 0
        assert result["overdue_count"] == 0


def test_overdue_supervisor_requirement_makes_profile_noncompliant(app):
    with app.app_context():
        agency, officer = make_peace_officer()

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2023, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert (
            result["overall_status"]
            == "NONCOMPLIANT"
        )

        assert result["overdue_count"] >= 1

        supervisor = result["components"]["SUPERVISOR"]

        assert supervisor["status"] == "NONCOMPLIANT"


def test_review_flag_propagates_from_supervisor_evidence(app):
    with app.app_context():
        agency, officer = make_peace_officer()

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2023, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["review_required"] is True
        assert result["pending_review_count"] == 0
        assert result["agency_review_count"] >= 1


def test_next_due_date_uses_earliest_future_requirement(app):
    with app.app_context():
        agency, officer = make_peace_officer()

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2026, 1, 1),
            )
        )

        add_course(
            agency,
            officer,
            "3737",
            date(2026, 2, 1),
        )

        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["next_due_date"] is not None
        assert (
            result["next_due_date"]
            <= "2027-08-31"
        )


def test_nonapplicable_assignment_components_do_not_drive_status(app):
    with app.app_context():
        _, officer = make_peace_officer()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert (
            result["components"]["POLICE_CHIEF"][
                "status"
            ]
            == "NOT_APPLICABLE"
        )
        assert (
            result["components"]["SUPERVISOR"][
                "status"
            ]
            == "NOT_APPLICABLE"
        )
        assert (
            result["components"][
                "PUBLIC_INFORMATION_OFFICER"
            ]["status"]
            == "NOT_APPLICABLE"
        )


def test_agency_review_does_not_become_pending_review(app):
    with app.app_context():
        agency = Agency(
            name="Agency Review Test"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="777777",
            first_name="CHRISTOPHER",
            last_name="THAI",
        )
        db.session.add(officer)
        db.session.flush()

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2023, 10, 23),
            )
        )

        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["overall_status"] == "NONCOMPLIANT"
        assert result["review_required"] is True
        assert result["pending_review_count"] == 0
        assert result["agency_review_count"] == 2
        assert result["pending_review_requirements"] == []
        assert (
            len(result["agency_review_requirements"])
            == 2
        )

        statuses = {
            item["normalized_status"]
            for item in result[
                "agency_review_requirements"
            ]
        }

        assert statuses == {
            "OVERDUE",
            "OUTSTANDING",
        }


def test_non_peace_officer_does_not_receive_peace_officer_requirements(app):
    with app.app_context():
        agency = Agency(
            name="Non Peace Officer Test"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="888888",
            first_name="ALEX",
            last_name="DISPATCHER",
        )
        db.session.add(officer)
        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        component = result["components"][
            "PEACE_OFFICER"
        ]

        assert component["applicable"] is False
        assert (
            component["status"]
            == "NOT_APPLICABLE"
        )
        assert component["requirements"] == []


def test_future_pio_requirement_makes_profile_due(app):
    with app.app_context():
        agency, officer = make_peace_officer()

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

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        component = result["components"][
            "PUBLIC_INFORMATION_OFFICER"
        ]

        assert (
            component["raw_status"]
            == "FUTURE_REQUIREMENT"
        )
        assert component["status"] == "DUE"
        assert result["overall_status"] == "DUE"
        assert (
            result["pending_review_count"]
            == 0
        )


def test_employee_with_no_applicable_engine_is_not_evaluated(app):
    with app.app_context():
        agency = Agency(
            name="Coverage Test Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="999001",
            first_name="ALEX",
            last_name="DISPATCHER",
        )
        db.session.add(officer)
        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert (
            result["overall_status"]
            == "NOT_EVALUATED"
        )

        coverage = result["evaluation_coverage"]

        assert (
            coverage["coverage_status"]
            == "NOT_EVALUATED"
        )
        assert (
            coverage["evaluated_component_count"]
            == 0
        )
        assert (
            coverage["applicable_components"]
            == []
        )


def test_county_jailer_component_is_not_applicable_without_license(
    app,
):
    with app.app_context():
        agency, officer = make_peace_officer()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        component = result["components"]["COUNTY_JAILER"]

        assert component["applicable"] is False
        assert component["status"] == "NOT_APPLICABLE"

        assert (
            "COUNTY_JAILER"
            not in result[
                "evaluation_coverage"
            ]["applicable_components"]
        )


def test_county_jailer_component_is_evaluated_with_license(
    app,
):
    with app.app_context():
        agency, officer = make_peace_officer()

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Jailer License",
                award_date=date(2025, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        component = result["components"]["COUNTY_JAILER"]

        assert component["applicable"] is True
        assert component["status"] == "DUE"
        assert component["raw_status"] == "OUTSTANDING"

        assert (
            "COUNTY_JAILER"
            in result[
                "evaluation_coverage"
            ]["applicable_components"]
        )

        course_numbers = {
            item["course_number"]
            for item in component["requirements"]
        }

        assert course_numbers == {"4902", "3939"}


def test_dual_license_employee_evaluates_both_license_components(
    app,
):
    with app.app_context():
        agency, officer = make_peace_officer()

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Jailer License",
                award_date=date(2025, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        applicable = set(
            result[
                "evaluation_coverage"
            ]["applicable_components"]
        )

        assert "PEACE_OFFICER" in applicable
        assert "COUNTY_JAILER" in applicable

        assert (
            result["components"]["PEACE_OFFICER"][
                "applicable"
            ]
            is True
        )

        assert (
            result["components"]["COUNTY_JAILER"][
                "applicable"
            ]
            is True
        )


def test_jailer_deficiencies_roll_into_unified_requirements(
    app,
):
    with app.app_context():
        agency, officer = make_peace_officer()

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Jailer License",
                award_date=date(2025, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        jailer_requirements = [
            item
            for item in result["requirements"]
            if item["source_component"]
            == "COUNTY_JAILER"
        ]

        course_numbers = {
            item["course_number"]
            for item in jailer_requirements
        }

        assert course_numbers == {"4902", "3939"}
        assert result["overall_status"] == "DUE"


def test_peace_officer_cycle_requirement_drives_profile_due(app):
    with app.app_context():
        agency = Agency(
            name="Cycle Requirement Test"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="765432",
            first_name="CYCLE",
            last_name="OFFICER",
        )
        db.session.add(officer)
        db.session.flush()

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Peace Officer License",
                award_date=date(2025, 1, 1),
            )
        )

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Basic Peace Officer",
                award_date=date(2025, 1, 1),
            )
        )

        add_course(
            agency,
            officer,
            "3189",
            date(2026, 1, 1),
            8,
        )
        add_course(
            agency,
            officer,
            "7006",
            date(2026, 1, 2),
            8,
        )
        add_course(
            agency,
            officer,
            "3369",
            date(2026, 1, 3),
            16,
        )
        add_course(
            agency,
            officer,
            "3311",
            date(2026, 1, 4),
            16,
        )

        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        peace = result["components"][
            "PEACE_OFFICER"
        ]

        assert peace["result"]["unit_status"] == "COMPLETE"
        assert (
            peace["result"]["cycle_status"]
            == "OUTSTANDING"
        )
        assert peace["status"] == "DUE"
        assert result["overall_status"] == "DUE"

        cycle_requirements = [
            item
            for item in result[
                "outstanding_requirements"
            ]
            if item.get("type")
            == "PEACE_OFFICER_CYCLE_COURSE"
        ]

        assert len(cycle_requirements) == 4


def test_police_chief_profile_uses_3740_equivalency_and_alerrt_credit(
    app,
):
    with app.app_context():
        agency, officer = make_peace_officer()

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type="POLICE_CHIEF",
                effective_date=date(2020, 1, 1),
            )
        )

        # Initial chief training.
        add_course(
            agency,
            officer,
            "3780",
            date(2020, 6, 1),
            40,
        )
        add_course(
            agency,
            officer,
            "3740",
            date(2021, 6, 1),
            40,
        )

        # Current-unit Chief Leadership Series.
        # This satisfies #3189 and contributes
        # 8 embedded ALERRT hours.
        add_course(
            agency,
            officer,
            "3740",
            date(2026, 1, 1),
            40,
        )

        # Additional approved ALERRT credit.
        add_course(
            agency,
            officer,
            "3312",
            date(2026, 2, 1),
            2,
        )

        db.session.commit()

        result = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        chief = result["components"]["POLICE_CHIEF"]
        peace = result["components"]["PEACE_OFFICER"]

        assert chief["applicable"] is True
        assert peace["applicable"] is True

        assert (
            chief["result"]["current_unit_3740_completed"]
            is True
        )

        assert (
            chief["result"][
                "state_federal_law_update_satisfied_by_3740"
            ]
            is True
        )

        peace_result = peace["result"]

        assert peace_result["alerrt_hours"] == 10.0
        assert (
            peace_result["remaining_alerrt_hours"]
            == 6.0
        )

        course_3189 = next(
            item
            for item in peace_result["required_courses"]
            if item["course_number"] == "3189"
        )

        assert course_3189["completed"] is True
        assert course_3189["status"] == "COMPLETE"
        assert (
            course_3189["satisfaction_basis"]
            == "EQUIVALENCY"
        )

        # The unified employee profile must not
        # reintroduce #3189 as an outstanding item.
        assert not any(
            item.get("course_number") == "3189"
            and item.get("source_component")
            == "PEACE_OFFICER"
            for item in result["requirements"]
        )

        alerrt_requirement = next(
            item
            for item in result[
                "outstanding_requirements"
            ]
            if (
                item.get("source_component")
                == "PEACE_OFFICER"
                and item.get("type")
                == "ALERRT_HOURS"
            )
        )

        assert (
            alerrt_requirement["message"]
            == (
                "6.00 additional approved "
                "ALERRT hours required."
            )
        )
