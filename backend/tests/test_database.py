import pytest

from app import create_app
from app.extensions import db
from app.models import Agency, ImportJob, Officer


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


def test_agency_can_be_created(app):
    with app.app_context():
        agency = Agency(
            name="Port of Galveston Police Department",
            tcole_agency_number="TEST-001",
        )

        db.session.add(agency)
        db.session.commit()

        saved = db.session.get(Agency, agency.id)

        assert saved is not None
        assert saved.name == "Port of Galveston Police Department"
        assert saved.status == "active"


def test_officer_belongs_to_agency(app):
    with app.app_context():
        agency = Agency(name="Test Police Department")
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="12345678",
            first_name="John",
            last_name="Smith",
        )

        db.session.add(officer)
        db.session.commit()

        assert officer.agency.id == agency.id
        assert officer in agency.officers


def test_import_job_belongs_to_agency(app):
    with app.app_context():
        agency = Agency(name="Test Police Department")
        db.session.add(agency)
        db.session.flush()

        job = ImportJob(
            agency_id=agency.id,
            awards_filename="rptAwards.csv",
            courses_filename="rptCourseTaken.csv",
        )

        db.session.add(job)
        db.session.commit()

        assert job.agency.id == agency.id
        assert job.status == "pending"


def test_tcole_pid_must_be_unique_within_agency(app):
    with app.app_context():
        agency = Agency(name="Test Police Department")
        db.session.add(agency)
        db.session.flush()

        db.session.add(
            Officer(
                agency_id=agency.id,
                tcole_pid="12345678",
                first_name="John",
                last_name="Smith",
            )
        )
        db.session.commit()

        db.session.add(
            Officer(
                agency_id=agency.id,
                tcole_pid="12345678",
                first_name="Jane",
                last_name="Smith",
            )
        )

        with pytest.raises(Exception):
            db.session.commit()

        db.session.rollback()
