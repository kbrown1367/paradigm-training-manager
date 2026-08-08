import csv
import io

from app.extensions import db
from app.models import Officer


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

    first_name = parts[0]
    middle_name = " ".join(parts[1:]) if len(parts) > 1 else None

    return {
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
    }


def import_awards_roster(agency_id, csv_content):
    if isinstance(csv_content, bytes):
        csv_content = csv_content.decode("utf-8-sig")

    stream = io.StringIO(csv_content)
    reader = csv.DictReader(stream)

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
    created = 0
    updated = 0
    seen_pids = set()

    for row_number, row in enumerate(reader, start=2):
        pid = (row.get("P_ID1") or "").strip()
        officer_name = (row.get("OFFICER_NAME1") or "").strip()

        if not pid:
            raise AwardsImportError(
                f"Row {row_number}: TCOLE PID is missing."
            )

        if not officer_name:
            raise AwardsImportError(
                f"Row {row_number}: officer name is missing."
            )

        rows_processed += 1

        if pid in seen_pids:
            continue

        seen_pids.add(pid)

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
            created += 1
        else:
            officer.first_name = name["first_name"]
            officer.middle_name = name["middle_name"]
            officer.last_name = name["last_name"]
            updated += 1

    db.session.commit()

    return {
        "rows_processed": rows_processed,
        "unique_officers": len(seen_pids),
        "officers_created": created,
        "officers_updated": updated,
    }
