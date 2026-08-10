from pathlib import Path

import pytest

from app import create_app
from app.extensions import db
from app.models import Agency, ImportJob, Officer, OfficerAward, TrainingRecord
from app.services.tcole_import import run_tcole_import


FIXTURE_DIR = Path(__file__).parent / "fixtures"
AWARDS_PATH = FIXTURE_DIR / "rptAwards.csv"
COURSES_PATH = FIXTURE_DIR / "rptCourseTaken.csv"
CYCLE_PATH = FIXTURE_DIR / "rptCycleT_All.csv"
LICENSEE_SEARCH_PATH = (
    FIXTURE_DIR / "rptDepartmentOfficerSearch.csv"
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_real_tcole_files_import_end_to_end(app):
    with app.app_context():
        agency = Agency(
            name="Port of Galveston Police Department"
        )
        db.session.add(agency)
        db.session.commit()

        result = run_tcole_import(
            agency.id,
            AWARDS_PATH.read_bytes(),
            COURSES_PATH.read_bytes(),
            CYCLE_PATH.read_bytes(),
            LICENSEE_SEARCH_PATH.read_bytes(),
            awards_filename=AWARDS_PATH.name,
            courses_filename=COURSES_PATH.name,
            cycle_filename=CYCLE_PATH.name,
            licensee_search_filename=(
                LICENSEE_SEARCH_PATH.name
            ),
        )

        assert result["status"] == "completed"

        assert Officer.query.count() > 0
        assert OfficerAward.query.count() > 0
        assert TrainingRecord.query.count() > 0
        assert ImportJob.query.count() == 1

        job = ImportJob.query.one()

        assert job.status == "completed"
        assert job.awards_filename == "rptAwards.csv"
        assert job.courses_filename == "rptCourseTaken.csv"
        assert job.cycle_filename == "rptCycleT_All.csv"

        assert job.officer_count == Officer.query.count()
        assert job.award_count == OfficerAward.query.count()
        assert job.course_count == TrainingRecord.query.count()

        assert job.training_records_with_hours == TrainingRecord.query.filter(
            TrainingRecord.credited_hours.isnot(None)
        ).count()

        # Real TCOLE four-report regression baseline.
        #
        # These values verify that the Department Licensee
        # Search report is fully reconciled and that Peace
        # Officer License dates populate service-start dates.
        assert job.licensee_search_rows_processed == 6925
        assert job.peace_officer_license_rows == 41
        assert job.service_dates_populated == 41
        assert job.service_dates_updated == 0
        assert job.service_dates_unchanged == 0

        assert job.jailer_license_rows == 5
        assert job.jailer_service_dates_populated == 5
        assert job.jailer_service_dates_updated == 0
        assert job.jailer_service_dates_unchanged == 0

        assert job.unmatched_license_rows == 0

        officers_with_service_dates = Officer.query.filter(
            Officer.peace_officer_service_start_date.isnot(None)
        ).count()

        assert officers_with_service_dates == 41

        jailers_with_service_dates = Officer.query.filter(
            Officer.jailer_service_start_date.isnot(None)
        ).count()

        assert jailers_with_service_dates == 5

        battice = Officer.query.filter_by(
            tcole_pid="478578"
        ).one()

        assert (
            battice.jailer_service_start_date.isoformat()
            == "2020-01-30"
        )

        print()
        print("REAL TCOLE FOUR-FILE IMPORT SUMMARY")
        print("------------------------------------")
        print(f"Officers: {Officer.query.count()}")
        print(f"Award rows processed: {job.award_rows_processed}")
        print(f"Awards created: {job.award_count}")
        print(f"Course rows processed: {job.course_rows_processed}")
        print(f"Training records created: {job.course_count}")
        print(f"Cycle rows processed: {job.cycle_rows_processed}")
        print(
            "Licensee search rows processed: "
            f"{job.licensee_search_rows_processed}"
        )
        print(
            "Peace Officer License rows: "
            f"{job.peace_officer_license_rows}"
        )
        print(
            "Peace Officer service dates populated: "
            f"{job.service_dates_populated}"
        )
        print(
            "Jailer License rows: "
            f"{job.jailer_license_rows}"
        )
        print(
            "Jailer service dates populated: "
            f"{job.jailer_service_dates_populated}"
        )
        print(
            "Service dates updated: "
            f"{job.service_dates_updated}"
        )
        print(
            "Service dates unchanged: "
            f"{job.service_dates_unchanged}"
        )
        print(
            "Unmatched license rows: "
            f"{job.unmatched_license_rows}"
        )
        print(
            "Training records with credited hours: "
            f"{job.training_records_with_hours}"
        )
        print(f"Warnings: {job.warning_count}")
        print(f"Errors: {job.error_count}")
