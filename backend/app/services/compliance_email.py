from datetime import date

from app.services.employee_workspace import (
    build_employee_workspace,
)
from app.models import Officer


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


def build_compliance_email(
    officer,
    evaluation_date=None,
):
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
        ]
        if part
    )

    status = _status_label(
        workspace["overall_status"]
    )

    training = workspace["training_summary"]
    unit = workspace["training_unit"]

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

    if workspace["overdue_requirements"]:
        lines.extend(
            [
                "",
                "OVERDUE REQUIREMENTS",
            ]
        )

        lines.extend(
            _format_requirement(requirement)
            for requirement in
            workspace["overdue_requirements"]
        )

    if workspace["outstanding_requirements"]:
        lines.extend(
            [
                "",
                "OUTSTANDING REQUIREMENTS",
            ]
        )

        lines.extend(
            _format_requirement(requirement)
            for requirement in
            workspace["outstanding_requirements"]
        )

    if workspace["pending_review_requirements"]:
        lines.extend(
            [
                "",
                "RECORDS PENDING REVIEW",
            ]
        )

        lines.extend(
            _format_requirement(requirement)
            for requirement in
            workspace["pending_review_requirements"]
        )

    if (
        not workspace["overdue_requirements"]
        and not workspace["outstanding_requirements"]
        and not workspace["pending_review_requirements"]
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
        "subject": "TCOLE Training Compliance Status",
        "body": "\n".join(lines),
        "can_email": bool(email),
    }


def get_compliance_email(
    agency_id,
    officer_id,
    evaluation_date=None,
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
    )
