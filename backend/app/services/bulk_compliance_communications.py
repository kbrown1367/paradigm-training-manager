# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

from datetime import date

from app.compliance.email_resolver import (
    resolve_officer_email,
)
from app.compliance.officer_profile import (
    evaluate_officer_compliance_profile,
)
from app.models import Agency, Officer


PRIMARY_TRACK_COMPONENTS = {
    "PEACE_OFFICER": "peace_officer",
    "COUNTY_JAILER": "jailer",
    "TELECOMMUNICATOR": "telecommunicator",
}

DEFAULT_SELECTED_STATUSES = {
    "DUE",
    "NONCOMPLIANT",
}


def _employee_name(officer):
    return " ".join(
        part
        for part in [
            officer.first_name,
            officer.middle_name,
            officer.last_name,
            officer.suffix,
        ]
        if part
    )


def _applicable_tracks(profile):
    applicable_components = (
        profile.get("evaluation_coverage", {})
        .get("applicable_components", [])
    )

    return [
        track
        for component, track
        in PRIMARY_TRACK_COMPONENTS.items()
        if component in applicable_components
    ]


def _communication_track(applicable_tracks):
    if not applicable_tracks:
        return None

    if len(applicable_tracks) > 1:
        return "combined"

    return applicable_tracks[0]


def _preflight_issues(
    profile,
    resolved_email,
    applicable_tracks,
):
    issues = []

    if not resolved_email.get("email"):
        issues.append(
            {
                "code": "MISSING_EMAIL",
                "message": (
                    "No employee email address is configured."
                ),
            }
        )

    if not applicable_tracks:
        issues.append(
            {
                "code": "NO_APPLICABLE_LICENSE_TRACK",
                "message": (
                    "No supported Peace Officer, County "
                    "Jailer, or Telecommunicator compliance "
                    "track applies to this employee."
                ),
            }
        )

    if profile["overall_status"] == "NOT_EVALUATED":
        issues.append(
            {
                "code": "NOT_EVALUATED",
                "message": (
                    "The employee does not currently have "
                    "an evaluated compliance status."
                ),
            }
        )

    return issues


def _build_recipient(
    officer,
    evaluation_date,
):
    profile = evaluate_officer_compliance_profile(
        officer,
        evaluation_date=evaluation_date,
    )

    resolved_email = resolve_officer_email(
        officer
    )

    applicable_tracks = _applicable_tracks(
        profile
    )

    communication_track = _communication_track(
        applicable_tracks
    )

    issues = _preflight_issues(
        profile,
        resolved_email,
        applicable_tracks,
    )

    preflight_status = (
        "ACTION_REQUIRED"
        if issues
        else "READY"
    )

    selected_by_default = (
        preflight_status == "READY"
        and profile["overall_status"]
        in DEFAULT_SELECTED_STATUSES
    )

    return {
        "officer_id": str(officer.id),
        "agency_id": str(officer.agency_id),
        "tcole_pid": officer.tcole_pid,
        "employee_name": _employee_name(officer),
        "first_name": officer.first_name,
        "middle_name": officer.middle_name,
        "last_name": officer.last_name,
        "suffix": officer.suffix,
        "overall_status":
            profile["overall_status"],
        "evaluation_coverage":
            profile["evaluation_coverage"],
        "email": resolved_email.get("email"),
        "email_source":
            resolved_email.get("source"),
        "applicable_tracks": applicable_tracks,
        "communication_track":
            communication_track,
        "overdue_count":
            profile["overdue_count"],
        "outstanding_count":
            profile["outstanding_count"],
        "pending_review_count":
            profile["pending_review_count"],
        "next_due_date":
            profile["next_due_date"],
        "preflight_status":
            preflight_status,
        "preflight_issues":
            issues,
        "selected_by_default":
            selected_by_default,
    }


def build_bulk_compliance_preflight(
    agency_id,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    agency = Agency.query.filter_by(
        id=agency_id
    ).one_or_none()

    if agency is None:
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

    recipients = [
        _build_recipient(
            officer,
            evaluation_date,
        )
        for officer in officers
    ]

    ready = [
        recipient
        for recipient in recipients
        if recipient["preflight_status"]
        == "READY"
    ]

    action_required = [
        recipient
        for recipient in recipients
        if recipient["preflight_status"]
        == "ACTION_REQUIRED"
    ]

    selected_by_default = [
        recipient
        for recipient in recipients
        if recipient["selected_by_default"]
    ]

    summary = {
        "total_employees":
            len(recipients),
        "eligible_recipients":
            len(ready),
        "action_required":
            len(action_required),
        "selected_by_default":
            len(selected_by_default),
        "peace_officer": sum(
            "peace_officer"
            in recipient["applicable_tracks"]
            for recipient in recipients
        ),
        "county_jailer": sum(
            "jailer"
            in recipient["applicable_tracks"]
            for recipient in recipients
        ),
        "telecommunicator": sum(
            "telecommunicator"
            in recipient["applicable_tracks"]
            for recipient in recipients
        ),
        "multi_license": sum(
            len(recipient["applicable_tracks"]) > 1
            for recipient in recipients
        ),
    }

    return {
        "agency": {
            "id": str(agency.id),
            "name": agency.name,
        },
        "evaluation_date":
            evaluation_date.isoformat(),
        "summary": summary,
        "recipients": recipients,
    }
