from datetime import date

from app.services.employee_workspace import (
    build_employee_workspace,
)
from app.models import Officer


EMAIL_TRACKS = {
    "peace_officer": {
        "label": "Peace Officer",
        "subject": "TCOLE Peace Officer Compliance Status",
        "source_components": {"PEACE_OFFICER"},
    },
    "jailer": {
        "label": "County Jailer",
        "subject": "TCOLE County Jailer Compliance Status",
        "source_components": {"COUNTY_JAILER"},
    },
    "telecommunicator": {
        "label": "Telecommunicator",
        "subject": (
            "TCOLE Telecommunicator Compliance Status"
        ),
        "source_components": {"TELECOMMUNICATOR"},
    },
    "combined": {
        "label": "Combined",
        "subject": "TCOLE Compliance Status",
        "source_components": {
            "PEACE_OFFICER",
            "COUNTY_JAILER",
            "TELECOMMUNICATOR",
        },
    },
}


def _format_date(value):
    if not value:
        return "Not specified"

    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return str(value)

    return (
        f"{parsed.month}/{parsed.day}/{parsed.year}"
    )


def _status_label(status):
    labels = {
        "COMPLIANT": "COMPLIANT",
        "DUE": "TRAINING DUE",
        "NONCOMPLIANT": "NONCOMPLIANT",
        "PENDING_REVIEW": "PENDING REVIEW",
        "NOT_EVALUATED": "NOT EVALUATED",
    }

    return labels.get(
        status,
        str(status or "UNKNOWN").replace("_", " "),
    )


def _format_requirement(requirement):
    message = (
        requirement.get("message")
        or requirement.get("type", "Requirement")
        .replace("_", " ")
        .title()
    )

    due_date = requirement.get("due_date")

    if due_date:
        return (
            f"- {message} "
            f"(Due {_format_date(due_date)})"
        )

    return f"- {message}"


def _requirement_matches_track(
    requirement,
    track,
):
    if track == "combined":
        return True

    source_component = requirement.get(
        "source_component"
    )

    # Requirements without a track-specific source are
    # retained. This prevents general requirements from
    # disappearing merely because a focused email was
    # requested.
    if not source_component:
        return True

    allowed = EMAIL_TRACKS[track][
        "source_components"
    ]

    return source_component in allowed


def _filter_requirements(
    requirements,
    track,
):
    return [
        requirement
        for requirement in (requirements or [])
        if _requirement_matches_track(
            requirement,
            track,
        )
    ]


def _proficiency_status_label(status):
    labels = {
        "ELIGIBLE": "ELIGIBLE",
        "NOT_ELIGIBLE": "NOT YET ELIGIBLE",
        "INSUFFICIENT_DATA": "ADDITIONAL INFORMATION NEEDED",
        "TERMINAL": "HIGHEST CERTIFICATE ACHIEVED",
        "HIGHEST_CERTIFICATE":
            "HIGHEST CERTIFICATE ACHIEVED",
        "NOT_APPLICABLE": "NOT APPLICABLE",
    }

    return labels.get(
        status,
        str(status or "UNKNOWN").replace("_", " "),
    )


def _format_course_options(course_numbers):
    course_numbers = [
        str(number)
        for number in (course_numbers or [])
        if number
    ]

    if not course_numbers:
        return None

    if len(course_numbers) == 1:
        return (
            "Required course: "
            f"TCOLE #{course_numbers[0]}"
        )

    if len(course_numbers) == 2:
        return (
            "Accepted courses: "
            f"TCOLE #{course_numbers[0]} "
            f"or #{course_numbers[1]}"
        )

    return (
        "Accepted courses: "
        + ", ".join(
            f"TCOLE #{number}"
            for number in course_numbers[:-1]
        )
        + f", or #{course_numbers[-1]}"
    )


