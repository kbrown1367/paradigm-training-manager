# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import UUID

from flask import (
    Blueprint,
    jsonify,
    request,
    send_file,
)

from app.auth import (
    ROLE_AGENCY_ADMIN,
    generate_invitation_token,
    get_session_user,
    hash_password,
    invitation_expiration,
    normalize_login_email,
    user_is_platform_admin,
)
from app.extensions import db
from app.services.audit_log import (
    record_audit_event,
)
from app.services.retained_tcole_files import (
    FILE_TYPES,
    purge_expired_tcole_files,
)
from app.models import (
    Agency,
    AuditEvent,
    ImportJob,
    Officer,
    OfficerAssignment,
    OfficerAward,
    OfficerCredentialVerification,
    OfficerLicenseTracking,
    RetainedTcoleFile,
    TrainingCredit,
    TrainingRecord,
    User,
)


platform_api = Blueprint(
    "platform_api",
    __name__,
)


AGENCY_PURGE_MODELS = (
    AuditEvent,
    TrainingCredit,
    TrainingRecord,
    OfficerAssignment,
    OfficerAward,
    OfficerCredentialVerification,
    OfficerLicenseTracking,
    RetainedTcoleFile,
    ImportJob,
    Officer,
    User,
)


def platform_error(
    message,
    status_code,
):
    return jsonify(
        {
            "error": message,
        }
    ), status_code


@platform_api.before_request
def require_platform_admin():
    user = get_session_user()

    if user is None:
        return platform_error(
            "Authentication required.",
            401,
        )

    if not user_is_platform_admin(user):
        return platform_error(
            "Resource not found.",
            404,
        )

    return None


def serialize_platform_user(user):
    return {
        "id": str(user.id),
        "agency_id": (
            str(user.agency_id)
            if user.agency_id is not None
            else None
        ),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "status": user.status,
        "invitation_created_at": (
            user.invitation_created_at.isoformat()
            if user.invitation_created_at
            else None
        ),
        "invitation_expires_at": (
            user.invitation_expires_at.isoformat()
            if user.invitation_expires_at
            else None
        ),
        "last_login_at": (
            user.last_login_at.isoformat()
            if user.last_login_at
            else None
        ),
        "created_at": (
            user.created_at.isoformat()
            if user.created_at
            else None
        ),
    }


def serialize_platform_agency(
    agency,
    include_users=False,
):
    active_employee_count = (
        Officer.query.filter_by(
            agency_id=agency.id,
            employment_status="active",
        ).count()
    )

    archived_employee_count = (
        Officer.query.filter_by(
            agency_id=agency.id,
            employment_status="archived",
        ).count()
    )

    agency_admins = (
        User.query.filter_by(
            agency_id=agency.id,
            role=ROLE_AGENCY_ADMIN,
        )
        .order_by(
            User.last_name,
            User.first_name,
            User.email,
        )
        .all()
    )

    result = {
        "id": str(agency.id),
        "name": agency.name,
        "tcole_agency_number":
            agency.tcole_agency_number,
        "ori": agency.ori,
        "email_domain": agency.email_domain,
        "email_pattern": agency.email_pattern,
        "status": agency.status,
        "active_employee_count":
            active_employee_count,
        "archived_employee_count":
            archived_employee_count,
        "administrator_count":
            len(agency_admins),
        "active_administrator_count":
            sum(
                1
                for user in agency_admins
                if user.status == "active"
            ),
        "created_at": (
            agency.created_at.isoformat()
            if agency.created_at
            else None
        ),
        "updated_at": (
            agency.updated_at.isoformat()
            if agency.updated_at
            else None
        ),
    }

    if include_users:
        result["administrators"] = [
            serialize_platform_user(user)
            for user in agency_admins
        ]

    return result


def get_agency_or_none(
    agency_id,
):
    return Agency.query.filter_by(
        id=agency_id,
    ).one_or_none()


def get_agency_admin_or_none(
    agency_id,
    user_id,
):
    return User.query.filter_by(
        id=user_id,
        agency_id=agency_id,
        role=ROLE_AGENCY_ADMIN,
    ).one_or_none()


