import json
from datetime import date
from pathlib import Path

from app.compliance.training_calendar import get_unit
from app.models import Officer


RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "county_jailer_2025_2029.json"
)


def load_rule():
    with RULE_PATH.open() as file:
        return json.load(file)


def has_county_jailer_license(officer):
    return any(
        award.award_type == "License"
        and award.award_name in {
            "Jailer License",
            "County Jailer License",
        }
        for award in officer.awards
    )


def _course_completed(
    officer,
    course_number,
    start_date,
    end_date,
):
    return any(
        record.course_number == course_number
        and start_date <= record.course_date <= end_date
        for record in officer.training_records
    )


def _course_result(
    officer,
    requirement,
    start_date,
    end_date,
    due_date,
    exempt=False,
):
    completed = _course_completed(
        officer,
        requirement["course_number"],
        start_date,
        end_date,
    )

    if exempt:
        status = "EXEMPT"
        satisfaction_basis = "VERIFIED_EXEMPTION"
    elif completed:
        status = "COMPLETE"
        satisfaction_basis = "DIRECT"
    else:
        status = "OUTSTANDING"
        satisfaction_basis = None

    return {
        "course_number": requirement["course_number"],
        "name": requirement["name"],
        "completed": completed,
        "exempt": exempt,
        "status": status,
        "satisfaction_basis": satisfaction_basis,
        "due_date": due_date.isoformat(),
    }


def evaluate_county_jailer(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_rule()
    calendar = get_unit(evaluation_date)

    cycle_start = calendar["cycle_start"]
    cycle_end = calendar["cycle_end"]
    unit_start = calendar["start"]
    unit_end = calendar["end"]

    unit_course_results = [
        _course_result(
            officer,
            requirement,
            unit_start,
            unit_end,
            unit_end,
        )
        for requirement in rule["unit_requirements"]
    ]

    missing_unit = [
        course
        for course in unit_course_results
        if course["status"] == "OUTSTANDING"
    ]

    if not missing_unit:
        unit_status = "COMPLETE"
    elif evaluation_date <= unit_end:
        unit_status = "OUTSTANDING"
    else:
        unit_status = "OVERDUE"

    exemption = bool(
        officer
        .verified_jailer_cultural_diversity_exemption
    )

    cycle_course_results = [
        _course_result(
            officer,
            requirement,
            cycle_start,
            cycle_end,
            cycle_end,
            exempt=(
                exemption
                and requirement.get(
                    "exemption_fact"
                )
                == (
                    "verified_jailer_"
                    "cultural_diversity_exemption"
                )
            ),
        )
        for requirement in rule["cycle_requirements"]
    ]

    missing_cycle = [
        course
        for course in cycle_course_results
        if course["status"] == "OUTSTANDING"
    ]

    if not missing_cycle:
        cycle_status = "COMPLETE"
    elif evaluation_date <= cycle_end:
        cycle_status = "OUTSTANDING"
    else:
        cycle_status = "OVERDUE"

    requirements = []

    for course in unit_course_results:
        if course["status"] == "OUTSTANDING":
            requirements.append(
                {
                    "type": "REQUIRED_COURSE",
                    "scope": "UNIT",
                    "status": (
                        "FAILED"
                        if evaluation_date > unit_end
                        else "OUTSTANDING"
                    ),
                    "course_number":
                        course["course_number"],
                    "due_date":
                        course["due_date"],
                    "message": (
                        f"{course['name']} "
                        f"(#{course['course_number']}) "
                        "remains outstanding."
                    ),
                }
            )

    for course in cycle_course_results:
        if course["status"] == "OUTSTANDING":
            requirements.append(
                {
                    "type": "REQUIRED_COURSE",
                    "scope": "CYCLE",
                    "status": (
                        "FAILED"
                        if evaluation_date > cycle_end
                        else "OUTSTANDING"
                    ),
                    "course_number":
                        course["course_number"],
                    "due_date":
                        course["due_date"],
                    "message": (
                        f"{course['name']} "
                        f"(#{course['course_number']}) "
                        "remains outstanding."
                    ),
                }
            )

    if (
        unit_status == "OVERDUE"
        or cycle_status == "OVERDUE"
    ):
        overall_status = "OVERDUE"
    elif requirements:
        overall_status = "OUTSTANDING"
    else:
        overall_status = "COMPLETE"

    return {
        "officer_id": str(officer.id),
        "tcole_pid": officer.tcole_pid,
        "license_type": "County Jailer",
        "license_status": "UNVERIFIED",
        "applicability_status": "PROVISIONAL",
        "applicability_basis": (
            "County Jailer License award present; "
            "current active license status has not "
            "yet been independently verified."
        ),
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["version"],
        "evaluation_date":
            evaluation_date.isoformat(),
        "cycle_start": cycle_start.isoformat(),
        "cycle_end": cycle_end.isoformat(),
        "cycle_number":
            calendar["cycle_number"],
        "unit_number":
            calendar["unit_number"],
        "unit_start": unit_start.isoformat(),
        "unit_end": unit_end.isoformat(),
        "due_date": unit_end.isoformat(),
        "unit_status": unit_status,
        "cycle_status": cycle_status,
        "unit_results": [
            {
                "unit_number":
                    calendar["unit_number"],
                "unit_start":
                    unit_start.isoformat(),
                "unit_end":
                    unit_end.isoformat(),
                "due_date":
                    unit_end.isoformat(),
                "status": unit_status,
                "required_courses":
                    unit_course_results,
            }
        ],
        "cultural_diversity_exemption":
            exemption,
        "cycle_required_courses":
            cycle_course_results,
        "status": overall_status,
        "requirements": requirements,
        "deficiencies": requirements,
    }

def evaluate_agency_county_jailers(
    agency_id,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    officers = (
        Officer.query
        .filter_by(agency_id=agency_id)
        .order_by(
            Officer.last_name,
            Officer.first_name,
        )
        .all()
    )

    results = [
        evaluate_county_jailer(
            officer,
            evaluation_date=evaluation_date,
        )
        for officer in officers
        if has_county_jailer_license(officer)
    ]

    return {
        "rule_set_id": "JAILER-COMPLIANCE",
        "evaluation_date":
            evaluation_date.isoformat(),
        "officer_count": len(results),
        "complete_count": sum(
            result["status"] == "COMPLETE"
            for result in results
        ),
        "outstanding_count": sum(
            result["status"] == "OUTSTANDING"
            for result in results
        ),
        "overdue_count": sum(
            result["status"] == "OVERDUE"
            for result in results
        ),
        "officers": results,
    }
