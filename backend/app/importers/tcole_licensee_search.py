import csv
import io
from datetime import datetime

from app.extensions import db
from app.models import Officer


REQUIRED_COLUMNS = {
    "P_ID",
    "LNAME",
    "FNAME",
    "MNAME",
    "SFX",
    "RecordDesc",
    "RecordName",
    "RecordDate",
}


SUPPORTED_LICENSES = {
    "Peace Officer License": {
        "kind": "PEACE_OFFICER",
        "field": "peace_officer_service_start_date",
    },
    "Jailer License": {
        "kind": "JAILER",
        "field": "jailer_service_start_date",
    },
    "County Jailer License": {
        "kind": "JAILER",
        "field": "jailer_service_start_date",
    },
}


class LicenseeSearchImportError(ValueError):
    pass


def _decode_csv(content):
    if isinstance(content, bytes):
        return content.decode("utf-8-sig")

    return content


def _parse_date(
    value,
    row_number,
    record_name,
):
    value = (value or "").strip()

    if not value:
        raise LicenseeSearchImportError(
            f"Row {row_number}: {record_name} "
            "record does not contain a RecordDate."
        )

    try:
        return datetime.strptime(
            value,
            "%m/%d/%Y",
        ).date()
    except ValueError as exc:
        raise LicenseeSearchImportError(
            f"Row {row_number}: invalid RecordDate "
            f"{value!r}."
        ) from exc


def import_licensee_search(
    agency_id,
    content,
    commit=True,
):
    text = _decode_csv(content)

    reader = csv.DictReader(
        io.StringIO(text)
    )

    fieldnames = set(reader.fieldnames or [])

    missing_columns = (
        REQUIRED_COLUMNS - fieldnames
    )

    if missing_columns:
        missing = ", ".join(
            sorted(missing_columns)
        )

        raise LicenseeSearchImportError(
            "Department Licensee Search Report "
            f"is missing required columns: {missing}."
        )

    rows_processed = 0
    supported_license_rows = 0

    peace_officer_license_rows = 0
    service_dates_populated = 0
    service_dates_updated = 0
    service_dates_unchanged = 0

    jailer_license_rows = 0
    jailer_service_dates_populated = 0
    jailer_service_dates_updated = 0
    jailer_service_dates_unchanged = 0

    unmatched_license_rows = 0

    # Keyed by logical license kind plus PID so aliases such
    # as Jailer License / County Jailer License cannot create
    # duplicate service-date records for one employee.
    seen_license_records = set()

    for row_number, row in enumerate(
        reader,
        start=2,
    ):
        rows_processed += 1

        record_desc = (
            row.get("RecordDesc") or ""
        ).strip()

        record_name = (
            row.get("RecordName") or ""
        ).strip()

        if record_desc != "License":
            continue

        license_definition = (
            SUPPORTED_LICENSES.get(record_name)
        )

        if license_definition is None:
            continue

        supported_license_rows += 1

        license_kind = license_definition["kind"]
        field_name = license_definition["field"]

        if license_kind == "PEACE_OFFICER":
            peace_officer_license_rows += 1
        elif license_kind == "JAILER":
            jailer_license_rows += 1

        tcole_pid = (
            row.get("P_ID") or ""
        ).strip()

        if not tcole_pid:
            raise LicenseeSearchImportError(
                f"Row {row_number}: {record_name} "
                "record has no P_ID."
            )

        seen_key = (
            license_kind,
            tcole_pid,
        )

        if seen_key in seen_license_records:
            raise LicenseeSearchImportError(
                "Department Licensee Search Report "
                "contains more than one "
                f"{license_kind.replace('_', ' ').title()} "
                f"license record for P_ID {tcole_pid}."
            )

        seen_license_records.add(seen_key)

        license_date = _parse_date(
            row.get("RecordDate"),
            row_number,
            record_name,
        )

        officer = Officer.query.filter_by(
            agency_id=agency_id,
            tcole_pid=tcole_pid,
        ).one_or_none()

        if officer is None:
            unmatched_license_rows += 1
            continue

        existing_date = getattr(
            officer,
            field_name,
        )

        if existing_date is None:
            setattr(
                officer,
                field_name,
                license_date,
            )

            if license_kind == "PEACE_OFFICER":
                service_dates_populated += 1
            else:
                jailer_service_dates_populated += 1

        elif existing_date == license_date:
            if license_kind == "PEACE_OFFICER":
                service_dates_unchanged += 1
            else:
                jailer_service_dates_unchanged += 1

        else:
            # TCOLE is authoritative for imported
            # license/service dates.
            setattr(
                officer,
                field_name,
                license_date,
            )

            if license_kind == "PEACE_OFFICER":
                service_dates_updated += 1
            else:
                jailer_service_dates_updated += 1

    if supported_license_rows == 0:
        raise LicenseeSearchImportError(
            "No supported license records were found "
            "in the Department Licensee Search Report."
        )

    if commit:
        db.session.commit()

    return {
        "rows_processed": rows_processed,
        "supported_license_rows":
            supported_license_rows,
        "peace_officer_license_rows":
            peace_officer_license_rows,
        "service_dates_populated":
            service_dates_populated,
        "service_dates_updated":
            service_dates_updated,
        "service_dates_unchanged":
            service_dates_unchanged,
        "jailer_license_rows":
            jailer_license_rows,
        "jailer_service_dates_populated":
            jailer_service_dates_populated,
        "jailer_service_dates_updated":
            jailer_service_dates_updated,
        "jailer_service_dates_unchanged":
            jailer_service_dates_unchanged,
        "unmatched_license_rows":
            unmatched_license_rows,
    }
