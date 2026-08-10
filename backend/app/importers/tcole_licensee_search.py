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


class LicenseeSearchImportError(ValueError):
    pass


def _decode_csv(content):
    if isinstance(content, bytes):
        return content.decode("utf-8-sig")

    return content


def _parse_date(value, row_number):
    value = (value or "").strip()

    if not value:
        raise LicenseeSearchImportError(
            f"Row {row_number}: Peace Officer License "
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
    peace_officer_license_rows = 0
    service_dates_populated = 0
    service_dates_updated = 0
    service_dates_unchanged = 0
    unmatched_license_rows = 0

    seen_pids = set()

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

        if (
            record_desc != "License"
            or record_name
            != "Peace Officer License"
        ):
            continue

        peace_officer_license_rows += 1

        tcole_pid = (
            row.get("P_ID") or ""
        ).strip()

        if not tcole_pid:
            raise LicenseeSearchImportError(
                f"Row {row_number}: Peace Officer "
                "License record has no P_ID."
            )

        if tcole_pid in seen_pids:
            raise LicenseeSearchImportError(
                "Department Licensee Search Report "
                "contains more than one Peace Officer "
                f"License record for P_ID {tcole_pid}."
            )

        seen_pids.add(tcole_pid)

        license_date = _parse_date(
            row.get("RecordDate"),
            row_number,
        )

        officer = Officer.query.filter_by(
            agency_id=agency_id,
            tcole_pid=tcole_pid,
        ).one_or_none()

        if officer is None:
            unmatched_license_rows += 1
            continue

        existing_date = (
            officer.peace_officer_service_start_date
        )

        if existing_date is None:
            officer.peace_officer_service_start_date = (
                license_date
            )
            service_dates_populated += 1

        elif existing_date == license_date:
            service_dates_unchanged += 1

        else:
            # TCOLE is authoritative for this field.
            officer.peace_officer_service_start_date = (
                license_date
            )
            service_dates_updated += 1

    if peace_officer_license_rows == 0:
        raise LicenseeSearchImportError(
            "No Peace Officer License records were "
            "found in the Department Licensee Search "
            "Report."
        )

    if commit:
        db.session.commit()

    return {
        "rows_processed": rows_processed,
        "peace_officer_license_rows":
            peace_officer_license_rows,
        "service_dates_populated":
            service_dates_populated,
        "service_dates_updated":
            service_dates_updated,
        "service_dates_unchanged":
            service_dates_unchanged,
        "unmatched_license_rows":
            unmatched_license_rows,
    }
