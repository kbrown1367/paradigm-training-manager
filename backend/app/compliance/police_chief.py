# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import json
from datetime import date
from pathlib import Path

from app.compliance.peace_officer_unit import (
    evaluate_peace_officer_unit,
)
from app.compliance.training_calendar import get_unit
from app.models import OfficerAssignment


RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "police_chief.json"
)


def load_rule():
    with RULE_PATH.open() as file:
        return json.load(file)


def get_first_chief_assignment(officer):
    assignments = [
        assignment
        for assignment in officer.assignments
        if assignment.assignment_type == "POLICE_CHIEF"
    ]

    if not assignments:
        return None

    return min(
        assignments,
        key=lambda assignment: assignment.effective_date,
    )


def get_active_chief_assignment(
    officer,
    evaluation_date,
):
    assignments = [
        assignment
        for assignment in officer.assignments
        if (
            assignment.assignment_type
            == "POLICE_CHIEF"
            and assignment.effective_date
            <= evaluation_date
            and (
                assignment.end_date is None
                or assignment.end_date
                >= evaluation_date
            )
        )
    ]

    if not assignments:
        return None

    return max(
        assignments,
        key=lambda assignment: assignment.effective_date,
    )


def find_course(
    officer,
    course_number,
    start_date=None,
    end_date=None,
):
    matches = [
        record
        for record in officer.training_records
        if record.course_number == course_number
    ]

    if start_date is not None:
        matches = [
            record
            for record in matches
            if record.course_date >= start_date
        ]

    if end_date is not None:
        matches = [
            record
            for record in matches
            if record.course_date <= end_date
        ]

    if not matches:
        return None

    return min(
        matches,
        key=lambda record: record.course_date,
    )


def evaluate_police_chief(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_rule()

    active_assignment = get_active_chief_assignment(
        officer,
        evaluation_date,
    )

    if active_assignment is None:
        return {
            "applicable": False,
            "assignment_type": "POLICE_CHIEF",
            "status": "NOT_APPLICABLE",
        }

    first_assignment = get_first_chief_assignment(
        officer
    )

    appointment_date = first_assignment.effective_date

    deadline_years = rule[
        "initial_training"
    ]["deadline_years_after_first_appointment"]

    try:
        initial_due_date = appointment_date.replace(
            year=appointment_date.year + deadline_years
        )
    except ValueError:
        initial_due_date = appointment_date.replace(
            year=appointment_date.year + deadline_years,
            day=28,
        )

    initial_results = []

    initial_completion_dates = []

    for required in rule[
        "initial_training"
    ]["required_courses"]:
        record = find_course(
            officer,
            required["course_number"],
            start_date=appointment_date,
            end_date=initial_due_date,
        )

        completed = record is not None

        if completed:
            initial_completion_dates.append(
                record.course_date
            )

        initial_results.append(
            {
                "course_number": required[
                    "course_number"
                ],
                "name": required["name"],
                "completed": completed,
                "completion_date": (
                    record.course_date.isoformat()
                    if record is not None
                    else None
                ),
                "due_date": initial_due_date.isoformat(),
            }
        )

    initial_training_complete = all(
        item["completed"]
        for item in initial_results
    )

    initial_completion_date = (
        max(initial_completion_dates)
        if initial_training_complete
        else None
    )

    unit = get_unit(evaluation_date)

    current_unit_3740 = find_course(
        officer,
        "3740",
        start_date=unit["start"],
        end_date=unit["end"],
    )

    satisfied_course_overrides = set()

    if current_unit_3740 is not None:
        for equivalency in rule[
            "continuing_education"
        ].get("course_equivalencies", []):
            satisfied_course_overrides.add(
                equivalency[
                    "satisfies_course_number"
                ]
            )

    peace_officer = evaluate_peace_officer_unit(
        officer,
        evaluation_date=evaluation_date,
        satisfied_course_overrides=(
            satisfied_course_overrides
        ),
    )

    continuing_required = (
        initial_training_complete
        and initial_completion_date
        < unit["start"]
    )

    continuing_satisfied = (
        current_unit_3740 is not None
        if continuing_required
        else None
    )

    requirements = []

    if not initial_training_complete:
        initial_status = (
            "OUTSTANDING"
            if evaluation_date <= initial_due_date
            else "FAILED"
        )

        for item in initial_results:
            if not item["completed"]:
                requirements.append(
                    {
                        "type": "NEW_CHIEF_TRAINING",
                        "status": initial_status,
                        "course_number": item[
                            "course_number"
                        ],
                        "due_date": (
                            initial_due_date.isoformat()
                        ),
                        "message": (
                            f"{item['name']} "
                            f"(#{item['course_number']}) "
                            "is required for New Chief training."
                        ),
                    }
                )

    if (
        continuing_required
        and not continuing_satisfied
    ):
        requirements.append(
            {
                "type": "CHIEF_CONTINUING_EDUCATION",
                "status": "OUTSTANDING",
                "course_number": "3740",
                "due_date": unit["end"].isoformat(),
                "message": (
                    "Texas Police Chief Leadership Series "
                    "(#3740) is required during this "
                    "training unit."
                ),
            }
        )

    chief_status = (
        "COMPLETE"
        if not requirements
        else (
            "OVERDUE"
            if any(
                item["status"] == "FAILED"
                for item in requirements
            )
            else "OUTSTANDING"
        )
    )

    return {
        "applicable": True,
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["version"],
        "assignment_type": "POLICE_CHIEF",
        "assignment_effective_date": (
            active_assignment.effective_date.isoformat()
        ),
        "first_chief_appointment_date": (
            appointment_date.isoformat()
        ),
        "initial_training_due_date": (
            initial_due_date.isoformat()
        ),
        "initial_training_complete": (
            initial_training_complete
        ),
        "initial_training_completion_date": (
            initial_completion_date.isoformat()
            if initial_completion_date
            else None
        ),
        "initial_training": initial_results,
        "continuing_education_required": (
            continuing_required
        ),
        "current_unit_3740_completed": (
            current_unit_3740 is not None
        ),
        "current_unit_3740_completion_date": (
            current_unit_3740.course_date.isoformat()
            if current_unit_3740
            else None
        ),
        "state_federal_law_update_satisfied_by_3740": (
            current_unit_3740 is not None
        ),
        "supervisor_requirement_satisfied_by_3740": (
            current_unit_3740 is not None
        ),
        "chief_status": chief_status,
        "requirements": requirements,
        "peace_officer": peace_officer,
    }
