# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import uuid

from app.extensions import db
from app.importers.tcole_awards import import_awards_roster
from app.importers.tcole_courses import import_training_records
from app.importers.tcole_cycle import import_cycle_hours
from app.importers.tcole_licensee_search import (
    import_licensee_search,
)
from app.models import Agency, ImportJob, Officer, TrainingRecord, utcnow


class TcoleImportError(ValueError):
    pass


def serialize_import_job(job):
    return {
        "import_job_id": str(job.id),
        "status": job.status,
        "awards_filename": job.awards_filename,
        "courses_filename": job.courses_filename,
        "cycle_filename": job.cycle_filename,
        "licensee_search_filename":
            job.licensee_search_filename,
        "officer_count": job.officer_count,
        "award_rows_processed": job.award_rows_processed,
        "course_rows_processed": job.course_rows_processed,
        "cycle_rows_processed": job.cycle_rows_processed,
        "licensee_search_rows_processed":
            job.licensee_search_rows_processed,
        "peace_officer_license_rows":
            job.peace_officer_license_rows,
        "jailer_license_rows":
            job.jailer_license_rows,
        "jailer_service_dates_populated":
            job.jailer_service_dates_populated,
        "jailer_service_dates_updated":
            job.jailer_service_dates_updated,
        "jailer_service_dates_unchanged":
            job.jailer_service_dates_unchanged,
        "service_dates_populated":
            job.service_dates_populated,
        "service_dates_updated":
            job.service_dates_updated,
        "service_dates_unchanged":
            job.service_dates_unchanged,
        "unmatched_license_rows":
            job.unmatched_license_rows,
        "training_records_with_hours":
            job.training_records_with_hours,
        "awards_created": job.award_count,
        "training_records_created": job.course_count,
        "awards_skipped": job.skipped_award_count,
        "training_records_skipped": job.skipped_course_count,
        "warning_count": job.warning_count,
        "error_count": job.error_count,
        "failure_reason": job.failure_reason,
        "started_at": (
            job.started_at.isoformat()
            if job.started_at is not None
            else None
        ),
        "completed_at": (
            job.completed_at.isoformat()
            if job.completed_at is not None
            else None
        ),
    }


def get_import_summary(import_job_id, agency_id):
    if isinstance(import_job_id, str):
        try:
            import_job_id = uuid.UUID(import_job_id)
        except ValueError as exc:
            raise TcoleImportError(
                "Import job identifier is invalid."
            ) from exc

    job = ImportJob.query.filter_by(
        id=import_job_id,
        agency_id=agency_id,
    ).one_or_none()

    if job is None:
        raise TcoleImportError(
            "Import job does not exist for this agency."
        )

    return serialize_import_job(job)



def _get_staged_import_job(agency_id, import_job_id):
    job = ImportJob.query.filter_by(
        id=import_job_id,
        agency_id=agency_id,
    ).one_or_none()

    if job is None:
        raise TcoleImportError(
            "Import job does not exist for this agency."
        )

    return job


def _fail_staged_import(job_id, exc):
    db.session.rollback()

    failed_job = db.session.get(
        ImportJob,
        job_id,
    )

    if failed_job is not None:
        failed_job.status = "failed"
        failed_job.error_count = 1
        failed_job.failure_reason = str(exc)
        failed_job.completed_at = utcnow()
        db.session.commit()


def start_tcole_awards_import(
    agency_id,
    awards_content,
    awards_filename="rptAwards.csv",
):
    agency = db.session.get(Agency, agency_id)

    if agency is None:
        raise TcoleImportError("Agency does not exist.")

    job = ImportJob(
        agency_id=agency_id,
        status="validating",
        awards_filename=awards_filename,
        started_at=utcnow(),
    )

    db.session.add(job)
    db.session.commit()

    try:
        result = import_awards_roster(
            agency_id,
            awards_content,
            commit=False,
        )

        job.status = "awards_completed"
        job.officer_count = Officer.query.filter_by(
            agency_id=agency_id
        ).count()
        job.award_rows_processed = result[
            "rows_processed"
        ]
        job.award_count = result[
            "awards_created"
        ]
        job.skipped_award_count = result[
            "awards_skipped"
        ]
        job.warning_count = 0
        job.error_count = 0
        job.failure_reason = None

        db.session.commit()

        return serialize_import_job(job)

    except Exception as exc:
        _fail_staged_import(job.id, exc)
        raise


