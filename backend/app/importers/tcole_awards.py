import csv
import io
from datetime import datetime

from app.extensions import db
from app.models import Officer, OfficerAward


REQUIRED_COLUMNS = {
    "P_ID1",
    "OFFICER_NAME1",
    "Type1",
    "Award",
    "Date",
}


class AwardsImportError(ValueError):
    pass


def parse_officer_name(value):
    value = (value or "").strip()

    if not value:
        raise AwardsImportError("Officer name is missing.")

    if "," not in value:
        raise AwardsImportError(
            f"Officer name is not in expected LAST, FIRST format: {value}"
        )

    last_name, given_names = value.split(",", 1)

    last_name = last_name.strip()
    given_names = given_names.strip()

    parts = given_names.split()

    if not last_name or not parts:
        raise AwardsImportError(
            f"Officer name is incomplete: {value}"
        )

    return {
        "first_name": parts[0],
        "middle_name": " ".join(parts[1:]) if len(parts) > 1 else None,
        "last_name": last_name,
    }


def parse_award_date(value, row_number):
    value = (value or "").strip()

    if not value:
        raise AwardsImportError(
            f"Row {row_number}: award date is missing."
        )

    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError as exc:
        raise AwardsImportError(
            f"Row {row_number}: invalid award date '{value}'."
        ) from exc


def import_awards_roster(agency_id, csv_content, commit=True):
    if isinstance(csv_content, bytes):
        csv_content = csv_content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(csv_content))

    if reader.fieldnames is None:
        raise AwardsImportError("The awards file is empty.")

    actual_columns = {
        column.strip()
        for column in reader.fieldnames
        if column is not None
    }

    missing_columns = REQUIRED_COLUMNS - actual_columns

    if missing_columns:
        raise AwardsImportError(
            "Invalid TCOLE awards file. Missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    rows_processed = 0
    officers_created = 0
    officers_updated = 0
    awards_created = 0
    awards_skipped = 0

    officers_by_pid = {}
    seen_awards = set()

    try:
        for row_number, row in enumerate(reader, start=2):
            pid = (row.get("P_ID1") or "").strip()
            officer_name = (row.get("OFFICER_NAME1") or "").strip()
            award_type = (row.get("Type1") or "").strip()
            award_name = (row.get("Award") or "").strip()

            if not pid:
                raise AwardsImportError(
                    f"Row {row_number}: TCOLE PID is missing."
                )

            if not officer_name:
                raise AwardsImportError(
                    f"Row {row_number}: officer name is missing."
                )

            if award_type not in {"Certificate", "License"}:
                raise AwardsImportError(
                    f"Row {row_number}: unsupported award type '{award_type}'."
                )

            if not award_name:
                raise AwardsImportError(
                    f"Row {row_number}: award name is missing."
                )

            award_date = parse_award_date(
                row.get("Date"),
                row_number,
            )

            rows_processed += 1

            officer = officers_by_pid.get(pid)

            if officer is None:
                name = parse_officer_name(officer_name)

                officer = Officer.query.filter_by(
                    agency_id=agency_id,
                    tcole_pid=pid,
                ).one_or_none()

                if officer is None:
                    officer = Officer(
                        agency_id=agency_id,
                        tcole_pid=pid,
                        first_name=name["first_name"],
                        middle_name=name["middle_name"],
                        last_name=name["last_name"],
                    )
                    db.session.add(officer)
                    db.session.flush()
                    officers_created += 1
                else:
                    officer.first_name = name["first_name"]
                    officer.middle_name = name["middle_name"]
                    officer.last_name = name["last_name"]
                    officers_updated += 1

                officers_by_pid[pid] = officer

            award_key = (
                officer.id,
                award_type,
                award_name,
                award_date,
            )

            if award_key in seen_awards:
                awards_skipped += 1
                continue

            seen_awards.add(award_key)

            existing_award = OfficerAward.query.filter_by(
                agency_id=agency_id,
                officer_id=officer.id,
                award_type=award_type,
                award_name=award_name,
                award_date=award_date,
            ).one_or_none()

            if existing_award is not None:
                awards_skipped += 1
                continue

            db.session.add(
                OfficerAward(
                    agency_id=agency_id,
                    officer_id=officer.id,
                    award_type=award_type,
                    award_name=award_name,
                    award_date=award_date,
                )
            )

            awards_created += 1

        if commit:
            db.session.commit()

    except Exception:
        if commit:
            db.session.rollback()
        raise

    return {
        "rows_processed": rows_processed,
        "unique_officers": len(officers_by_pid),
        "officers_created": officers_created,
        "officers_updated": officers_updated,
        "awards_created": awards_created,
        "awards_skipped": awards_skipped,
    }
