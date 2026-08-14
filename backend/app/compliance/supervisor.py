# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import json
from datetime import date
from pathlib import Path


RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "supervisor.json"
)


def load_rule():
    with RULE_PATH.open() as file:
        return json.load(file)


def add_years(value, years):
    try:
        return value.replace(
            year=value.year + years
        )
    except ValueError:
        return value.replace(
            year=value.year + years,
            day=28,
        )


def get_supervisor_assignments(officer):
    return sorted(
        [
            assignment
            for assignment in officer.assignments
            if assignment.assignment_type == "SUPERVISOR"
        ],
        key=lambda item: item.effective_date,
    )


def get_active_supervisor_assignment(
    officer,
    evaluation_date,
):
    assignments = [
        assignment
        for assignment in get_supervisor_assignments(officer)
        if (
            assignment.effective_date <= evaluation_date
            and (
                assignment.end_date is None
                or assignment.end_date >= evaluation_date
            )
        )
    ]

    if not assignments:
        return None

    return max(
        assignments,
        key=lambda item: item.effective_date,
    )


def find_course(
    officer,
    course_numbers,
    start_date=None,
    end_date=None,
):
    matches = [
        record
        for record in officer.training_records
        if record.course_number in course_numbers
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


def evaluate_supervisor(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_rule()

    active_assignment = get_active_supervisor_assignment(
        officer,
        evaluation_date,
    )

    if active_assignment is None:
        return {
            "applicable": False,
            "assignment_type": "SUPERVISOR",
            "status": "NOT_APPLICABLE",
        }

    all_supervisor_assignments = (
        get_supervisor_assignments(officer)
    )

    first_assignment = all_supervisor_assignments[0]

    first_appointment_date = (
        first_assignment.effective_date
    )

    first_window_start = add_years(
        first_appointment_date,
        -rule[
            "first_time_supervisor"
        ]["window_years_before"],
    )

    first_window_end = add_years(
        first_appointment_date,
        rule[
            "first_time_supervisor"
        ]["window_years_after"],
    )

    # Course #3737 is a one-time, career-level requirement.
    # Any documented completion in the officer's imported
    # TCOLE training history satisfies the current requirement.
    #
    # The appointment window is retained separately so PTM can
    # distinguish timely completion from prior or late completion.
    course_3737 = find_course(
        officer,
        {
            rule[
                "first_time_supervisor"
            ]["course_number"]
        },
    )

    first_time_complete = (
        course_3737 is not None
    )

    if course_3737 is None:
        completion_timing = None
    elif (
        first_window_start
        <= course_3737.course_date
        <= first_window_end
    ):
        completion_timing = "WITHIN_WINDOW"
    elif course_3737.course_date < first_window_start:
        completion_timing = "PRIOR_COMPLETION"
    else:
        completion_timing = "LATE_COMPLETION"

    completed_within_window = (
        completion_timing == "WITHIN_WINDOW"
    )

    hb33_due = date.fromisoformat(
        rule["hb33"]["due_date"]
    )

    hb33_course_numbers = {
        item["course_number"]
        for item in rule[
            "hb33"
        ]["eligible_courses"]
    }

    hb33_course_names = {
        item["course_number"]: item["name"]
        for item in rule[
            "hb33"
        ]["eligible_courses"]
    }

    hb33_course_options = "; ".join(
        (
            f"#{item['course_number']} "
            f"{item['name']}"
        )
        for item in rule[
            "hb33"
        ]["eligible_courses"]
    )

    hb33_training = find_course(
        officer,
        hb33_course_numbers,
        end_date=hb33_due,
    )

    hb33_complete = (
        hb33_training is not None
    )

    requirements = []

    if not first_time_complete:
        requirements.append(
            {
                "type": "NEW_SUPERVISOR_TRAINING",
                "course_number": "3737",
                "status": (
                    "OUTSTANDING"
                    if evaluation_date <= first_window_end
                    else "OVERDUE"
                ),
                "window_start":
                    first_window_start.isoformat(),
                "due_date":
                    first_window_end.isoformat(),
                "evidence_basis": (
                    "No qualifying #3737 completion was found "
                    "in the imported TCOLE training record "
                    "during the applicable appointment window."
                ),
                "agency_review_recommended": True,
                "message": (
                    "No qualifying New Supervisor's Course "
                    "(#3737) completion was found in the "
                    "imported TCOLE training record for the "
                    f"required {first_window_start.isoformat()} "
                    f"through {first_window_end.isoformat()} "
                    "window. Agency review recommended."
                ),
            }
        )

    if not hb33_complete:
        requirements.append(
            {
                "type": "HB33_SUPERVISOR_TRAINING",
                "status": (
                    "OUTSTANDING"
                    if evaluation_date <= hb33_due
                    else "OVERDUE"
                ),
                "due_date": hb33_due.isoformat(),
                "evidence_basis": (
                    "No approved HB33 supervisor course was "
                    "found in the imported TCOLE training record."
                ),
                "agency_review_recommended": True,
                "message": (
                    "HB33 Supervisor Training remains "
                    "outstanding. Complete one approved "
                    "course by "
                    f"{hb33_due.strftime('%m/%d/%Y')}: "
                    f"{hb33_course_options}. "
                    "No qualifying completion was found in "
                    "the imported TCOLE training record. "
                    "Agency review recommended."
                ),
            }
        )

    if not requirements:
        status = "COMPLIANT"
    elif any(
        item["status"] == "OVERDUE"
        for item in requirements
    ):
        status = "NONCOMPLIANT"
    else:
        status = "DUE"

    return {
        "applicable": True,
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["version"],
        "assignment_type": "SUPERVISOR",
        "assignment_effective_date":
            active_assignment.effective_date.isoformat(),
        "first_supervisor_appointment_date":
            first_appointment_date.isoformat(),
        "evaluation_date":
            evaluation_date.isoformat(),
        "first_time_supervisor": {
            "required": True,
            "course_number": "3737",
            "window_start":
                first_window_start.isoformat(),
            "due_date":
                first_window_end.isoformat(),
            "completed": first_time_complete,
            "completion_date": (
                course_3737.course_date.isoformat()
                if course_3737
                else None
            ),
            "completion_timing": completion_timing,
            "completed_within_window":
                completed_within_window,
            "repeat_required": False,
        },
        "hb33": {
            "due_date": hb33_due.isoformat(),
            "completed": hb33_complete,
            "completion_course_number": (
                hb33_training.course_number
                if hb33_training
                else None
            ),
            "completion_course_name": (
                hb33_course_names.get(
                    hb33_training.course_number
                )
                if hb33_training
                else None
            ),
            "completion_date": (
                hb33_training.course_date.isoformat()
                if hb33_training
                else None
            ),
        },
        "status": status,
        "requirements": requirements,
        "deficiencies": requirements,
    }
