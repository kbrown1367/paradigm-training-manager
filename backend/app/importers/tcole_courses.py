import csv
import io
from datetime import datetime

from app.extensions import db
from app.models import Officer, TrainingRecord


REQUIRED_COLUMNS = {
    "P_ID1",
    "P_ID",
    "STUDENT_NAME",
    "PLUS_COURSE_ID",
    "COURSE_ID",
    "COURSE_DATE",
}


class CourseImportError(ValueError):
    pass


def parse_course(value, row_number):
    value = (value or "").strip()

    if not value:
        raise CourseImportError(
            f"Row {row_number}: course is missing."
        )

    if " - " not in value:
        raise CourseImportError(
            f"Row {row_number}: course is not in expected NUMBER - TITLE format."
        )

    course_number, course_title = value.split(" - ", 1)

    course_number = course_number.strip()
    course_title = course_title.strip()

    if not course_number or not course_title:
        raise CourseImportError(
            f"Row {row_number}: course number or title is missing."
        )

    return course_number, course_title


def parse_course_date(value, row_number):
    value = (value or "").strip()

    if not value:
        raise CourseImportError(
            f"Row {row_number}: course date is missing."
        )

    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError as exc:
        raise CourseImportError(
            f"Row {row_number}: invalid course date '{value}'."
        ) from exc


def import_training_records(agency_id, csv_content, commit=True):
    if isinstance(csv_content, bytes):
        csv_content = csv_content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(csv_content))

    if reader.fieldnames is None:
        raise CourseImportError("The course file is empty.")

    actual_columns = {
        column.strip()
        for column in reader.fieldnames
        if column is not None
    }

    missing_columns = REQUIRED_COLUMNS - actual_columns

    if missing_columns:
        raise CourseImportError(
            "Invalid TCOLE course file. Missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    rows_processed = 0
    records_created = 0
    records_skipped = 0
    officers_matched = set()
    seen_records = set()

    try:
        for row_number, row in enumerate(reader, start=2):
            pid = (row.get("P_ID") or "").strip()
            student_name = (row.get("STUDENT_NAME") or "").strip()
            plus_course_id = (row.get("PLUS_COURSE_ID") or "").strip() or None

            if not pid:
                raise CourseImportError(
                    f"Row {row_number}: TCOLE PID is missing."
                )

            if not student_name:
                raise CourseImportError(
                    f"Row {row_number}: student name is missing."
                )

            officer = Officer.query.filter_by(
                agency_id=agency_id,
                tcole_pid=pid,
            ).one_or_none()

            if officer is None:
                raise CourseImportError(
                    f"Row {row_number}: no officer exists for TCOLE PID {pid}. "
                    "Import the agency awards file first."
                )

            course_number, course_title = parse_course(
                row.get("COURSE_ID"),
                row_number,
            )

            course_date = parse_course_date(
                row.get("COURSE_DATE"),
                row_number,
            )

            rows_processed += 1
            officers_matched.add(pid)

            record_key = (
                officer.id,
                course_number,
                course_title,
                course_date,
                plus_course_id,
            )

            if record_key in seen_records:
                records_skipped += 1
                continue

            seen_records.add(record_key)

            existing = TrainingRecord.query.filter_by(
                agency_id=agency_id,
                officer_id=officer.id,
                course_number=course_number,
                course_title=course_title,
                course_date=course_date,
                plus_course_id=plus_course_id,
            ).one_or_none()

            if existing is not None:
                records_skipped += 1
                continue

            db.session.add(
                TrainingRecord(
                    agency_id=agency_id,
                    officer_id=officer.id,
                    course_number=course_number,
                    course_title=course_title,
                    course_date=course_date,
                    plus_course_id=plus_course_id,
                )
            )

            records_created += 1

        if commit:
            db.session.commit()

    except Exception:
        if commit:
            db.session.rollback()
        raise

    return {
        "rows_processed": rows_processed,
        "unique_officers": len(officers_matched),
        "training_records_created": records_created,
        "training_records_skipped": records_skipped,
    }
