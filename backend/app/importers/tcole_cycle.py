import csv
import io
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models import Officer, TrainingCredit, TrainingRecord


REQUIRED_COLUMNS = {
    "Textbox83",
    "PeopleName",
    "P_ID2",
    "Textbox33",
    "Course",
    "COURSE_DATE",
    "Hours",
}


class CycleImportError(ValueError):
    pass


def parse_cycle_date(value, row_number):
    value = (value or "").strip()

    if not value:
        raise CycleImportError(
            f"Row {row_number}: course date is missing."
        )

    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError as exc:
        raise CycleImportError(
            f"Row {row_number}: invalid course date '{value}'."
        ) from exc


def parse_hours(value, row_number):
    value = (value or "").strip()

    if not value:
        raise CycleImportError(
            f"Row {row_number}: credited hours are missing."
        )

    try:
        hours = Decimal(value)
    except InvalidOperation as exc:
        raise CycleImportError(
            f"Row {row_number}: invalid credited hours '{value}'."
        ) from exc

    if hours < 0:
        raise CycleImportError(
            f"Row {row_number}: credited hours cannot be negative."
        )

    return hours


def import_cycle_hours(agency_id, csv_content, commit=True):
    if isinstance(csv_content, bytes):
        csv_content = csv_content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(csv_content))

    if reader.fieldnames is None:
        raise CycleImportError("The cycle report is empty.")

    actual_columns = {
        column.strip()
        for column in reader.fieldnames
        if column is not None
    }

    missing_columns = REQUIRED_COLUMNS - actual_columns

    if missing_columns:
        raise CycleImportError(
            "Invalid TCOLE cycle report. Missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    rows_processed = 0
    credits_created = 0
    credits_skipped = 0
    matched_records = set()

    totals_by_record = defaultdict(Decimal)

    try:
        for row_number, row in enumerate(reader, start=2):
            pid = (row.get("P_ID2") or "").strip()
            course_number = (row.get("Course") or "").strip()
            role_snapshot = (row.get("Textbox83") or "").strip() or None
            reported_total_text = (
                row.get("Textbox33") or ""
            ).strip() or None

            if not pid:
                raise CycleImportError(
                    f"Row {row_number}: TCOLE PID is missing."
                )

            if not course_number:
                raise CycleImportError(
                    f"Row {row_number}: course number is missing."
                )

            course_date = parse_cycle_date(
                row.get("COURSE_DATE"),
                row_number,
            )

            hours = parse_hours(
                row.get("Hours"),
                row_number,
            )

            officer = Officer.query.filter_by(
                agency_id=agency_id,
                tcole_pid=pid,
            ).one_or_none()

            if officer is None:
                raise CycleImportError(
                    f"Row {row_number}: no officer exists for TCOLE PID {pid}."
                )

            training_record = TrainingRecord.query.filter_by(
                agency_id=agency_id,
                officer_id=officer.id,
                course_number=course_number,
                course_date=course_date,
            ).one_or_none()

            if training_record is None:
                raise CycleImportError(
                    f"Row {row_number}: no training record matches "
                    f"PID {pid}, course {course_number}, "
                    f"date {course_date.isoformat()}."
                )

            rows_processed += 1
            matched_records.add(training_record.id)

            existing = TrainingCredit.query.filter_by(
                agency_id=agency_id,
                training_record_id=training_record.id,
                course_number=course_number,
                course_date=course_date,
                credited_hours=hours,
                role_snapshot=role_snapshot,
            ).one_or_none()

            if existing is None:
                db.session.add(
                    TrainingCredit(
                        agency_id=agency_id,
                        officer_id=officer.id,
                        training_record_id=training_record.id,
                        course_number=course_number,
                        course_date=course_date,
                        credited_hours=hours,
                        role_snapshot=role_snapshot,
                        reported_total_text=reported_total_text,
                    )
                )
                credits_created += 1
            else:
                credits_skipped += 1

            totals_by_record[training_record.id] += hours

        for training_record_id, total_hours in totals_by_record.items():
            training_record = db.session.get(
                TrainingRecord,
                training_record_id,
            )
            training_record.credited_hours = total_hours
            training_record.hours_source = "TCOLE_CYCLE_REPORT"

        if commit:
            db.session.commit()

    except Exception:
        if commit:
            db.session.rollback()
        raise

    return {
        "rows_processed": rows_processed,
        "training_records_matched": len(matched_records),
        "credits_created": credits_created,
        "credits_skipped": credits_skipped,
    }
