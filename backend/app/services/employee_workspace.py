from datetime import date
from decimal import Decimal

from app.compliance.email_resolver import (
    resolve_officer_email,
)
from app.compliance.officer_profile import (
    evaluate_officer_compliance_profile,
)
from app.compliance.proficiency_tracks import (
    build_proficiency_advancement,
)
from app.compliance.training_calendar import get_unit
from app.models import Officer
from app.services.license_tracking import (
    serialize_license_tracking,
)


def _serialize_assignment(assignment):
    return {
        "id": str(assignment.id),
        "assignment_type": assignment.assignment_type,
        "effective_date": (
            assignment.effective_date.isoformat()
            if assignment.effective_date
            else None
        ),
        "end_date": (
            assignment.end_date.isoformat()
            if assignment.end_date
            else None
        ),
        "active": assignment.end_date is None,
    }


def _serialize_training_record(record):
    return {
        "id": str(record.id),
        "course_number": record.course_number,
        "course_title": record.course_title,
        "course_date": record.course_date.isoformat(),
        "credited_hours": (
            float(record.credited_hours)
            if record.credited_hours is not None
            else None
        ),
        "hours_source": record.hours_source,
        "source": record.source,
    }


def build_employee_workspace(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    profile = evaluate_officer_compliance_profile(
        officer,
        evaluation_date=evaluation_date,
    )

    proficiency_advancement = (
        build_proficiency_advancement(
            officer,
            evaluation_date=evaluation_date,
        )
    )

    email = resolve_officer_email(officer)
    unit = get_unit(evaluation_date)

    current_unit_training = sorted(
        (
            record
            for record in officer.training_records
            if (
                unit["start"]
                <= record.course_date
                <= unit["end"]
            )
        ),
        key=lambda record: (
            record.course_date,
            record.course_number,
            record.course_title,
        ),
        reverse=True,
    )

    current_unit_hours = sum(
        (
            Decimal(record.credited_hours)
            for record in current_unit_training
            if record.credited_hours is not None
        ),
        Decimal("0"),
    )

    assignments = sorted(
        officer.assignments,
        key=lambda assignment: (
            assignment.effective_date,
            assignment.assignment_type,
        ),
        reverse=True,
    )

    peace_officer_component = profile[
        "components"
    ].get("PEACE_OFFICER", {})

    county_jailer_component = profile[
        "components"
    ].get("COUNTY_JAILER", {})

    telecommunicator_component = profile[
        "components"
    ].get("TELECOMMUNICATOR", {})

    # Summary cards should reflect an applicable primary
    # license-track unit evaluation rather than assuming
    # every employee is evaluated as a Peace Officer.
    if peace_officer_component.get("applicable"):
        summary_component = peace_officer_component
    elif county_jailer_component.get("applicable"):
        summary_component = county_jailer_component
    elif telecommunicator_component.get("applicable"):
        summary_component = telecommunicator_component
    else:
        summary_component = {}

    summary_result = (
        summary_component.get("result", {})
    )

    training_summary = {
        "current_unit_hours":
            float(current_unit_hours),
        "minimum_total_hours":
            summary_result.get(
                "minimum_total_hours"
            ),
        "remaining_total_hours":
            summary_result.get(
                "remaining_total_hours"
            ),
        "alerrt_hours":
            summary_result.get(
                "alerrt_hours"
            ),
        "required_alerrt_hours":
            summary_result.get(
                "required_alerrt_hours"
            ),
        "remaining_alerrt_hours":
            summary_result.get(
                "remaining_alerrt_hours"
            ),
        "training_record_count":
            len(current_unit_training),
    }

    return {
        "officer": {
            **profile["officer"],
            "email_override":
                officer.email_override,
            "employment_status":
                officer.employment_status,
            "archived_at": (
                officer.archived_at.isoformat()
                if officer.archived_at
                else None
            ),
            "archived_reason":
                officer.archived_reason,
        },
        "resolved_email": email,
        "license_tracking":
            serialize_license_tracking(officer),
        "evaluation_date":
            evaluation_date.isoformat(),
        "overall_status":
            profile["overall_status"],
        "evaluation_coverage":
            profile["evaluation_coverage"],
        "review_required":
            profile["review_required"],
        "next_due_date":
            profile["next_due_date"],
        "counts": {
            "overdue":
                profile["overdue_count"],
            "outstanding":
                profile["outstanding_count"],
            "pending_review":
                profile["pending_review_count"],
            "agency_review":
                profile["agency_review_count"],
        },
        "training_unit": {
            "cycle_number":
                unit["cycle_number"],
            "cycle_start":
                unit["cycle_start"].isoformat(),
            "cycle_end":
                unit["cycle_end"].isoformat(),
            "unit_number":
                unit["unit_number"],
            "unit_start":
                unit["start"].isoformat(),
            "unit_end":
                unit["end"].isoformat(),
        },
        "training_summary": training_summary,
        "assignments": [
            _serialize_assignment(assignment)
            for assignment in assignments
        ],
        "current_unit_training": [
            _serialize_training_record(record)
            for record in current_unit_training
        ],
        "requirements":
            profile["requirements"],
        "overdue_requirements":
            profile["overdue_requirements"],
        "outstanding_requirements":
            profile["outstanding_requirements"],
        "pending_review_requirements":
            profile[
                "pending_review_requirements"
            ],
        "agency_review_requirements":
            profile[
                "agency_review_requirements"
            ],
        "components":
            profile["components"],
        "proficiency_advancement":
            proficiency_advancement,
    }


def get_employee_workspace(
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

    return build_employee_workspace(
        officer,
        evaluation_date=evaluation_date,
    )
