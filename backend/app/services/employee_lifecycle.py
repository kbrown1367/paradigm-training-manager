# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

from datetime import datetime, timezone

from app.extensions import db
from app.models import Officer


class EmployeeLifecycleError(Exception):
    pass


def get_agency_officer(
    agency_id,
    officer_id,
):
    return Officer.query.filter_by(
        id=officer_id,
        agency_id=agency_id,
    ).one_or_none()


def serialize_lifecycle(officer):
    return {
        "id": str(officer.id),
        "agency_id": str(officer.agency_id),
        "tcole_pid": officer.tcole_pid,
        "first_name": officer.first_name,
        "middle_name": officer.middle_name,
        "last_name": officer.last_name,
        "suffix": officer.suffix,
        "employment_status":
            officer.employment_status,
        "archived_at": (
            officer.archived_at.isoformat()
            if officer.archived_at
            else None
        ),
        "archived_reason":
            officer.archived_reason,
    }


def archive_employee(
    agency_id,
    officer_id,
    reason=None,
):
    officer = get_agency_officer(
        agency_id,
        officer_id,
    )

    if officer is None:
        return None

    if officer.employment_status == "archived":
        raise EmployeeLifecycleError(
            "Employee is already archived."
        )

    clean_reason = None

    if reason is not None:
        clean_reason = str(reason).strip() or None

    if (
        clean_reason is not None
        and len(clean_reason) > 500
    ):
        raise EmployeeLifecycleError(
            "Archive reason must be 500 characters or fewer."
        )

    officer.employment_status = "archived"
    officer.archived_at = datetime.now(
        timezone.utc
    )
    officer.archived_reason = clean_reason

    db.session.commit()

    return serialize_lifecycle(officer)


def restore_employee(
    agency_id,
    officer_id,
):
    officer = get_agency_officer(
        agency_id,
        officer_id,
    )

    if officer is None:
        return None

    if officer.employment_status != "archived":
        raise EmployeeLifecycleError(
            "Employee is already active."
        )

    officer.employment_status = "active"
    officer.archived_at = None
    officer.archived_reason = None

    db.session.commit()

    return serialize_lifecycle(officer)
