import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.compliance.credentials import (
    get_highest_peace_officer_certificate,
)
from app.compliance.training_calendar import get_unit
from app.models import Officer


RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "peace_officer_unit_2025_2027.json"
)


def load_rule():
    with RULE_PATH.open() as file:
        return json.load(file)


def has_peace_officer_license(officer):
    return any(
        award.award_type == "License"
        and award.award_name == "Peace Officer License"
        for award in officer.awards
    )


def evaluate_peace_officer_unit(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_rule()

    unit = get_unit(evaluation_date)
    unit_start = unit["start"]
    unit_end = unit["end"]

    credential = get_highest_peace_officer_certificate(
        officer
    )

    training = [
        record
        for record in officer.training_records
        if unit_start <= record.course_date <= unit_end
    ]

    total_hours = sum(
        (
            Decimal(record.credited_hours)
            for record in training
            if record.credited_hours is not None
        ),
        Decimal("0"),
    )

    completed_course_numbers = {
        record.course_number
        for record in training
    }

    required_course_results = []

    for required in rule["required_courses"]:
        completed = (
            required["course_number"]
            in completed_course_numbers
        )

        required_course_results.append(
            {
                "course_number": required["course_number"],
                "name": required["name"],
                "completed": completed,
                "status": (
                    "SATISFIED"
                    if completed
                    else "OUTSTANDING"
                ),
            }
        )

    approved_alerrt = set(
        rule["alerrt"]["approved_courses"]
    )

    alerrt_training = [
        record
        for record in training
        if record.course_number in approved_alerrt
    ]

    alerrt_hours = sum(
        (
            Decimal(record.credited_hours)
            for record in alerrt_training
            if record.credited_hours is not None
        ),
        Decimal("0"),
    )

    historical_level_one_courses = set(
        rule["alerrt"]["level_one_historical_courses"]
    )

    has_prior_level_one = any(
        record.course_number
        in historical_level_one_courses
        and record.course_date < unit_start
        for record in officer.training_records
    )

    current_level_one_course = rule[
        "alerrt"
    ]["current_level_one_course"]

    has_current_level_one = any(
        record.course_number == current_level_one_course
        for record in training
    )

    level_one_satisfied = (
        has_prior_level_one
        or has_current_level_one
    )

    minimum_hours = Decimal(
        str(rule["minimum_total_hours"])
    )

    required_alerrt_hours = Decimal(
        str(rule["alerrt"]["minimum_hours"])
    )

    remaining_total_hours = max(
        Decimal("0"),
        minimum_hours - total_hours,
    )

    remaining_alerrt_hours = max(
        Decimal("0"),
        required_alerrt_hours - alerrt_hours,
    )

    requirements = []

    if remaining_total_hours > 0:
        requirements.append(
            {
                "type": "TOTAL_HOURS",
                "status": "OUTSTANDING",
                "due_date": unit_end.isoformat(),
                "message": (
                    f"{remaining_total_hours} additional "
                    "training hours required."
                ),
            }
        )

    for course in required_course_results:
        if not course["completed"]:
            requirements.append(
                {
                    "type": "REQUIRED_COURSE",
                    "status": "OUTSTANDING",
                    "course_number": course[
                        "course_number"
                    ],
                    "due_date": unit_end.isoformat(),
                    "message": (
                        f"{course['name']} "
                        f"(#{course['course_number']}) "
                        "remains outstanding."
                    ),
                }
            )

    if remaining_alerrt_hours > 0:
        requirements.append(
            {
                "type": "ALERRT_HOURS",
                "status": "OUTSTANDING",
                "due_date": unit_end.isoformat(),
                "message": (
                    f"{remaining_alerrt_hours} additional "
                    "approved ALERRT hours required."
                ),
            }
        )

    if not level_one_satisfied:
        requirements.append(
            {
                "type": "ALERRT_LEVEL_ONE",
                "status": "OUTSTANDING",
                "course_number": current_level_one_course,
                "due_date": unit_end.isoformat(),
                "message": (
                    "ALERRT Level I (#3311) remains "
                    "outstanding because no qualifying prior "
                    "Level I completion was found."
                ),
            }
        )

    if not requirements:
        unit_status = "COMPLETE"
    elif evaluation_date <= unit_end:
        unit_status = "OUTSTANDING"
    else:
        unit_status = "OVERDUE"

    requirement_status = (
        "SATISFIED"
        if unit_status == "COMPLETE"
        else (
            "OUTSTANDING"
            if unit_status == "OUTSTANDING"
            else "FAILED"
        )
    )

    if unit_status == "OVERDUE":
        for requirement in requirements:
            requirement["status"] = "FAILED"

    return {
        "officer_id": str(officer.id),
        "tcole_pid": officer.tcole_pid,
        "name": " ".join(
            part
            for part in [
                officer.first_name,
                officer.middle_name,
                officer.last_name,
            ]
            if part
        ),
        "license_type": "Peace Officer",
        "license_status": "UNVERIFIED",
        "applicability_status": "PROVISIONAL",
        "applicability_basis": (
            "Peace Officer License award present; "
            "current active license status has not "
            "yet been independently verified."
        ),
        "highest_certificate": credential[
            "highest_certificate"
        ],
        "certificate_level": credential[
            "certificate_level"
        ],
        "highest_certificate_date": credential[
            "highest_certificate_date"
        ],
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["version"],
        "evaluation_date": evaluation_date.isoformat(),
        "cycle_start": unit["cycle_start"].isoformat(),
        "cycle_end": unit["cycle_end"].isoformat(),
        "cycle_number": unit["cycle_number"],
        "unit_number": unit["unit_number"],
        "unit_start": unit_start.isoformat(),
        "unit_end": unit_end.isoformat(),
        "due_date": unit_end.isoformat(),
        "unit_status": unit_status,
        "requirement_status": requirement_status,
        "total_hours": float(total_hours),
        "minimum_total_hours": float(minimum_hours),
        "remaining_total_hours": float(
            remaining_total_hours
        ),
        "required_courses": required_course_results,
        "alerrt_hours": float(alerrt_hours),
        "required_alerrt_hours": float(
            required_alerrt_hours
        ),
        "remaining_alerrt_hours": float(
            remaining_alerrt_hours
        ),
        "alerrt_level_one_satisfied": (
            level_one_satisfied
        ),
        "prior_level_one_found": has_prior_level_one,
        "current_level_one_found": has_current_level_one,
        "requirements": requirements,
        "deficiencies": requirements,
    }


def evaluate_agency_peace_officers(
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
        evaluate_peace_officer_unit(
            officer,
            evaluation_date=evaluation_date,
        )
        for officer in officers
        if has_peace_officer_license(officer)
    ]

    complete_count = sum(
        result["unit_status"] == "COMPLETE"
        for result in results
    )

    outstanding_count = sum(
        result["unit_status"] == "OUTSTANDING"
        for result in results
    )

    overdue_count = sum(
        result["unit_status"] == "OVERDUE"
        for result in results
    )

    unit = get_unit(evaluation_date)

    return {
        "rule_set_id": "PO-UNIT",
        "evaluation_date": evaluation_date.isoformat(),
        "cycle_start": unit["cycle_start"].isoformat(),
        "cycle_end": unit["cycle_end"].isoformat(),
        "cycle_number": unit["cycle_number"],
        "unit_number": unit["unit_number"],
        "unit_start": unit["start"].isoformat(),
        "unit_end": unit["end"].isoformat(),
        "due_date": unit["end"].isoformat(),
        "applicability_status": "PROVISIONAL",
        "officer_count": len(results),
        "complete_count": complete_count,
        "outstanding_count": outstanding_count,
        "overdue_count": overdue_count,
        "officers": results,
    }