def run_tcole_courses_stage(
    agency_id,
    import_job_id,
    courses_content,
    courses_filename="rptCourseTaken.csv",
):
    job = _get_staged_import_job(
        agency_id,
        import_job_id,
    )

    if job.status != "awards_completed":
        raise TcoleImportError(
            "Awards Report must be completed before Course History."
        )

    try:
        result = import_training_records(
            agency_id,
            courses_content,
            commit=False,
        )

        job.status = "courses_completed"
        job.courses_filename = courses_filename
        job.course_rows_processed = result[
            "rows_processed"
        ]
        job.course_count = result[
            "training_records_created"
        ]
        job.skipped_course_count = result[
            "training_records_skipped"
        ]

        db.session.commit()

        return serialize_import_job(job)

    except Exception as exc:
        _fail_staged_import(job.id, exc)
        raise


def run_tcole_cycle_stage(
    agency_id,
    import_job_id,
    cycle_content,
    cycle_filename="rptCycleT_All.csv",
):
    job = _get_staged_import_job(
        agency_id,
        import_job_id,
    )

    if job.status != "courses_completed":
        raise TcoleImportError(
            "Course History must be completed before "
            "the Cycle Training Report."
        )

    try:
        result = import_cycle_hours(
            agency_id,
            cycle_content,
            commit=False,
        )

        job.status = "cycle_completed"
        job.cycle_filename = cycle_filename
        job.cycle_rows_processed = result[
            "rows_processed"
        ]

        job.training_records_with_hours = (
            TrainingRecord.query.filter_by(
                agency_id=agency_id
            )
            .filter(
                TrainingRecord.credited_hours.isnot(None)
            )
            .count()
        )

        db.session.commit()

        return serialize_import_job(job)

    except Exception as exc:
        _fail_staged_import(job.id, exc)
        raise


def run_tcole_licensee_search_stage(
    agency_id,
    import_job_id,
    licensee_search_content,
    licensee_search_filename=(
        "rptDepartmentOfficerSearch.csv"
    ),
):
    job = _get_staged_import_job(
        agency_id,
        import_job_id,
    )

    if job.status != "cycle_completed":
        raise TcoleImportError(
            "Cycle Training Report must be completed before "
            "the Department Licensee Search Report."
        )

    try:
        result = import_licensee_search(
            agency_id,
            licensee_search_content,
            commit=False,
        )

        job.status = "completed"
        job.licensee_search_filename = (
            licensee_search_filename
        )
        job.licensee_search_rows_processed = result[
            "rows_processed"
        ]
        job.peace_officer_license_rows = result[
            "peace_officer_license_rows"
        ]
        job.jailer_license_rows = result[
            "jailer_license_rows"
        ]
        job.jailer_service_dates_populated = result[
            "jailer_service_dates_populated"
        ]
        job.jailer_service_dates_updated = result[
            "jailer_service_dates_updated"
        ]
        job.jailer_service_dates_unchanged = result[
            "jailer_service_dates_unchanged"
        ]
        job.service_dates_populated = result[
            "service_dates_populated"
        ]
        job.service_dates_updated = result[
            "service_dates_updated"
        ]
        job.service_dates_unchanged = result[
            "service_dates_unchanged"
        ]
        job.unmatched_license_rows = result[
            "unmatched_license_rows"
        ]

        job.officer_count = Officer.query.filter_by(
            agency_id=agency_id
        ).count()

        job.warning_count = 0
        job.error_count = 0
        job.failure_reason = None
        job.completed_at = utcnow()

        db.session.commit()

        return serialize_import_job(job)

    except Exception as exc:
        _fail_staged_import(job.id, exc)
        raise


