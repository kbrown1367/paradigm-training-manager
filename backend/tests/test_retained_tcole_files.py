from datetime import timedelta

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Agency,
    ImportJob,
    RetainedTcoleFile,
    utcnow,
)
from app.services.retained_tcole_files import (
    FILE_TYPE_AWARDS,
    purge_expired_tcole_files,
    retain_tcole_file,
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "AUTHORIZATION_DISABLED": True,
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def make_agency_and_job():
    agency = Agency(
        name="Retention Test Police Department"
    )
    db.session.add(agency)
    db.session.flush()

    job = ImportJob(
        agency_id=agency.id,
        status="completed",
    )
    db.session.add(job)
    db.session.commit()

    return agency.id, job.id


def test_retains_exact_file_bytes(app):
    with app.app_context():
        agency_id, job_id = make_agency_and_job()

        content = b"column,value\none,two\n"

        retained = retain_tcole_file(
            agency_id=agency_id,
            import_job_id=job_id,
            file_type=FILE_TYPE_AWARDS,
            filename="rptAwards.csv",
            content=content,
        )
        db.session.commit()

        assert retained.content == content
        assert retained.size_bytes == len(content)
        assert retained.original_filename == (
            "rptAwards.csv"
        )
        assert len(retained.sha256) == 64
        assert retained.expires_at > (
            retained.uploaded_at
        )


def test_new_file_replaces_same_agency_type(app):
    with app.app_context():
        agency_id, first_job_id = (
            make_agency_and_job()
        )

        retain_tcole_file(
            agency_id=agency_id,
            import_job_id=first_job_id,
            file_type=FILE_TYPE_AWARDS,
            filename="old.csv",
            content=b"old",
        )
        db.session.commit()

        second_job = ImportJob(
            agency_id=agency_id,
            status="completed",
        )
        db.session.add(second_job)
        db.session.commit()

        retain_tcole_file(
            agency_id=agency_id,
            import_job_id=second_job.id,
            file_type=FILE_TYPE_AWARDS,
            filename="new.csv",
            content=b"new",
        )
        db.session.commit()

        records = (
            RetainedTcoleFile.query
            .filter_by(
                agency_id=agency_id,
                file_type=FILE_TYPE_AWARDS,
            )
            .all()
        )

        assert len(records) == 1
        assert records[0].content == b"new"
        assert records[0].original_filename == (
            "new.csv"
        )
        assert records[0].import_job_id == (
            second_job.id
        )


def test_same_file_type_is_tenant_isolated(app):
    with app.app_context():
        agency_one_id, job_one_id = (
            make_agency_and_job()
        )

        agency_two = Agency(
            name="Second Police Department"
        )
        db.session.add(agency_two)
        db.session.flush()

        job_two = ImportJob(
            agency_id=agency_two.id,
            status="completed",
        )
        db.session.add(job_two)
        db.session.commit()

        retain_tcole_file(
            agency_id=agency_one_id,
            import_job_id=job_one_id,
            file_type=FILE_TYPE_AWARDS,
            filename="one.csv",
            content=b"agency-one",
        )

        retain_tcole_file(
            agency_id=agency_two.id,
            import_job_id=job_two.id,
            file_type=FILE_TYPE_AWARDS,
            filename="two.csv",
            content=b"agency-two",
        )

        db.session.commit()

        assert RetainedTcoleFile.query.count() == 2


def test_expired_file_is_purged_without_job(app):
    with app.app_context():
        agency_id, job_id = make_agency_and_job()

        retained = retain_tcole_file(
            agency_id=agency_id,
            import_job_id=job_id,
            file_type=FILE_TYPE_AWARDS,
            filename="expired.csv",
            content=b"expired",
        )

        retained.expires_at = (
            utcnow() - timedelta(seconds=1)
        )
        db.session.commit()

        count = purge_expired_tcole_files()
        db.session.commit()

        assert count == 1
        assert RetainedTcoleFile.query.count() == 0
        assert ImportJob.query.filter_by(
            id=job_id
        ).one_or_none() is not None


def test_cli_purges_only_expired_retained_files(app):
    from app.services.retained_tcole_files import (
        FILE_TYPE_COURSES,
    )

    with app.app_context():
        agency_id, job_id = make_agency_and_job()

        expired = retain_tcole_file(
            agency_id=agency_id,
            import_job_id=job_id,
            file_type=FILE_TYPE_AWARDS,
            filename="expired.csv",
            content=b"expired",
        )

        current = retain_tcole_file(
            agency_id=agency_id,
            import_job_id=job_id,
            file_type=FILE_TYPE_COURSES,
            filename="current.csv",
            content=b"current",
        )

        expired.expires_at = (
            utcnow() - timedelta(seconds=1)
        )

        current.expires_at = (
            utcnow() + timedelta(days=30)
        )

        db.session.commit()

    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["purge-expired-tcole-files"]
    )

    assert result.exit_code == 0
    assert (
        "Purged 1 expired retained "
        "TCOLE file(s)."
        in result.output
    )

    with app.app_context():
        rows = (
            RetainedTcoleFile.query
            .filter_by(
                agency_id=agency_id,
            )
            .all()
        )

        assert len(rows) == 1
        assert rows[0].file_type == (
            FILE_TYPE_COURSES
        )
        assert rows[0].content == b"current"


def test_cli_is_safe_when_nothing_is_expired(app):
    with app.app_context():
        agency_id, job_id = make_agency_and_job()

        retain_tcole_file(
            agency_id=agency_id,
            import_job_id=job_id,
            file_type=FILE_TYPE_AWARDS,
            filename="current.csv",
            content=b"current",
        )

        db.session.commit()

    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["purge-expired-tcole-files"]
    )

    assert result.exit_code == 0
    assert (
        "Purged 0 expired retained "
        "TCOLE file(s)."
        in result.output
    )

    with app.app_context():
        assert RetainedTcoleFile.query.count() == 1
