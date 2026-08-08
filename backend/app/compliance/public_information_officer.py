import json
from datetime import date
from pathlib import Path

from app.models import (
    OfficerAssignment,
    OfficerCredentialVerification,
)


RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "public_information_officer.json"
)


def load_rule():
    with RULE_PATH.open() as file:
        return json.load(file)


def add_years(value, years=1):
    try:
        return value.replace(
            year=value.year + years
        )
    except ValueError:
        return value.replace(
            year=value.year + years,
            day=28,
        )


def get_active_pio_assignment(
    officer,
    evaluation_date,
):
    assignments = [
        assignment
        for assignment in officer.assignments
        if (
            assignment.assignment_type
            == "PUBLIC_INFORMATION_OFFICER"
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
        key=lambda item: item.effective_date,
    )


def determine_annual_window(
    appointment_date,
    evaluation_date,
):
    first_due = add_years(
        appointment_date,
        1,
    )

    if evaluation_date <= first_due:
        return {
            "period_number": 1,
            "start": appointment_date,
            "due": first_due,
        }

    period_number = 2
    period_start = first_due
    period_due = add_years(first_due, 1)

    while evaluation_date > period_due:
        period_number += 1
        period_start = period_due
        period_due = add_years(period_due, 1)

    return {
        "period_number": period_number,
        "start": period_start,
        "due": period_due,
    }


def find_approved_training(
    officer,
    approved_course_numbers,
    start_date,
    due_date,
):
    matches = [
        record
        for record in officer.training_records
        if (
            record.course_number
            in approved_course_numbers
            and start_date
            <= record.course_date
            <= due_date
        )
    ]

    if not matches:
        return None

    return min(
        matches,
        key=lambda record: record.course_date,
    )


def evaluate_public_information_officer(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_rule()

    assignment = get_active_pio_assignment(
        officer,
        evaluation_date,
    )

    if assignment is None:
        return {
            "applicable": False,
            "assignment_type":
                "PUBLIC_INFORMATION_OFFICER",
            "status": "NOT_APPLICABLE",
        }

    annual_window = determine_annual_window(
        assignment.effective_date,
        evaluation_date,
    )

    approved_courses = {
        item["course_number"]: item["name"]
        for item in rule["approved_courses"]
    }

    training = find_approved_training(
        officer,
        set(approved_courses),
        annual_window["start"],
        annual_window["due"],
    )

    training_completed = training is not None

    if training_completed:
        training_status = "COMPLIANT"
    elif evaluation_date <= annual_window["due"]:
        training_status = "FUTURE_REQUIREMENT"
    else:
        training_status = "NON_COMPLIANT"

    tdem_verification = (
        OfficerCredentialVerification.query
        .filter_by(
            agency_id=officer.agency_id,
            officer_id=officer.id,
            credential_type="TDEM_PIO_CERTIFICATION",
            status="VERIFIED",
            revoked_at=None,
        )
        .order_by(
            OfficerCredentialVerification.verified_at.desc()
        )
        .first()
    )

    tdem_verified = (
        tdem_verification is not None
    )

    tdem_status = (
        "VERIFIED"
        if tdem_verified
        else "UNVERIFIED"
    )

    if not training_completed:
        overall_status = training_status
    elif not tdem_verified:
        overall_status = "PENDING"
    else:
        overall_status = "COMPLIANT"

    deficiencies = []

    if not training_completed:
        deficiencies.append(
            {
                "type": "PIO_APPROVED_TRAINING",
                "status": (
                    "OUTSTANDING"
                    if evaluation_date
                    <= annual_window["due"]
                    else "OVERDUE"
                ),
                "due_date":
                    annual_window["due"].isoformat(),
                "message": (
                    "One approved Public Information "
                    "Officer course is required."
                ),
            }
        )

    if (
        training_completed
        and not tdem_verified
    ):
        deficiencies.append(
            {
                "type": "TDEM_CERTIFICATION",
                "status": "UNVERIFIED",
                "due_date": None,
                "message": (
                    "Approved PIO training was found, "
                    "but TDEM certification has not "
                    "been independently verified in PTM."
                ),
            }
        )

    return {
        "applicable": True,
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["version"],
        "assignment_type":
            "PUBLIC_INFORMATION_OFFICER",
        "assignment_effective_date":
            assignment.effective_date.isoformat(),
        "evaluation_date":
            evaluation_date.isoformat(),
        "annual_period_number":
            annual_window["period_number"],
        "annual_period_start":
            annual_window["start"].isoformat(),
        "annual_due_date":
            annual_window["due"].isoformat(),
        "approved_course_numbers":
            list(approved_courses.keys()),
        "training_completed": training_completed,
        "training_status": training_status,
        "training_course_number": (
            training.course_number
            if training is not None
            else None
        ),
        "training_course_name": (
            approved_courses.get(
                training.course_number
            )
            if training is not None
            else None
        ),
        "training_completion_date": (
            training.course_date.isoformat()
            if training is not None
            else None
        ),
        "tdem_certification_required": True,
        "tdem_certification_status":
            tdem_status,
        "tdem_certification_verified":
            tdem_verified,
        "tdem_certification_effective_date": (
            tdem_verification.effective_date.isoformat()
            if (
                tdem_verification is not None
                and tdem_verification.effective_date
            )
            else None
        ),
        "tdem_certification_verified_at": (
            tdem_verification.verified_at.isoformat()
            if tdem_verification is not None
            else None
        ),
        "status": overall_status,
        "deficiencies": deficiencies,
    }