def _proficiency_email_lines(
    advancement,
    track_label,
    highest_certificate,
):
    if (
        not advancement
        or advancement.get("status")
        == "NOT_APPLICABLE"
    ):
        return []

    current_certificate = advancement.get(
        "current_certificate"
    )
    next_certificate = advancement.get(
        "next_certificate"
    )
    status = advancement.get("status")

    lines = [
        "",
        f"{track_label.upper()} PROFICIENCY",
        "",
        (
            "Current Certificate: "
            f"{current_certificate or 'None identified'}"
        ),
    ]

    if next_certificate is None:
        lines.extend(
            [
                (
                    "Status: "
                    f"{_proficiency_status_label(status)}"
                ),
                (
                    f"{highest_certificate} is the highest "
                    f"{track_label} proficiency certificate."
                ),
            ]
        )
        return lines

    lines.extend(
        [
            f"Next Certificate: {next_certificate}",
            (
                "Advancement Status: "
                f"{_proficiency_status_label(status)}"
            ),
        ]
    )

    best_pathway = advancement.get(
        "best_available_pathway"
    ) or advancement.get(
        "qualifying_pathway"
    )

    if best_pathway:
        pathway_type = best_pathway.get("type")

        if pathway_type == "SERVICE_TRAINING":
            required_years = best_pathway.get(
                "service_years"
            )
            actual_years = best_pathway.get(
                "actual_service_years",
                advancement.get("service_years"),
            )

            required_hours = best_pathway.get(
                "training_hours"
            )
            actual_hours = best_pathway.get(
                "actual_training_hours",
                advancement.get("training_hours"),
            )

            lines.append("")

            if (
                actual_years is not None
                and required_years is not None
            ):
                service_met = (
                    actual_years >= required_years
                )

                if service_met:
                    lines.append(
                        "Service requirement met: "
                        f"{actual_years:g} years of "
                        f"{required_years:g} required"
                    )
                else:
                    years_short = (
                        required_years - actual_years
                    )

                    lines.append(
                        "Service requirement remaining: "
                        f"{actual_years:g} years completed; "
                        f"{years_short:g} additional "
                        "year"
                        f"{'s' if years_short != 1 else ''} "
                        "required"
                    )

            if (
                actual_hours is not None
                and required_hours is not None
            ):
                training_met = (
                    actual_hours >= required_hours
                )

                if training_met:
                    lines.append(
                        "Training requirement met: "
                        f"{actual_hours:,.0f} hours of "
                        f"{required_hours:,.0f} required"
                    )
                else:
                    hours_short = (
                        required_hours - actual_hours
                    )

                    lines.append(
                        "Training requirement remaining: "
                        f"{actual_hours:,.0f} hours "
                        "completed; "
                        f"{hours_short:,.0f} additional "
                        "hours required"
                    )

        elif pathway_type == "EDUCATION":
            required_years = best_pathway.get(
                "service_years"
            )
            actual_years = best_pathway.get(
                "actual_service_years",
                advancement.get("service_years"),
            )
            education_level = best_pathway.get(
                "education_level"
            )
            education_met = best_pathway.get(
                "education_met"
            )

            lines.append("")

            if (
                actual_years is not None
                and required_years is not None
            ):
                if actual_years >= required_years:
                    lines.append(
                        "Service requirement met: "
                        f"{actual_years:g} years of "
                        f"{required_years:g} required"
                    )
                else:
                    years_short = (
                        required_years - actual_years
                    )

                    lines.append(
                        "Service requirement remaining: "
                        f"{actual_years:g} years completed; "
                        f"{years_short:g} additional "
                        "year"
                        f"{'s' if years_short != 1 else ''} "
                        "required"
                    )

            if education_level:
                level = (
                    education_level
                    .replace("_", " ")
                    .title()
                )

                if education_met:
                    lines.append(
                        "Education requirement met: "
                        f"{level} degree or higher"
                    )
                else:
                    lines.append(
                        "Education requirement remaining: "
                        f"{level} degree or higher"
                    )

        elif pathway_type == "MILITARY":
            required_years = best_pathway.get(
                "service_years"
            )
            actual_years = best_pathway.get(
                "actual_service_years",
                advancement.get("service_years"),
            )
            required_months = best_pathway.get(
                "required_military_months"
            )
            actual_months = best_pathway.get(
                "actual_military_months"
            )

            lines.append("")

            if (
                actual_years is not None
                and required_years is not None
            ):
                if actual_years >= required_years:
                    lines.append(
                        "Service requirement met: "
                        f"{actual_years:g} years of "
                        f"{required_years:g} required"
                    )
                else:
                    years_short = (
                        required_years - actual_years
                    )

                    lines.append(
                        "Service requirement remaining: "
                        f"{actual_years:g} years completed; "
                        f"{years_short:g} additional "
                        "year"
                        f"{'s' if years_short != 1 else ''} "
                        "required"
                    )

            if (
                actual_months is not None
                and required_months is not None
            ):
                if actual_months >= required_months:
                    lines.append(
                        "Military service/training "
                        "requirement met: "
                        f"{actual_months:g} months of "
                        f"{required_months:g} required"
                    )
                else:
                    months_short = (
                        required_months - actual_months
                    )

                    lines.append(
                        "Military service/training "
                        "requirement remaining: "
                        f"{actual_months:g} months "
                        "verified; "
                        f"{months_short:g} additional "
                        "months required"
                    )

    missing_courses = [
        requirement
        for requirement in (
            advancement.get(
                "course_requirements"
            ) or []
        )
        if requirement.get("status") == "MISSING"
    ]

    missing_course_names = {
        (
            requirement.get("label")
            or requirement.get("name")
        )
        for requirement in missing_courses
        if (
            requirement.get("label")
            or requirement.get("name")
        )
    }

    if missing_courses:
        lines.extend(
            [
                "",
                "REMAINING CERTIFICATE REQUIREMENTS",
            ]
        )

        for requirement in missing_courses:
            label = (
                requirement.get("label")
                or requirement.get("name")
                or "Course requirement"
            )

            lines.append(f"- {label}")

            accepted_courses = (
                requirement.get("accepted_courses")
            )

            if not accepted_courses:
                course_number = requirement.get(
                    "course_number"
                )

                if course_number:
                    accepted_courses = [
                        course_number
                    ]

            options = _format_course_options(
                accepted_courses
            )

            if options:
                lines.append(f"  {options}")

    other_missing = []

    for requirement in (
        advancement.get(
            "missing_requirements"
        ) or []
    ):
        duplicate_course = any(
            requirement == course_name
            or requirement.startswith(
                f"{course_name} (#"
            )
            for course_name in missing_course_names
        )

        if not duplicate_course:
            other_missing.append(requirement)

    if other_missing:
        if not missing_courses:
            lines.extend(
                [
                    "",
                    "REMAINING CERTIFICATE REQUIREMENTS",
                ]
            )

        lines.extend(
            f"- {requirement}"
            for requirement in other_missing
        )

    insufficient = advancement.get(
        "insufficient_data_requirements"
    ) or []

    if insufficient:
        lines.extend(
            [
                "",
                "ADDITIONAL INFORMATION NEEDED",
            ]
        )

        lines.extend(
            f"- {requirement}"
            for requirement in insufficient
        )

    if status == "ELIGIBLE":
        lines.extend(
            [
                "",
                (
                    "Based on the records currently "
                    "available, you meet the identified "
                    "requirements for "
                    f"{next_certificate}."
                ),
            ]
        )

    lines.extend(
        [
            "",
            (
                "Proficiency certificate requirements are "
                "separate from your current legislative "
                "training compliance requirements."
            ),
        ]
    )

    return lines

