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


CERTIFICATE_LEVEL_RANK = {
    None: 0,
    "NONE": 0,
    "BASIC": 1,
    "INTERMEDIATE": 2,
    "ADVANCED": 3,
    "MASTER": 4,
}


def _evaluate_below_intermediate_cycle(
    officer,
    rule,
    unit,
    credential,
    evaluation_date,
):
    cycle_rule = rule.get(
        "below_intermediate_cycle"
    )

    if not cycle_rule:
        return {
            "applicable": False,
            "status": "NOT_APPLICABLE",
            "required_courses": [],
            "requirements": [],
        }

    certificate_level = credential.get(
        "certificate_level"
    )

    intermediate_rank = CERTIFICATE_LEVEL_RANK[
        "INTERMEDIATE"
    ]

    certificate_rank = CERTIFICATE_LEVEL_RANK.get(
        certificate_level,
        0,
    )

    applicable = (
        certificate_rank < intermediate_rank
    )

    cycle_start = unit["cycle_start"]
    cycle_end = unit["cycle_end"]

    if not applicable:
        return {
            "applicable": False,
            "status": "NOT_APPLICABLE",
            "cycle_start": cycle_start.isoformat(),
            "cycle_end": cycle_end.isoformat(),
            "required_courses": [],
            "requirements": [],
        }

    cycle_training = [
        record
        for record in officer.training_records
        if (
            record.course_date is not None
            and cycle_start
            <= record.course_date
            <= cycle_end
        )
    ]

    completed_course_numbers = {
        record.course_number
        for record in cycle_training
    }

    required_course_results = []
    requirements = []

    for required in cycle_rule[
        "required_courses"
    ]:
        accepted_courses = [
            str(course_number)
            for course_number in required[
                "accepted_courses"
            ]
        ]

        completed_courses = sorted(
            set(accepted_courses)
            & completed_course_numbers
        )

        completed = bool(completed_courses)

        required_course_results.append(
            {
                "id": required["id"],
                "name": required["name"],
                "accepted_courses": accepted_courses,
                "completed": completed,
                "completed_courses": completed_courses,
                "status": (
                    "COMPLETE"
                    if completed
                    else "OUTSTANDING"
                ),
            }
        )

        if completed:
            continue

        accepted_display = " or ".join(
            f"#{course_number}"
            for course_number in accepted_courses
        )

        requirements.append(
            {
                "type":
                    "PEACE_OFFICER_CYCLE_COURSE",
                "status": "OUTSTANDING",
                "course_number": (
                    accepted_courses[0]
                    if len(accepted_courses) == 1
                    else None
                ),
                "accepted_courses":
                    accepted_courses,
                "due_date":
                    cycle_end.isoformat(),
                "message": (
                    f"{required['name']} "
                    f"({accepted_display}) remains "
                    "outstanding for the current "
                    "four-year training cycle. "
                    "This requirement applies because "
                    "the officer does not currently hold "
                    "an Intermediate Peace Officer "
                    "Certificate or higher."
                ),
            }
        )

    if not requirements:
        cycle_status = "COMPLETE"
    elif evaluation_date <= cycle_end:
        cycle_status = "OUTSTANDING"
    else:
        cycle_status = "OVERDUE"

    if cycle_status == "OVERDUE":
        for requirement in requirements:
            requirement["status"] = "FAILED"

    return {
        "applicable": True,
        "status": cycle_status,
        "cycle_start": cycle_start.isoformat(),
        "cycle_end": cycle_end.isoformat(),
        "required_courses":
            required_course_results,
        "requirements": requirements,
    }



def evaluate_peace_officer_unit(
    officer,
    evaluation_date=None,
    satisfied_course_overrides=None,
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

    historical_course_numbers = {
        record.course_number
        for record in officer.training_records
        if (
            record.course_date is not None
            and record.course_date <= evaluation_date
        )
    }

    satisfied_course_overrides = set(
        satisfied_course_overrides or []
    )

    required_course_results = []

    for required in rule["required_courses"]:
        course_number = required["course_number"]

        directly_completed = (
            course_number in completed_course_numbers
        )

        approved_equivalents = set(
            required.get(
                "equivalent_courses",
                [],
            )
        )

        equivalency_window = required.get(
            "equivalency_window",
            "CURRENT_UNIT",
        )

        if equivalency_window == "ANY_HISTORY":
            equivalent_course_pool = (
                historical_course_numbers
            )
        else:
            equivalent_course_pool = (
                completed_course_numbers
            )

        configured_equivalency_completed = bool(
            approved_equivalents
            & equivalent_course_pool
        )

        override_equivalency_completed = (
            course_number in satisfied_course_overrides
        )

        equivalency_completed = (
            configured_equivalency_completed
            or override_equivalency_completed
        )

        completed = (
            directly_completed
            or equivalency_completed
        )

        satisfaction_basis = (
            "DIRECT"
            if directly_completed
            else (
                "EQUIVALENCY"
                if equivalency_completed
                else None
            )
        )

        required_course_results.append(
            {
                "course_number": course_number,
                "name": required["name"],
                "completed": completed,
                "status": (
                    "COMPLETE"
                    if completed
                    else "OUTSTANDING"
                ),
                "satisfaction_basis": satisfaction_basis,
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

    embedded_alerrt_hours = {
        str(course_number): Decimal(str(hours))
        for course_number, hours
        in rule["alerrt"].get(
            "embedded_alerrt_hours",
            {},
        ).items()
    }

    for course_number, embedded_hours in (
        embedded_alerrt_hours.items()
    ):
        if any(
            record.course_number == course_number
            for record in training
        ):
            alerrt_hours += embedded_hours

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

    current_level_one_courses = {
        current_level_one_course,
        *rule["alerrt"].get(
            "current_level_one_equivalent_courses",
            [],
        ),
    }

    has_current_level_one = any(
        record.course_number in current_level_one_courses
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

    unit_requirements = list(requirements)

    cycle_result = (
        _evaluate_below_intermediate_cycle(
            officer,
            rule,
            unit,
            credential,
            evaluation_date,
        )
    )

    cycle_status = cycle_result["status"]

    requirements = [
        *unit_requirements,
        *cycle_result["requirements"],
    ]

    if (
        unit_status == "OVERDUE"
        or cycle_status == "OVERDUE"
    ):
        compliance_status = "OVERDUE"
    elif (
        unit_status == "OUTSTANDING"
        or cycle_status == "OUTSTANDING"
    ):
        compliance_status = "OUTSTANDING"
    else:
        compliance_status = "COMPLETE"

    requirement_status = (
        "SATISFIED"
        if compliance_status == "COMPLETE"
        else (
            "OUTSTANDING"
            if compliance_status == "OUTSTANDING"
            else "FAILED"
        )
    )

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
        "cycle_status": cycle_status,
        "compliance_status": compliance_status,
        "requirement_status": requirement_status,
        "cycle_requirements_applicable":
            cycle_result["applicable"],
        "cycle_required_courses":
            cycle_result["required_courses"],
        "unit_requirements": unit_requirements,
        "cycle_requirements":
            cycle_result["requirements"],
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
