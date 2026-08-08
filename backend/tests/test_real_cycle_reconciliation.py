from decimal import Decimal
from pathlib import Path

import pytest

from app import create_app
from app.extensions import db
from app.importers.tcole_cycle import import_cycle_hours
from app.models import (
    Agency,
    Officer,
    TrainingCredit,
    TrainingRecord,
)
from app.services.tcole_import import run_tcole_import


FIXTURE_DIR = Path(__file__).parent / "fixtures"
AWARDS_PATH = FIXTURE_DIR / "rptAwards.csv"
COURSES_PATH = FIXTURE_DIR / "rptCourseTaken.csv"
CYCLE_PATH = FIXTURE_DIR / "rptCycleT_All.csv"


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


def test_real_cycle_report_reconciles_to_training_history(app):
    with app.app_context():
        agency = Agency(
            name="Port of Galveston Police Department"
        )
        db.session.add(agency)
        db.session.commit()

        run_tcole_import(
            agency.id,
            AWARDS_PATH.read_bytes(),
            COURSES_PATH.read_bytes(),
            awards_filename=AWARDS_PATH.name,
            courses_filename=COURSES_PATH.name,
        )

        course_count = TrainingRecord.query.count()

        result = import_cycle_hours(
            agency.id,
            CYCLE_PATH.read_bytes(),
        )

        records_with_hours = TrainingRecord.query.filter(
            TrainingRecord.credited_hours.isnot(None)
        ).count()

        records_without_hours = TrainingRecord.query.filter(
            TrainingRecord.credited_hours.is_(None)
        ).count()

        total_credited_hours = (
            db.session.query(
                db.func.sum(TrainingRecord.credited_hours)
            ).scalar()
            or Decimal("0")
        )

        print()
        print("REAL TCOLE THREE-REPORT RECONCILIATION")
        print("--------------------------------------")
        print(f"Officers: {Officer.query.count()}")
        print(f"Training records: {course_count}")
        print(f"Cycle rows processed: {result['rows_processed']}")
        print(
            "Training records matched: "
            f"{result['training_records_matched']}"
        )
        print(f"Credit rows created: {result['credits_created']}")
        print(f"Credit rows skipped: {result['credits_skipped']}")
        print(f"Records with credited hours: {records_with_hours}")
        print(f"Records without credited hours: {records_without_hours}")
        print(f"Total credited hours: {total_credited_hours}")
        print(f"Raw training credits: {TrainingCredit.query.count()}")

        assert course_count == 6622
        assert result["training_records_matched"] == course_count
        assert records_with_hours == course_count
        assert records_without_hours == 0

        assert all(
            record.hours_source == "TCOLE_CYCLE_REPORT"
            for record in TrainingRecord.query.all()
        )
