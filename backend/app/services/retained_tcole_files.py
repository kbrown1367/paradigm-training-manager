# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import hashlib
from datetime import timedelta
from uuid import UUID

from app.extensions import db
from app.models import (
    RetainedTcoleFile,
    utcnow,
)


RETENTION_DAYS = 90

FILE_TYPE_AWARDS = "awards"
FILE_TYPE_COURSES = "courses"
FILE_TYPE_CYCLE = "cycle"
FILE_TYPE_LICENSEE_SEARCH = "licensee_search"

FILE_TYPES = {
    FILE_TYPE_AWARDS,
    FILE_TYPE_COURSES,
    FILE_TYPE_CYCLE,
    FILE_TYPE_LICENSEE_SEARCH,
}


def retain_tcole_file(
    *,
    agency_id,
    import_job_id,
    file_type,
    filename,
    content,
    content_type="text/csv",
):
    """
    Retain the exact bytes from a successfully imported TCOLE
    source file.

    Only one current file of each type is retained per agency.
    Replacement occurs only when this function is called after
    the corresponding import stage succeeds.
    """
    if file_type not in FILE_TYPES:
        raise ValueError(
            f"Unsupported TCOLE file type: {file_type}"
        )

    if not isinstance(content, bytes):
        raise ValueError(
            "Retained TCOLE file content must be bytes."
        )

    try:
        normalized_import_job_id = (
            import_job_id
            if isinstance(import_job_id, UUID)
            else UUID(str(import_job_id))
        )
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(
            "Retained TCOLE file import_job_id "
            "must be a valid UUID."
        ) from exc

    now = utcnow()

    retained = (
        RetainedTcoleFile.query
        .filter_by(
            agency_id=agency_id,
            file_type=file_type,
        )
        .one_or_none()
    )

    if retained is None:
        retained = RetainedTcoleFile(
            agency_id=agency_id,
            file_type=file_type,
        )
        db.session.add(retained)

    retained.import_job_id = normalized_import_job_id
    retained.original_filename = filename
    retained.content_type = (
        content_type or "text/csv"
    )
    retained.content = content
    retained.size_bytes = len(content)
    retained.sha256 = hashlib.sha256(
        content
    ).hexdigest()
    retained.uploaded_at = now
    retained.expires_at = (
        now + timedelta(days=RETENTION_DAYS)
    )

    db.session.flush()

    return retained


def purge_expired_tcole_files(*, as_of=None):
    """
    Delete retained source bytes whose 90-day retention period
    has expired.

    ImportJob and AuditEvent history are intentionally untouched.
    """
    cutoff = as_of or utcnow()

    expired = (
        RetainedTcoleFile.query
        .filter(
            RetainedTcoleFile.expires_at <= cutoff
        )
        .all()
    )

    count = len(expired)

    for retained in expired:
        db.session.delete(retained)

    db.session.flush()

    return count
