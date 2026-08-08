from pathlib import Path

import pytest

from app import create_app
from app.extensions import db
from app.models import Agency, ImportJob, Officer, OfficerAward, TrainingRecord
from app.services.tcole_import import run_tcole_import


FIXTURE_DIR = Path(__file__).parent / "fixtures"
AWARDS_PATH = FIXTURE_DIR / "rptAwards.csv"
COURSES_PATH = FIXTURE_DIR / "rptCourseTaken.csv"


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
    awards_content = AWARDS_PATH.read_bytes()
    courses_content = COURSES_PATH.read_bytes()

    with app.app_context():
        agency = Agency(
            name="Port of Galveston Police Department"
        )
        db.session.add(agency)
        db.session.commit()

        result = run_tcole_import(
            agency.id,
            awards_content,
            courses_content,
            awards_filename=AWARDS_PATH.name,
            courses_filename=COURSES_PATH.name,
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

        assert job.officer_count == Officer.query.count()
        assert job.award_count == OfficerAward.query.count()
        assert job.course_count == TrainingRecord.query.count()

        print()
        print("REAL TCOLE IMPORT SUMMARY")
        print("-------------------------")
        print(f"Officers: {Officer.query.count()}")
        print(f"Award rows processed: {job.award_rows_processed}")
        print(f"Awards created: {job.award_count}")
        print(f"Awards skipped: {job.skipped_award_count}")
        print(f"Course rows processed: {job.course_rows_processed}")
        print(f"Training records created: {job.course_count}")
        print(f"Training records skipped: {job.skipped_course_count}")
        print(f"Warnings: {job.warning_count}")
        print(f"Errors: {job.error_count}")
