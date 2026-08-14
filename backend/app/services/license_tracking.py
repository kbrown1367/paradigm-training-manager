# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

from datetime import datetime, timezone

from app.compliance.county_jailer import (
    has_county_jailer_license,
)
from app.compliance.peace_officer_unit import (
    has_peace_officer_license,
)
from app.compliance.telecommunicator_proficiency import (
    has_telecommunicator_license,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerLicenseTracking,
)


LICENSE_TYPES = {
    "PEACE_OFFICER": "Peace Officer",
    "COUNTY_JAILER": "County Jailer",
    "TELECOMMUNICATOR": "Telecommunicator",
}


class LicenseTrackingError(ValueError):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


def get_officer_for_agency(agency_id, officer_id):
    agency = db.session.get(Agency, agency_id)

    if agency is None:
        raise LicenseTrackingError(
            "Agency does not exist."
        )

    officer = Officer.query.filter_by(
        id=officer_id,
        agency_id=agency_id,
    ).one_or_none()

    if officer is None:
        raise LicenseTrackingError(
            "Employee does not exist for this agency."
        )

    return officer


def detected_license_types(officer):
    licenses = []

    if has_peace_officer_license(officer):
        licenses.append("PEACE_OFFICER")

    if has_county_jailer_license(officer):
        licenses.append("COUNTY_JAILER")

    if has_telecommunicator_license(officer):
        licenses.append("TELECOMMUNICATOR")

    return licenses


def _tracking_record(officer, license_type):
    return OfficerLicenseTracking.query.filter_by(
        agency_id=officer.agency_id,
        officer_id=officer.id,
        license_type=license_type,
    ).one_or_none()


def is_license_tracking_enabled(
    officer,
    license_type,
):
    record = _tracking_record(
        officer,
        license_type,
    )

    if record is None:
        return True

    return bool(record.tracking_enabled)


def serialize_license_tracking(officer):
    detected = detected_license_types(officer)

    items = []

    for license_type in detected:
        record = _tracking_record(
            officer,
            license_type,
        )

        tracking_enabled = (
            True
            if record is None
            else bool(record.tracking_enabled)
        )

        items.append(
            {
                "license_type": license_type,
                "license_name":
                    LICENSE_TYPES[license_type],
                "tracking_enabled":
                    tracking_enabled,
                "last_disabled_at": (
                    record.last_disabled_at.isoformat()
                    if (
                        record is not None
                        and record.last_disabled_at
                    )
                    else None
                ),
                "last_disabled_by": (
                    record.last_disabled_by
                    if record is not None
                    else None
                ),
                "last_disabled_reason": (
                    record.last_disabled_reason
                    if record is not None
                    else None
                ),
                "updated_at": (
                    record.updated_at.isoformat()
                    if (
                        record is not None
                        and record.updated_at
                    )
                    else None
                ),
                "updated_by": (
                    record.updated_by
                    if record is not None
                    else None
                ),
            }
        )

    return items


def set_license_tracking(
    agency_id,
    officer_id,
    license_type,
    tracking_enabled,
    changed_by=None,
    reason=None,
):
    officer = get_officer_for_agency(
        agency_id,
        officer_id,
    )

    license_type = (
        license_type or ""
    ).strip().upper()

    if license_type not in LICENSE_TYPES:
        raise LicenseTrackingError(
            "License type is invalid."
        )

    detected = detected_license_types(officer)

    if license_type not in detected:
        raise LicenseTrackingError(
            "That license is not present on this "
            "employee's TCOLE record."
        )

    if len(detected) <= 1:
        raise LicenseTrackingError(
            "Compliance tracking can only be changed "
            "for employees with multiple license types."
        )

    if not isinstance(tracking_enabled, bool):
        raise LicenseTrackingError(
            "tracking_enabled must be true or false."
        )

    current_states = {
        item: is_license_tracking_enabled(
            officer,
            item,
        )
        for item in detected
    }

    current_states[license_type] = tracking_enabled

    if not any(current_states.values()):
        raise LicenseTrackingError(
            "At least one license must remain tracked "
            "for an active employee."
        )

    record = _tracking_record(
        officer,
        license_type,
    )

    if record is None:
        record = OfficerLicenseTracking(
            agency_id=agency_id,
            officer_id=officer.id,
            license_type=license_type,
            tracking_enabled=True,
        )
        db.session.add(record)

    record.tracking_enabled = tracking_enabled
    record.updated_at = _utcnow()
    record.updated_by = (
        (changed_by or "").strip() or None
    )

    if not tracking_enabled:
        record.last_disabled_at = _utcnow()
        record.last_disabled_by = (
            (changed_by or "").strip() or None
        )
        record.last_disabled_reason = (
            (reason or "").strip() or None
        )

    db.session.commit()

    return serialize_license_tracking(officer)