def run_tcole_import(
    agency_id,
    awards_content,
    courses_content,
    cycle_content,
    licensee_search_content,
    awards_filename="rptAwards.csv",
    courses_filename="rptCourseTaken.csv",
    cycle_filename="rptCycleT_All.csv",
    licensee_search_filename=(
        "rptDepartmentOfficerSearch.csv"
    ),
):
    agency = db.session.get(Agency, agency_id)

    if agency is None:
        raise TcoleImportError("Agency does not exist.")

    job = ImportJob(
        agency_id=agency_id,
        status="validating",
        awards_filename=awards_filename,
        courses_filename=courses_filename,
        cycle_filename=cycle_filename,
        licensee_search_filename=(
            licensee_search_filename
        ),
        started_at=utcnow(),
    )

    db.session.add(job)
    db.session.commit()

    try:
        awards_result = import_awards_roster(
            agency_id,
            awards_content,
            commit=False,
        )

        db.session.flush()

        courses_result = import_training_records(
            agency_id,
            courses_content,
            commit=False,
        )

        db.session.flush()

        cycle_result = import_cycle_hours(
            agency_id,
            cycle_content,
            commit=False,
        )

        db.session.flush()

        licensee_search_result = (
            import_licensee_search(
                agency_id,
                licensee_search_content,
                commit=False,
            )
        )

        db.session.flush()

        job.status = "completed"

        job.officer_count = Officer.query.filter_by(
            agency_id=agency_id
        ).count()

        job.award_rows_processed = awards_result[
            "rows_processed"
        ]

        job.course_rows_processed = courses_result[
            "rows_processed"
        ]

        job.cycle_rows_processed = cycle_result[
            "rows_processed"
        ]

        job.licensee_search_rows_processed = (
            licensee_search_result[
                "rows_processed"
            ]
        )

        job.peace_officer_license_rows = (
            licensee_search_result[
                "peace_officer_license_rows"
            ]
        )

        job.jailer_license_rows = (
            licensee_search_result[
                "jailer_license_rows"
            ]
        )

        job.jailer_service_dates_populated = (
            licensee_search_result[
                "jailer_service_dates_populated"
            ]
        )

        job.jailer_service_dates_updated = (
            licensee_search_result[
                "jailer_service_dates_updated"
            ]
        )

        job.jailer_service_dates_unchanged = (
            licensee_search_result[
                "jailer_service_dates_unchanged"
            ]
        )

        job.service_dates_populated = (
            licensee_search_result[
                "service_dates_populated"
            ]
        )

        job.service_dates_updated = (
            licensee_search_result[
                "service_dates_updated"
            ]
        )

        job.service_dates_unchanged = (
            licensee_search_result[
                "service_dates_unchanged"
            ]
        )

        job.unmatched_license_rows = (
            licensee_search_result[
                "unmatched_license_rows"
            ]
        )

        job.training_records_with_hours = (
            TrainingRecord.query.filter_by(
                agency_id=agency_id
            )
            .filter(
                TrainingRecord.credited_hours.isnot(None)
            )
            .count()
        )

        job.award_count = awards_result[
            "awards_created"
        ]

        job.course_count = courses_result[
            "training_records_created"
        ]

        job.skipped_award_count = awards_result[
            "awards_skipped"
        ]

        job.skipped_course_count = courses_result[
            "training_records_skipped"
        ]

        job.warning_count = 0
        job.error_count = 0
        job.failure_reason = None
        job.completed_at = utcnow()

        db.session.commit()

        return serialize_import_job(job)

    except Exception as exc:
        db.session.rollback()

        failed_job = db.session.get(
            ImportJob,
            job.id,
        )

        if failed_job is not None:
            failed_job.status = "failed"
            failed_job.error_count = 1
            failed_job.failure_reason = str(exc)
            failed_job.completed_at = utcnow()
            db.session.commit()

        raise
