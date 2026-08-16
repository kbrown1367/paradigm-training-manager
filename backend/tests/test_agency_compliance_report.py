from datetime import date

import pytest

from app import create_app
from app.compliance.agency_report import (
    evaluate_agency_compliance_report,
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


def test_report_returns_none_for_unknown_agency(app):
    import uuid

    with app.app_context():
        result = evaluate_agency_compliance_report(
            uuid.uuid4(),
            evaluation_date=date(2026, 8, 16),
        )

        assert result is None


def test_report_contains_agency_and_period(app):
    with app.app_context():
        agency = Agency(
            name="Report Test Agency"
        )
        db.session.add(agency)
        db.session.flush()

        add_peace_officer(
            agency,
            "100001",
            "JANE",
            "SMITH",
        )

        db.session.commit()

        result = evaluate_agency_compliance_report(
            agency.id,
            evaluation_date=date(2026, 8, 16),
        )

        assert (
            result["report"]["title"]
            == "Agency Compliance Report"
        )
        assert (
            result["agency"]["name"]
            == "Report Test Agency"
        )
        assert (
            result["report"]["evaluation_date"]
            == "2026-08-16"
        )
        assert (
            result["training_cycle"]["start"]
            == "2025-09-01"
        )
        assert (
            result["training_cycle"]["end"]
            == "2029-08-31"
        )
        assert (
            result["training_unit"]["number"]
            == 1
        )


def test_report_uses_dashboard_summary(app):
    with app.app_context():
        agency = Agency(
            name="Summary Report Agency"
        )
        db.session.add(agency)
        db.session.flush()

        add_peace_officer(
            agency,
            "200001",
            "JANE",
            "SMITH",
        )

        db.session.commit()

        result = evaluate_agency_compliance_report(
            agency.id,
            evaluation_date=date(2026, 8, 16),
        )

        assert (
            result["executive_summary"][
                "active_employee_count"
            ]
            == 1
        )


def test_report_lists_employee_findings(app):
    with app.app_context():
        agency = Agency(
            name="Findings Report Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = add_peace_officer(
            agency,
            "300001",
            "JANE",
            "SMITH",
        )

        db.session.add(
            OfficerAssignment(
                agency_id=agency.id,
                officer_id=officer.id,
                assignment_type="SUPERVISOR",
                effective_date=date(2023, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_agency_compliance_report(
            agency.id,
            evaluation_date=date(2026, 8, 16),
        )

        findings = result["employee_findings"]

        assert len(findings) == 1
        assert findings[0]["tcole_pid"] == "300001"
        assert (
            findings[0]["overall_status"]
            == "NONCOMPLIANT"
        )
        assert findings[0]["requirements"]


def test_report_builds_requirement_rollup(app):
    with app.app_context():
        agency = Agency(
            name="Rollup Report Agency"
        )
        db.session.add(agency)
        db.session.flush()

        add_peace_officer(
            agency,
            "400001",
            "JANE",
            "SMITH",
        )

        add_peace_officer(
            agency,
            "400002",
            "JOHN",
            "DOE",
        )

        db.session.commit()

        result = evaluate_agency_compliance_report(
            agency.id,
            evaluation_date=date(2026, 8, 16),
        )

        rollup = result["requirement_rollup"]

        assert rollup
        assert any(
            item["employee_count"] == 2
            for item in rollup
        )


def test_report_training_plan_matches_rollup(app):
    with app.app_context():
        agency = Agency(
            name="Training Plan Agency"
        )
        db.session.add(agency)
        db.session.flush()

        add_peace_officer(
            agency,
            "500001",
            "JANE",
            "SMITH",
        )

        db.session.commit()

        result = evaluate_agency_compliance_report(
            agency.id,
            evaluation_date=date(2026, 8, 16),
        )

        assert len(result["training_plan"]) == len(
            result["requirement_rollup"]
        )

        assert all(
            item["recommended_action"]
            in {
                "IMMEDIATE",
                "REVIEW",
                "SCHEDULE",
            }
            for item in result["training_plan"]
        )


def test_archived_employee_not_in_report(app):
    with app.app_context():
        agency = Agency(
            name="Archived Report Agency"
        )
        db.session.add(agency)
        db.session.flush()

        active = add_peace_officer(
            agency,
            "600001",
            "JANE",
            "SMITH",
        )

        archived = add_peace_officer(
            agency,
            "600002",
            "JOHN",
            "DOE",
        )
        archived.employment_status = "archived"

        db.session.commit()

        result = evaluate_agency_compliance_report(
            agency.id,
            evaluation_date=date(2026, 8, 16),
        )

        assert (
            result["executive_summary"][
                "active_employee_count"
            ]
            == 1
        )

        reported_pids = {
            item["tcole_pid"]
            for item in result["employee_findings"]
        }

        assert archived.tcole_pid not in reported_pids
        assert active.tcole_pid in reported_pids


def test_report_requirement_names_are_human_readable():
    from app.compliance.agency_report import (
        _normalize_requirement,
    )

    requirement = _normalize_requirement(
        {
            "type": "REQUIRED_COURSE",
            "course_number": "3189",
            "message": (
                "State and Federal Law Update (#3189) "
                "remains outstanding."
            ),
            "source_component":
                "PEACE_OFFICER",
            "normalized_status":
                "OUTSTANDING",
            "due_date":
                "2027-08-31",
        }
    )

    assert (
        requirement["display_name"]
        == "State and Federal Law Update"
    )

    assert (
        requirement["course_numbers"]
        == ["3189"]
    )


def test_cycle_requirement_uses_course_name():
    from app.compliance.agency_report import (
        _normalize_requirement,
    )

    requirement = _normalize_requirement(
        {
            "type":
                "PEACE_OFFICER_CYCLE_COURSE",
            "course_number": None,
            "accepted_courses": [
                "3843",
                "1850",
            ],
            "message": (
                "Crisis Intervention Training "
                "(#3843 or #1850) remains outstanding "
                "for the current four-year training cycle."
            ),
            "source_component":
                "PEACE_OFFICER",
            "normalized_status":
                "OUTSTANDING",
            "due_date":
                "2029-08-31",
        }
    )

    assert (
        requirement["display_name"]
        == "Crisis Intervention Training"
    )

    assert (
        requirement["course_numbers"]
        == [
            "3843",
            "1850",
        ]
    )


def test_telecommunicator_course_title_is_used():
    from app.compliance.agency_report import (
        _normalize_requirement,
    )

    requirement = _normalize_requirement(
        {
            "requirement_type":
                "REQUIRED_COURSE",
            "course_number": "786",
            "course_title":
                "Cardiac Emergency Communication",
            "message": (
                "Cardiac Emergency Communication "
                "(#786) remains outstanding."
            ),
            "source_component":
                "TELECOMMUNICATOR",
            "normalized_status":
                "OUTSTANDING",
            "due_date":
                "2027-08-31",
        }
    )

    assert (
        requirement["display_name"]
        == "Cardiac Emergency Communication"
    )

    assert (
        requirement["course_numbers"]
        == ["786"]
    )


def test_internal_requirement_types_are_named():
    from app.compliance.agency_report import (
        _normalize_requirement,
    )

    alerrt = _normalize_requirement(
        {
            "type": "ALERRT_HOURS",
            "message": (
                "16 additional approved "
                "ALERRT hours required."
            ),
            "source_component":
                "PEACE_OFFICER",
            "normalized_status":
                "OUTSTANDING",
            "due_date":
                "2027-08-31",
        }
    )

    hours = _normalize_requirement(
        {
            "type": "TOTAL_HOURS",
            "message": (
                "38.00 additional "
                "training hours required."
            ),
            "source_component":
                "PEACE_OFFICER",
            "normalized_status":
                "OUTSTANDING",
            "due_date":
                "2027-08-31",
        }
    )

    assert (
        alerrt["display_name"]
        == "ALERRT Training Hours"
    )

    assert (
        hours["display_name"]
        == "Minimum Training Hours"
    )


def test_hb33_courses_are_available_to_report():
    from app.compliance.agency_report import (
        _normalize_requirement,
    )

    requirement = _normalize_requirement(
        {
            "type":
                "HB33_SUPERVISOR_TRAINING",
            "message": (
                "HB33 Supervisor Training remains "
                "outstanding. Complete one approved "
                "course by 08/31/2027: "
                "#3366 ALERRT Active Attack Incident "
                "Management; #3608 ALERRT Incident "
                "Response and Command."
            ),
            "source_component":
                "SUPERVISOR",
            "normalized_status":
                "OUTSTANDING",
            "due_date":
                "2027-08-31",
        }
    )

    assert (
        requirement["display_name"]
        == "HB 33 Supervisor Training"
    )

    assert (
        requirement["course_numbers"]
        == [
            "3366",
            "3608",
        ]
    )


def test_proficiency_opportunities_only_include_eligible():
    from app.compliance.agency_report import (
        _build_proficiency_opportunities,
    )

    dashboard = {
        "employees": [
            {
                "id": "1",
                "tcole_pid": "111111",
                "first_name": "JANE",
                "last_name": "SMITH",
                "proficiency_advancement": {
                    "peace_officer": {
                        "status": "TERMINAL",
                        "current_certificate":
                            "Master Peace Officer",
                        "next_certificate": None,
                    },
                    "jailer": None,
                    "telecommunicator": None,
                },
            },
            {
                "id": "2",
                "tcole_pid": "222222",
                "first_name": "JOHN",
                "last_name": "DOE",
                "proficiency_advancement": {
                    "peace_officer": {
                        "status": "ELIGIBLE",
                        "current_certificate":
                            "Basic Peace Officer",
                        "next_certificate":
                            "Intermediate Peace Officer",
                        "qualifying_pathway": {
                            "type":
                                "SERVICE_TRAINING",
                        },
                    },
                    "jailer": None,
                    "telecommunicator": None,
                },
            },
        ]
    }

    result = (
        _build_proficiency_opportunities(
            dashboard
        )
    )

    assert len(result) == 1

    assert (
        result[0]["tcole_pid"]
        == "222222"
    )

    assert (
        result[0]["next_certificate"]
        == "Intermediate Peace Officer"
    )

    assert (
        result[0]["track_label"]
        == "Peace Officer"
    )
