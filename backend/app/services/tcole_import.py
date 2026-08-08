from app.extensions import db
from app.importers.tcole_awards import import_awards_roster
from app.importers.tcole_courses import import_training_records
from app.models import Agency, ImportJob, Officer, utcnow


class TcoleImportError(ValueError):
    pass


def run_tcole_import(
    agency_id,
    awards_content,
    courses_content,
    awards_filename="rptAwards.csv",
    courses_filename="rptCourseTaken.csv",
):
    agency = db.session.get(Agency, agency_id)

    if agency is None:
        raise TcoleImportError("Agency does not exist.")

    job = ImportJob(
        agency_id=agency_id,
        status="validating",
        awards_filename=awards_filename,
        courses_filename=courses_filename,
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

        job.status = "completed"
        job.officer_count = Officer.query.filter_by(
            agency_id=agency_id
        ).count()
        job.award_count = awards_result["awards_created"]
        job.course_count = courses_result["training_records_created"]
        job.skipped_award_count = awards_result["awards_skipped"]
        job.skipped_course_count = courses_result["training_records_skipped"]
        job.warning_count = (
            job.skipped_award_count + job.skipped_course_count
        )
        job.error_count = 0
        job.failure_reason = None
        job.completed_at = utcnow()

        db.session.commit()

        return {
            "import_job_id": str(job.id),
            "status": job.status,
            "officer_count": job.officer_count,
            "awards_created": job.award_count,
            "training_records_created": job.course_count,
            "awards_skipped": job.skipped_award_count,
            "training_records_skipped": job.skipped_course_count,
            "warning_count": job.warning_count,
        }

    except Exception as exc:
        db.session.rollback()

        failed_job = db.session.get(ImportJob, job.id)

        if failed_job is not None:
            failed_job.status = "failed"
            failed_job.error_count = 1
            failed_job.failure_reason = str(exc)
            failed_job.completed_at = utcnow()
            db.session.commit()

        raise
