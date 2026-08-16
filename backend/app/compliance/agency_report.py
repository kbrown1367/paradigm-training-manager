# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import re
from datetime import date

from app.compliance.agency_dashboard import (
    evaluate_agency_compliance_dashboard,
)
from app.compliance.officer_profile import (
    evaluate_officer_compliance_profile,
)
from app.models import Officer


REPORTABLE_STATUSES = {
    "OVERDUE",
    "PENDING_REVIEW",
    "OUTSTANDING",
}


REQUIREMENT_TYPE_NAMES = {
    "ALERRT_HOURS":
        "ALERRT Training Hours",
    "TOTAL_HOURS":
        "Minimum Training Hours",
    "ALERRT_LEVEL_ONE":
        "ALERRT Level I",
    "HB33_SUPERVISOR_TRAINING":
        "HB 33 Supervisor Training",
    "PIO_APPROVED_TRAINING":
        "Public Information Officer Training",
    "CHIEF_CONTINUING_EDUCATION":
        "Texas Police Chief Leadership Series",
    "MINIMUM_TRAINING_HOURS":
        "Telecommunicator Training Hours",
}


TRACK_LABELS = {
    "peace_officer": "Peace Officer",
    "jailer": "County Jailer",
    "telecommunicator": "Telecommunicator",
}


def _deduplicate(values):
    result = []

    for value in values:
        value = str(value)

        if value not in result:
            result.append(value)

    return result