@platform_api.get("/agencies")
def platform_list_agencies():
    agencies = (
        Agency.query
        .order_by(Agency.name)
        .all()
    )

    return jsonify(
        [
            serialize_platform_agency(
                agency
            )
            for agency in agencies
        ]
    ), 200


@platform_api.post("/agencies")
def platform_create_agency():
    payload = request.get_json(
        silent=True
    ) or {}

    name = (
        payload.get("name") or ""
    ).strip()

    if not name:
        return platform_error(
            "Agency name is required.",
            400,
        )

    agency = Agency(
        name=name,
        tcole_agency_number=(
            payload.get(
                "tcole_agency_number"
            )
            or None
        ),
        ori=payload.get("ori") or None,
        email_domain=(
            payload.get("email_domain")
            or None
        ),
        email_pattern=(
            payload.get("email_pattern")
            or None
        ),
        status="active",
    )

    db.session.add(agency)
    db.session.commit()

    return jsonify(
        serialize_platform_agency(
            agency,
            include_users=True,
        )
    ), 201


@platform_api.get(
    "/agencies/<uuid:agency_id>"
)
def platform_get_agency(
    agency_id,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    return jsonify(
        serialize_platform_agency(
            agency,
            include_users=True,
        )
    ), 200


@platform_api.patch(
    "/agencies/<uuid:agency_id>"
)
def platform_update_agency(
    agency_id,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    payload = request.get_json(
        silent=True
    ) or {}

    if "name" in payload:
        name = (
            payload.get("name") or ""
        ).strip()

        if not name:
            return platform_error(
                "Agency name is required.",
                400,
            )

        agency.name = name

    for field in [
        "tcole_agency_number",
        "ori",
        "email_domain",
        "email_pattern",
    ]:
        if field in payload:
            value = payload.get(field)

            if isinstance(value, str):
                value = (
                    value.strip()
                    or None
                )

            setattr(
                agency,
                field,
                value,
            )

    if "status" in payload:
        status = payload.get(
            "status"
        )

        if status not in {
            "active",
            "inactive",
            "archived",
        }:
            return platform_error(
                "Agency status must be active, "
                "inactive, or archived.",
                400,
            )

        agency.status = status

    db.session.commit()

    return jsonify(
        serialize_platform_agency(
            agency,
            include_users=True,
        )
    ), 200


@platform_api.post(
    "/agencies/<uuid:agency_id>/archive"
)
def platform_archive_agency(
    agency_id,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    if agency.status == "archived":
        return jsonify(
            serialize_platform_agency(
                agency,
                include_users=True,
            )
        ), 200

    platform_user = get_session_user()

    agency.status = "archived"

    db.session.add(
        AuditEvent(
            agency_id=agency.id,
            user_id=platform_user.id,
            event_type="PLATFORM_AGENCY_ARCHIVED",
            object_type="AGENCY",
            object_id=str(agency.id),
            result="success",
            details={
                "agency_name": agency.name,
            },
            created_at=datetime.now(
                timezone.utc
            ),
        )
    )

    db.session.commit()

    return jsonify(
        serialize_platform_agency(
            agency,
            include_users=True,
        )
    ), 200


@platform_api.post(
    "/agencies/<uuid:agency_id>/restore"
)
def platform_restore_agency(
    agency_id,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    if agency.status == "active":
        return jsonify(
            serialize_platform_agency(
                agency,
                include_users=True,
            )
        ), 200

    platform_user = get_session_user()

    agency.status = "active"

    db.session.add(
        AuditEvent(
            agency_id=agency.id,
            user_id=platform_user.id,
            event_type="PLATFORM_AGENCY_RESTORED",
            object_type="AGENCY",
            object_id=str(agency.id),
            result="success",
            details={
                "agency_name": agency.name,
            },
            created_at=datetime.now(
                timezone.utc
            ),
        )
    )

    db.session.commit()

    return jsonify(
        serialize_platform_agency(
            agency,
            include_users=True,
        )
    ), 200


@platform_api.delete(
    "/agencies/<uuid:agency_id>"
)
def platform_delete_agency(
    agency_id,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    if agency.status == "active":
        return platform_error(
            "Agency must be archived before "
            "it can be permanently deleted.",
            409,
        )

    payload = request.get_json(
        silent=True
    ) or {}

    confirmation_name = (
        payload.get("confirmation_name")
        or ""
    ).strip()

    if confirmation_name != agency.name:
        return platform_error(
            "Confirmation name does not match "
            "the agency name.",
            400,
        )

    platform_user = get_session_user()
    deleted_agency_id = str(agency.id)
    deleted_agency_name = agency.name

    deleted_records = {}

    try:
        for model in AGENCY_PURGE_MODELS:
            deleted_records[
                model.__tablename__
            ] = (
                model.query.filter_by(
                    agency_id=agency.id
                ).delete(
                    synchronize_session=False
                )
            )

        db.session.delete(agency)
        db.session.flush()

        # Preserve evidence that Paradigm permanently
        # deleted a tenant. The deleted agency cannot be
        # referenced by FK after deletion, so the event is
        # platform-level. The deleted agency UUID is retained
        # in the event type.
        db.session.add(
            AuditEvent(
                agency_id=None,
                user_id=platform_user.id,
                event_type=(
                    "PLATFORM_AGENCY_DELETED:"
                    f"{deleted_agency_id}"
                ),
                created_at=datetime.now(
                    timezone.utc
                ),
            )
        )

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    return jsonify(
        {
            "deleted": True,
            "agency_id":
                deleted_agency_id,
            "agency_name":
                deleted_agency_name,
            "deleted_records":
                deleted_records,
        }
    ), 200


@platform_api.get(
    "/agencies/<uuid:agency_id>/administrators"
)
def platform_list_agency_administrators(
    agency_id,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    users = (
        User.query.filter_by(
            agency_id=agency.id,
            role=ROLE_AGENCY_ADMIN,
        )
        .order_by(
            User.last_name,
            User.first_name,
            User.email,
        )
        .all()
    )

    return jsonify(
        [
            serialize_platform_user(
                user
            )
            for user in users
        ]
    ), 200


@platform_api.post(
    "/agencies/<uuid:agency_id>/administrators"
)
def platform_create_agency_administrator(
    agency_id,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    payload = request.get_json(
        silent=True
    ) or {}

    first_name = (
        payload.get("first_name")
        or ""
    ).strip()

    last_name = (
        payload.get("last_name")
        or ""
    ).strip()

    email = normalize_login_email(
        payload.get("email")
    )

    if (
        not first_name
        or not last_name
        or not email
    ):
        return platform_error(
            "First name, last name, "
            "and email are required.",
            400,
        )

    existing = User.query.filter(
        db.func.lower(
            User.email
        ) == email
    ).one_or_none()

    if existing is not None:
        return platform_error(
            "A user with that email "
            "already exists.",
            409,
        )

    token, token_hash = (
        generate_invitation_token()
    )

    user = User(
        agency_id=agency.id,
        email=email,
        password_hash=None,
        invitation_token_hash=token_hash,
        invitation_created_at=db.func.now(),
        invitation_expires_at=(
            invitation_expiration()
        ),
        first_name=first_name,
        last_name=last_name,
        role=ROLE_AGENCY_ADMIN,
        status="pending_invitation",
    )

    db.session.add(user)
    db.session.commit()

    result = serialize_platform_user(
        user
    )

    result["invitation_path"] = (
        f"/activate?token={token}"
    )

    return jsonify(result), 201


@platform_api.post(
    "/agencies/<uuid:agency_id>"
    "/administrators/<uuid:user_id>"
    "/resend-invitation"
)
def platform_resend_agency_administrator_invitation(
    agency_id,
    user_id,
):
    user = get_agency_admin_or_none(
        agency_id,
        user_id,
    )

    if user is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    if user.status != "pending_invitation":
        return platform_error(
            "Only pending invitations may be regenerated.",
            400,
        )

    token, token_hash = (
        generate_invitation_token()
    )

    user.invitation_token_hash = (
        token_hash
    )

    user.invitation_created_at = (
        db.func.now()
    )

    user.invitation_expires_at = (
        invitation_expiration()
    )

    db.session.commit()

    result = serialize_platform_user(
        user
    )

    result["invitation_path"] = (
        f"/activate?token={token}"
    )

    return jsonify(result), 200


@platform_api.patch(
    "/agencies/<uuid:agency_id>"
    "/administrators/<uuid:user_id>"
)
def platform_update_agency_administrator(
    agency_id,
    user_id,
):
    user = get_agency_admin_or_none(
        agency_id,
        user_id,
    )

    if user is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    payload = request.get_json(
        silent=True
    ) or {}

    if "first_name" in payload:
        first_name = (
            payload.get("first_name")
            or ""
        ).strip()

        if not first_name:
            return platform_error(
                "First name is required.",
                400,
            )

        user.first_name = first_name

    if "last_name" in payload:
        last_name = (
            payload.get("last_name")
            or ""
        ).strip()

        if not last_name:
            return platform_error(
                "Last name is required.",
                400,
            )

        user.last_name = last_name

    if "email" in payload:
        email = normalize_login_email(
            payload.get("email")
        )

        if not email:
            return platform_error(
                "Email is required.",
                400,
            )

        existing = User.query.filter(
            db.func.lower(
                User.email
            ) == email,
            User.id != user.id,
        ).one_or_none()

        if existing is not None:
            return platform_error(
                "A user with that email "
                "already exists.",
                409,
            )

        user.email = email

    if "status" in payload:
        status = payload.get("status")

        if status not in {
            "active",
            "inactive",
        }:
            return platform_error(
                "User status must be "
                "active or inactive.",
                400,
            )

        user.status = status

    db.session.commit()

    return jsonify(
        serialize_platform_user(
            user
        )
    ), 200


@platform_api.post(
    "/agencies/<uuid:agency_id>"
    "/administrators/<uuid:user_id>"
    "/reset-password"
)
def platform_reset_agency_administrator_password(
    agency_id,
    user_id,
):
    user = get_agency_admin_or_none(
        agency_id,
        user_id,
    )

    if user is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    payload = request.get_json(
        silent=True
    ) or {}

    password = (
        payload.get("password")
        or ""
    )

    if len(password) < 12:
        return platform_error(
            "Password must be at least "
            "12 characters.",
            400,
        )

    user.password_hash = hash_password(
        password
    )

    db.session.commit()

    return jsonify(
        {
            "status": "password_reset",
            "user":
                serialize_platform_user(
                    user
                ),
        }
    ), 200

def serialize_retained_tcole_file(retained):
    return {
        "id": str(retained.id),
        "agency_id": str(retained.agency_id),
        "import_job_id": str(retained.import_job_id),
        "file_type": retained.file_type,
        "original_filename":
            retained.original_filename,
        "content_type": retained.content_type,
        "size_bytes": retained.size_bytes,
        "sha256": retained.sha256,
        "uploaded_at": (
            retained.uploaded_at.isoformat()
            if retained.uploaded_at
            else None
        ),
        "expires_at": (
            retained.expires_at.isoformat()
            if retained.expires_at
            else None
        ),
    }


@platform_api.get(
    "/agencies/<uuid:agency_id>/tcole-files"
)
def platform_list_retained_tcole_files(
    agency_id,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    purged = purge_expired_tcole_files()
    if purged:
        db.session.commit()

    retained_files = (
        RetainedTcoleFile.query
        .filter_by(
            agency_id=agency.id,
        )
        .order_by(
            RetainedTcoleFile.file_type
        )
        .all()
    )

    return jsonify(
        {
            "agency_id": str(agency.id),
            "agency_name": agency.name,
            "retention_days": 90,
            "files": [
                serialize_retained_tcole_file(
                    retained
                )
                for retained in retained_files
            ],
        }
    ), 200


@platform_api.get(
    "/agencies/<uuid:agency_id>/tcole-files/"
    "<file_type>/download"
)
def platform_download_retained_tcole_file(
    agency_id,
    file_type,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    if file_type not in FILE_TYPES:
        return platform_error(
            "Resource not found.",
            404,
        )

    purged = purge_expired_tcole_files()
    if purged:
        db.session.commit()

    retained = (
        RetainedTcoleFile.query
        .filter_by(
            agency_id=agency.id,
            file_type=file_type,
        )
        .one_or_none()
    )

    if retained is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    user = get_session_user()

    record_audit_event(
        agency_id=agency.id,
        user_id=(
            user.id
            if user is not None
            else None
        ),
        event_type="PLATFORM_TCOLE_FILE_DOWNLOADED",
        object_type="RETAINED_TCOLE_FILE",
        object_id=str(retained.id),
        result="success",
        details={
            "file_type": retained.file_type,
            "filename":
                retained.original_filename,
            "import_job_id":
                str(retained.import_job_id),
            "sha256": retained.sha256,
            "size_bytes":
                retained.size_bytes,
        },
    )

    db.session.commit()

    return send_file(
        BytesIO(retained.content),
        mimetype=retained.content_type,
        as_attachment=True,
        download_name=
            retained.original_filename,
    )


def serialize_activity_event(event):
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "result": event.result,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "details": event.details or {},
        "user": (
            serialize_platform_user(event.user)
            if event.user is not None
            else None
        ),
        "ip_address": event.ip_address,
        "user_agent": event.user_agent,
        "created_at": (
            event.created_at.isoformat()
            if event.created_at
            else None
        ),
    }


def login_activity_for_agency(
    agency_id,
    now=None,
):
    if now is None:
        now = datetime.now(timezone.utc)

    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    login_query = AuditEvent.query.filter_by(
        agency_id=agency_id,
        event_type="AUTH_LOGIN_SUCCESS",
    )

    last_event = (
        login_query
        .order_by(AuditEvent.created_at.desc())
        .first()
    )

    logins_7_days = login_query.filter(
        AuditEvent.created_at >= seven_days_ago
    ).count()

    logins_30_days = login_query.filter(
        AuditEvent.created_at >= thirty_days_ago
    ).count()

    active_admin_rows = (
        db.session.query(AuditEvent.user_id)
        .join(
            User,
            User.id == AuditEvent.user_id,
        )
        .filter(
            AuditEvent.agency_id == agency_id,
            AuditEvent.event_type
            == "AUTH_LOGIN_SUCCESS",
            AuditEvent.created_at
            >= thirty_days_ago,
            User.role == ROLE_AGENCY_ADMIN,
        )
        .distinct()
        .all()
    )

    return {
        "last_login_at": (
            last_event.created_at.isoformat()
            if last_event is not None
            and last_event.created_at
            else None
        ),
        "logins_7_days": logins_7_days,
        "logins_30_days": logins_30_days,
        "active_admins_30_days":
            len(active_admin_rows),
    }


@platform_api.get("/activity/agencies")
def platform_agency_activity():
    agencies = (
        Agency.query
        .order_by(Agency.name)
        .all()
    )

    result = []

    for agency in agencies:
        activity = login_activity_for_agency(
            agency.id
        )

        result.append(
            {
                "agency_id": str(agency.id),
                "agency_name": agency.name,
                "agency_status": agency.status,
                **activity,
            }
        )

    return jsonify(result), 200


@platform_api.get(
    "/agencies/<uuid:agency_id>/activity"
)
def platform_agency_login_activity(
    agency_id,
):
    agency = get_agency_or_none(
        agency_id
    )

    if agency is None:
        return platform_error(
            "Resource not found.",
            404,
        )

    activity = login_activity_for_agency(
        agency.id
    )

    recent_events = (
        AuditEvent.query
        .filter_by(
            agency_id=agency.id,
        )
        .order_by(
            AuditEvent.created_at.desc()
        )
        .limit(100)
        .all()
    )

    return jsonify(
        {
            "agency_id": str(agency.id),
            "agency_name": agency.name,
            **activity,
            "recent_activity": [
                serialize_activity_event(event)
                for event in recent_events
            ],
        }
    ), 200