def build_compliance_email(
    officer,
    evaluation_date=None,
    track="peace_officer",
):
    if track not in EMAIL_TRACKS:
        raise ValueError(
            "track must be one of: "
            "peace_officer, jailer, combined"
        )

    if evaluation_date is None:
        evaluation_date = date.today()

    workspace = build_employee_workspace(
        officer,
        evaluation_date=evaluation_date,
    )

    email = workspace["resolved_email"].get(
        "email"
    )

    officer_data = workspace["officer"]

    first_name = officer_data["first_name"]

    full_name = " ".join(
        part
        for part in [
            officer_data.get("first_name"),
            officer_data.get("middle_name"),
            officer_data.get("last_name"),
            officer_data.get("suffix"),
        ]
        if part
    )

    status = _status_label(
        workspace["overall_status"]
    )

    training = workspace["training_summary"]
    unit = workspace["training_unit"]

    overdue_requirements = _filter_requirements(
        workspace["overdue_requirements"],
        track,
    )

    outstanding_requirements = _filter_requirements(
        workspace["outstanding_requirements"],
        track,
    )

    pending_review_requirements = _filter_requirements(
        workspace["pending_review_requirements"],
        track,
    )

    lines = [
        f"{first_name},",
        "",
        (
            "This message provides your current TCOLE "
            "training compliance status based on the "
            "training records presently available to "
            "the agency."
        ),
        "",
        f"Current Status: {status}",
        (
            "Status Date: "
            f"{_format_date(workspace['evaluation_date'])}"
        ),
        (
            f"Training Unit {unit['unit_number']}: "
            f"{_format_date(unit['unit_start'])} through "
            f"{_format_date(unit['unit_end'])}"
        ),
    ]

    minimum_hours = training.get(
        "minimum_total_hours"
    )
    current_hours = training.get(
        "current_unit_hours"
    )

    if minimum_hours is not None:
        lines.append(
            "Current Unit Training Hours: "
            f"{current_hours:g} of "
            f"{minimum_hours:g} minimum"
        )

    if overdue_requirements:
        lines.extend(
            [
                "",
                "OVERDUE REQUIREMENTS",
            ]
        )

        lines.extend(
            _format_requirement(requirement)
            for requirement in
            overdue_requirements
        )

    if outstanding_requirements:
        lines.extend(
            [
                "",
                "OUTSTANDING REQUIREMENTS",
            ]
        )

        lines.extend(
            _format_requirement(requirement)
            for requirement in
            outstanding_requirements
        )

    if pending_review_requirements:
        lines.extend(
            [
                "",
                "RECORDS PENDING REVIEW",
            ]
        )

        lines.extend(
            _format_requirement(requirement)
            for requirement in
            pending_review_requirements
        )

    if (
        not overdue_requirements
        and not outstanding_requirements
        and not pending_review_requirements
    ):
        lines.extend(
            [
                "",
                (
                    "No outstanding TCOLE training "
                    "requirements are currently identified."
                ),
            ]
        )

    if workspace["next_due_date"]:
        lines.extend(
            [
                "",
                (
                    "Next Identified Due Date: "
                    f"{_format_date(workspace['next_due_date'])}"
                ),
            ]
        )

    proficiency_tracks = (
        workspace.get("proficiency_advancement")
        or {}
    )

    peace_officer_proficiency = (
        proficiency_tracks.get("peace_officer")
    )

    jailer_proficiency = (
        proficiency_tracks.get("jailer")
    )

    telecommunicator_proficiency = (
        proficiency_tracks.get(
            "telecommunicator"
        )
    )

    if track in {"peace_officer", "combined"}:
        lines.extend(
            _proficiency_email_lines(
                peace_officer_proficiency,
                track_label="Peace Officer",
                highest_certificate=(
                    "Master Peace Officer"
                ),
            )
        )

    if track in {"jailer", "combined"}:
        lines.extend(
            _proficiency_email_lines(
                jailer_proficiency,
                track_label="County Jailer",
                highest_certificate="Master Jailer",
            )
        )

    if track in {
        "telecommunicator",
        "combined",
    }:
        lines.extend(
            _proficiency_email_lines(
                telecommunicator_proficiency,
                track_label="Telecommunicator",
                highest_certificate=(
                    "Master Telecommunicator"
                ),
            )
        )

    lines.extend(
        [
            "",
            (
                "Please coordinate with your agency's "
                "training administrator regarding any "
                "outstanding requirements."
            ),
            (
                "If you believe the agency's records do "
                "not reflect training you have already "
                "completed, please provide the applicable "
                "training documentation for review."
            ),
            "",
            (
                "This notice was prepared from records "
                "currently available in Paradigm Training "
                "Manager."
            ),
        ]
    )

    return {
        "officer_id": str(officer.id),
        "employee_name": full_name,
        "recipient": email,
        "subject": EMAIL_TRACKS[track]["subject"],
        "body": "\n".join(lines),
        "can_email": bool(email),
    }


def get_compliance_email(
    agency_id,
    officer_id,
    evaluation_date=None,
    track="peace_officer",
):
    officer = Officer.query.filter_by(
        id=officer_id,
        agency_id=agency_id,
    ).one_or_none()

    if officer is None:
        return None

    return build_compliance_email(
        officer,
        evaluation_date=evaluation_date,
        track=track,
    )