def _name_from_message(message):
    if not message:
        return None

    # Most course requirements use:
    #
    # Course Name (#1234) remains outstanding.
    #
    # Extracting the text before the course reference
    # lets the report reuse the compliance engine's
    # established terminology instead of maintaining
    # another course-name catalog.
    match = re.match(
        r"^\s*(.+?)\s+\(#",
        message,
    )

    if match:
        return match.group(1).strip()

    match = re.match(
        r"^\s*(.+?)\s+remains outstanding",
        message,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return None


def _humanize_identifier(value):
    if not value:
        return None

    words = str(value).replace("_", " ").split()

    special = {
        "ALERRT": "ALERRT",
        "HB33": "HB 33",
        "PIO": "PIO",
        "TCOLE": "TCOLE",
    }

    result = []

    for word in words:
        upper = word.upper()

        if upper in special:
            result.append(special[upper])
        else:
            result.append(word.capitalize())

    return " ".join(result)


def _requirement_name(requirement):
    for key in (
        "course_title",
        "title",
        "name",
        "requirement_name",
    ):
        value = requirement.get(key)

        if value:
            return str(value).strip()

    requirement_type = (
        requirement.get("type")
        or requirement.get("requirement_type")
    )

    if requirement_type in REQUIREMENT_TYPE_NAMES:
        return REQUIREMENT_TYPE_NAMES[
            requirement_type
        ]

    message_name = _name_from_message(
        requirement.get("message")
    )

    if message_name:
        return message_name

    return (
        _humanize_identifier(requirement_type)
        or "Compliance Requirement"
    )


def _requirement_course_numbers(requirement):
    values = []

    for key in (
        "course_number",
        "course_id",
        "required_course",
    ):
        value = requirement.get(key)

        if value:
            values.append(value)

    for key in (
        "accepted_courses",
        "equivalent_courses",
        "approved_course_numbers",
    ):
        for value in requirement.get(key, []) or []:
            values.append(value)

    for item in requirement.get(
        "eligible_courses",
        [],
    ) or []:
        if isinstance(item, dict):
            value = item.get("course_number")

            if value:
                values.append(value)
        elif item:
            values.append(item)

    # Some components currently expose the approved
    # alternatives only in their explanatory message,
    # such as the HB 33 supervisor requirement.
    #
    # Preserve those course numbers for the report
    # without making them part of compliance logic.
    message = requirement.get("message") or ""

    values.extend(
        re.findall(
            r"#(\d+)",
            message,
        )
    )

    return _deduplicate(values)


def _normalize_requirement(requirement):
    return {
        "source_component":
            requirement.get("source_component"),
        "type":
            requirement.get("type")
            or requirement.get("requirement_type"),
        "display_name":
            _requirement_name(requirement),
        "course_numbers":
            _requirement_course_numbers(
                requirement
            ),
        "scope":
            requirement.get("scope"),
        "status":
            requirement.get("normalized_status")
            or requirement.get("status"),
        "due_date":
            requirement.get("due_date"),
        "message":
            requirement.get("message")
            or requirement.get("description"),
        "agency_review_recommended":
            bool(
                requirement.get(
                    "agency_review_recommended",
                    False,
                )
            ),
    }


def _requirement_key(requirement):
    return (
        requirement.get("source_component", ""),
        requirement.get("type", ""),
        requirement.get("display_name", ""),
        tuple(
            requirement.get(
                "course_numbers",
                [],
            )
        ),
        requirement.get("due_date"),
    )


def _reportable_requirements(profile):
    requirements = []

    for requirement in profile["requirements"]:
        status = requirement.get(
            "normalized_status"
        )

        if status not in REPORTABLE_STATUSES:
            continue

        requirements.append(
            _normalize_requirement(
                requirement
            )
        )

    return requirements


def _build_requirement_rollup(employee_profiles):
    groups = {}

    for employee, profile in employee_profiles:
        for requirement in _reportable_requirements(
            profile
        ):
            key = _requirement_key(requirement)

            if key not in groups:
                groups[key] = {
                    "source_component":
                        requirement.get(
                            "source_component"
                        ),
                    "type":
                        requirement.get("type"),
                    "display_name":
                        requirement.get(
                            "display_name"
                        ),
                    "course_numbers":
                        requirement.get(
                            "course_numbers",
                            [],
                        ),
                    "scope":
                        requirement.get("scope"),
                    "due_date":
                        requirement.get(
                            "due_date"
                        ),
                    "message":
                        requirement.get(
                            "message"
                        ),
                    "overdue_count": 0,
                    "outstanding_count": 0,
                    "pending_review_count": 0,
                    "agency_review_count": 0,
                    "employee_count": 0,
                    "employees": [],
                }

            group = groups[key]
            status = requirement.get("status")

            if status == "OVERDUE":
                group["overdue_count"] += 1

            elif status == "OUTSTANDING":
                group["outstanding_count"] += 1

            elif status == "PENDING_REVIEW":
                group[
                    "pending_review_count"
                ] += 1

            if requirement.get(
                "agency_review_recommended"
            ):
                group["agency_review_count"] += 1

            group["employee_count"] += 1

            group["employees"].append(
                {
                    "id": str(employee.id),
                    "tcole_pid":
                        employee.tcole_pid,
                    "first_name":
                        employee.first_name,
                    "last_name":
                        employee.last_name,
                    "status": status,
                    "agency_review_recommended":
                        requirement.get(
                            "agency_review_recommended",
                            False,
                        ),
                }
            )

    rollup = list(groups.values())

    for group in rollup:
        group["employees"].sort(
            key=lambda employee: (
                employee[
                    "last_name"
                ].lower(),
                employee[
                    "first_name"
                ].lower(),
            )
        )

    rollup.sort(
        key=lambda group: (
            0 if group["overdue_count"] else 1,
            (
                0
                if group[
                    "pending_review_count"
                ]
                else 1
            ),
            -group["employee_count"],
            group["due_date"]
            or "9999-12-31",
            group[
                "display_name"
            ].lower(),
        )
    )

    return rollup


def _build_training_plan(requirement_rollup):
    plan = []

    for requirement in requirement_rollup:
        if requirement[
            "pending_review_count"
        ]:
            action = "REVIEW"

        elif requirement[
            "overdue_count"
        ]:
            action = "IMMEDIATE"

        else:
            action = "SCHEDULE"

        plan.append(
            {
                **requirement,
                "recommended_action":
                    action,
            }
        )

    return plan


def _build_employee_findings(employee_profiles):
    findings = []

    for employee, profile in employee_profiles:
        requirements = _reportable_requirements(
            profile
        )

        if not requirements:
            continue

        findings.append(
            {
                "id": str(employee.id),
                "tcole_pid":
                    employee.tcole_pid,
                "first_name":
                    employee.first_name,
                "middle_name":
                    employee.middle_name,
                "last_name":
                    employee.last_name,
                "suffix":
                    employee.suffix,
                "overall_status":
                    profile["overall_status"],
                "highest_certificate":
                    profile["officer"][
                        "highest_certificate"
                    ],
                "next_due_date":
                    profile["next_due_date"],
                "requirements":
                    requirements,
            }
        )

    status_priority = {
        "NONCOMPLIANT": 0,
        "PENDING_REVIEW": 1,
        "DUE": 2,
        "COMPLIANT": 3,
        "NOT_EVALUATED": 4,
    }

    findings.sort(
        key=lambda employee: (
            status_priority.get(
                employee[
                    "overall_status"
                ],
                99,
            ),
            employee[
                "last_name"
            ].lower(),
            employee[
                "first_name"
            ].lower(),
        )
    )

    return findings


def _build_proficiency_opportunities(
    dashboard,
):
    opportunities = []

    for employee in dashboard["employees"]:
        advancement = employee.get(
            "proficiency_advancement"
        ) or {}

        for track, result in advancement.items():
            if not result:
                continue

            if result.get("status") != "ELIGIBLE":
                continue

            next_certificate = result.get(
                "next_certificate"
            )

            if not next_certificate:
                continue

            opportunities.append(
                {
                    "id": employee["id"],
                    "tcole_pid":
                        employee["tcole_pid"],
                    "first_name":
                        employee["first_name"],
                    "last_name":
                        employee["last_name"],
                    "track": track,
                    "track_label":
                        TRACK_LABELS.get(
                            track,
                            _humanize_identifier(
                                track
                            ),
                        ),
                    "current_certificate":
                        result.get(
                            "current_certificate"
                        ),
                    "next_certificate":
                        next_certificate,
                    "status": "ELIGIBLE",
                    "qualifying_pathway":
                        result.get(
                            "qualifying_pathway"
                        ),
                }
            )

    opportunities.sort(
        key=lambda employee: (
            employee[
                "last_name"
            ].lower(),
            employee[
                "first_name"
            ].lower(),
            employee[
                "track_label"
            ].lower(),
        )
    )

    return opportunities


def evaluate_agency_compliance_report(
    agency_id,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    dashboard = (
        evaluate_agency_compliance_dashboard(
            agency_id,
            evaluation_date=evaluation_date,
        )
    )

    if dashboard is None:
        return None

    officers = (
        Officer.query
        .filter_by(
            agency_id=agency_id,
            employment_status="active",
        )
        .order_by(
            Officer.last_name,
            Officer.first_name,
        )
        .all()
    )

    employee_profiles = []

    for officer in officers:
        profile = (
            evaluate_officer_compliance_profile(
                officer,
                evaluation_date=evaluation_date,
            )
        )

        employee_profiles.append(
            (officer, profile)
        )

    employee_findings = (
        _build_employee_findings(
            employee_profiles
        )
    )

    requirement_rollup = (
        _build_requirement_rollup(
            employee_profiles
        )
    )

    training_plan = _build_training_plan(
        requirement_rollup
    )

    proficiency_opportunities = (
        _build_proficiency_opportunities(
            dashboard
        )
    )

    return {
        "report": {
            "title":
                "Agency Compliance Report",
            "product":
                "Paradigm Training Manager™",
            "evaluation_date":
                evaluation_date.isoformat(),
        },
        "agency":
            dashboard["agency"],
        "training_cycle":
            dashboard["training_cycle"],
        "training_unit":
            dashboard["training_unit"],
        "executive_summary":
            dashboard["summary"],
        "employee_findings":
            employee_findings,
        "requirement_rollup":
            requirement_rollup,
        "training_plan":
            training_plan,
        "proficiency_opportunities":
            proficiency_opportunities,
    }
