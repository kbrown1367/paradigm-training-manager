# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

from datetime import datetime, timezone

from flask import request

from app.extensions import db
from app.models import AuditEvent


def _request_ip_address():
    forwarded_for = request.headers.get(
        "X-Forwarded-For",
        "",
    )

    if forwarded_for:
        return (
            forwarded_for.split(",", 1)[0].strip()
            or None
        )

    return request.remote_addr


def _request_user_agent():
    value = request.headers.get(
        "User-Agent"
    )

    if not value:
        return None

    return value[:500]


def record_audit_event(
    *,
    agency_id,
    user_id,
    event_type,
    object_type=None,
    object_id=None,
    result="success",
    details=None,
    capture_request=True,
):
    event = AuditEvent(
        agency_id=agency_id,
        user_id=user_id,
        event_type=event_type,
        object_type=object_type,
        object_id=(
            str(object_id)
            if object_id is not None
            else None
        ),
        result=result,
        details=details,
        ip_address=(
            _request_ip_address()
            if capture_request
            else None
        ),
        user_agent=(
            _request_user_agent()
            if capture_request
            else None
        ),
        created_at=datetime.now(
            timezone.utc
        ),
    )

    db.session.add(event)

    return event
