# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.compliance.telecommunicator_proficiency import (
    has_telecommunicator_license,
)
from app.compliance.training_calendar import get_unit


RULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rules"
    / "data"
    / "telecommunicator_unit_2025_2027.json"
)


def _load_rule():
    with RULE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def _course_number(record):
    value = getattr(
        record,
        "course_number",
        None,
    )

    if value is None:
        return None

    return str(value).strip()


def _credited_hours(record):
    value = getattr(
        record,
        "credited_hours",
        None,
    )

    if value is None:
        return Decimal("0")

    return Decimal(str(value))


def evaluate_telecommunicator_unit(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    if not has_telecommunicator_license(officer):
        return {
            "applicable": False,
            "unit_status": "NOT_APPLICABLE",
            "requirements": [],
            "deficiencies": [],
        }

    rule = _load_rule()
    unit = get_unit(evaluation_date)

    unit_start = unit["start"]
    unit_end = unit["end"]

    records = [
        record
        for record in officer.training_records
        if (
            record.course_date is not None
            and unit_start
            <= record.course_date
            <= unit_end
        )
    ]

    total_hours = sum(
        (
            _credited_hours(record)
            for record in records
        ),
        Decimal("0"),
    )

    minimum_hours = Decimal(
        str(rule["minimum_total_hours"])
    )

    remaining_hours = max(
        Decimal("0"),
        minimum_hours - total_hours,
    )

    requirements = []

    if remaining_hours > 0:
        requirements.append(
            {
                "requirement_type":
                    "MINIMUM_TRAINING_HOURS",
                "title":
                    "Telecommunicator Training Hours",
                "description": (
                    f"{remaining_hours} additional "
                    "training hours required during "
                    "the current training unit."
                ),
                "message": (
                    f"{float(remaining_hours):g} additional "
                    "Telecommunicator training hours "
                    "required."
                ),
                "minimum_hours":
                    float(minimum_hours),
                "completed_hours":
                    float(total_hours),
                "remaining_hours":
                    float(remaining_hours),
                "status": (
                    "OUTSTANDING"
                    if evaluation_date <= unit_end
                    else "OVERDUE"
                ),
                "due_date":
                    unit_end.isoformat(),
            }
        )

    required_course_results = []

    for required_course in rule[
        "required_courses"
    ]:
        required_number = str(
            required_course["course_number"]
        ).strip()

        matching_records = [
            record
            for record in records
            if (
                _course_number(record)
                == required_number
            )
        ]

        complete = bool(matching_records)

        course_result = {
            "requirement_type":
                "REQUIRED_COURSE",
            "course_number":
                required_number,
            "course_title":
                required_course["course_title"],
            "message": (
                f"{required_course['course_title']} "
                f"(#{required_number}) remains "
                "outstanding."
            ),
            "status": (
                "COMPLETE"
                if complete
                else (
                    "OUTSTANDING"
                    if evaluation_date <= unit_end
                    else "OVERDUE"
                )
            ),
            "due_date":
                unit_end.isoformat(),
        }

        required_course_results.append(
            course_result
        )

        if not complete:
            requirements.append(
                dict(course_result)
            )

    if any(
        item["status"] == "OVERDUE"
        for item in requirements
    ):
        unit_status = "OVERDUE"
    elif requirements:
        unit_status = "OUTSTANDING"
    else:
        unit_status = "COMPLETE"

    return {
        "applicable": True,
        "unit_status": unit_status,
        "unit_number": unit["unit_number"],
        "unit_start": unit_start.isoformat(),
        "unit_end": unit_end.isoformat(),
        "due_date": unit_end.isoformat(),
        "minimum_total_hours":
            float(minimum_hours),
        "current_unit_hours":
            float(total_hours),
        "remaining_total_hours":
            float(remaining_hours),
        "required_courses":
            required_course_results,
        "requirements": requirements,
        "deficiencies": requirements,
        "rule_version": rule["rule_id"],
    }
