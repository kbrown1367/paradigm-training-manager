from datetime import datetime

from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerCredentialVerification,
    utcnow,
)


CREDENTIAL_TYPES = {
    "TDEM_PIO_CERTIFICATION":
        "TDEM Public Information Officer Certification",
}


class CredentialVerificationError(ValueError):
    pass


def parse_date(value, field_name, required=False):
    value = (value or "").strip()

    if not value:
        if required:
            raise CredentialVerificationError(
                f"{field_name} is required."
            )
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()
    except ValueError as exc:
        raise CredentialVerificationError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from exc


def get_officer(agency_id, officer_id):
    agency = db.session.get(
        Agency,
        agency_id,
    )

    if agency is None:
        raise CredentialVerificationError(
            "Agency does not exist."
        )

    officer = Officer.query.filter_by(
        id=officer_id,
        agency_id=agency_id,
    ).one_or_none()

    if officer is None:
        raise CredentialVerificationError(
            "Officer does not exist for this agency."
        )

    return officer


def serialize_verification(record):
    return {
        "id": str(record.id),
        "credential_type":
            record.credential_type,
        "credential_name":
            CREDENTIAL_TYPES.get(
                record.credential_type,
                record.credential_type,
            ),
        "status": record.status,
        "effective_date": (
            record.effective_date.isoformat()
            if record.effective_date
            else None
        ),
        "verified_at": (
            record.verified_at.isoformat()
            if record.verified_at
            else None
        ),
        "verified_by": record.verified_by,
        "reference": record.reference,
        "notes": record.notes,
        "revoked_at": (
            record.revoked_at.isoformat()
            if record.revoked_at
            else None
        ),
        "active": (
            record.status == "VERIFIED"
            and record.revoked_at is None
        ),
    }


def get_active_verification(
    agency_id,
    officer_id,
    credential_type,
):
    get_officer(
        agency_id,
        officer_id,
    )

    return (
        OfficerCredentialVerification.query
        .filter_by(
            agency_id=agency_id,
            officer_id=officer_id,
            credential_type=credential_type,
            status="VERIFIED",
            revoked_at=None,
        )
        .order_by(
            OfficerCredentialVerification.verified_at.desc()
        )
        .first()
    )


def verify_credential(
    agency_id,
    officer_id,
    credential_type,
    effective_date=None,
    verified_by=None,
    reference=None,
    notes=None,
):
    get_officer(
        agency_id,
        officer_id,
    )

    credential_type = (
        credential_type or ""
    ).strip().upper()

    if credential_type not in CREDENTIAL_TYPES:
        raise CredentialVerificationError(
            "Credential type is invalid."
        )

    existing = get_active_verification(
        agency_id,
        officer_id,
        credential_type,
    )

    if existing is not None:
        raise CredentialVerificationError(
            "This credential is already verified."
        )

    record = OfficerCredentialVerification(
        agency_id=agency_id,
        officer_id=officer_id,
        credential_type=credential_type,
        status="VERIFIED",
        effective_date=parse_date(
            effective_date,
            "effective_date",
        ),
        verified_by=(
            (verified_by or "").strip() or None
        ),
        reference=(
            (reference or "").strip() or None
        ),
        notes=(
            (notes or "").strip() or None
        ),
    )

    db.session.add(record)
    db.session.commit()

    return serialize_verification(record)


def revoke_verification(
    agency_id,
    officer_id,
    credential_type,
):
    record = get_active_verification(
        agency_id,
        officer_id,
        credential_type,
    )

    if record is None:
        raise CredentialVerificationError(
            "No active verification exists."
        )

    record.status = "REVOKED"
    record.revoked_at = utcnow()

    db.session.commit()

    return serialize_verification(record)


def list_verifications(
    agency_id,
    officer_id,
):
    get_officer(
        agency_id,
        officer_id,
    )

    records = (
        OfficerCredentialVerification.query
        .filter_by(
            agency_id=agency_id,
            officer_id=officer_id,
        )
        .order_by(
            OfficerCredentialVerification.verified_at.desc()
        )
        .all()
    )

    return [
        serialize_verification(record)
        for record in records
    ]
