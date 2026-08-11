from datetime import date

import pytest

from app import create_app
from app.extensions import db
from app.importers.tcole_licensee_search import (
    import_licensee_search,
)
from app.models import Agency, Officer


HEADER = (
    "P_ID,LNAME,FNAME,MNAME,SFX,SEX,RACE,"
    "AGENCY_ID,DOB,RecordDesc,RecordName,RecordDate\n"
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def make_officer():
    agency = Agency(
        name="Test Communications Center"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="555555",
        first_name="Jane",
        last_name="Dispatcher",
    )
    db.session.add(officer)
    db.session.commit()

    return agency, officer


def test_telecommunicator_license_imports_service_date(app):
    with app.app_context():
        agency, officer = make_officer()

        content = (
            HEADER
            + "555555,DISPATCHER,JANE,,,F,White,"
            "0001,01/01/1990,License,"
            "Telecommunicator License,04/14/2023\n"
        )

        result = import_licensee_search(
            agency.id,
            content,
        )

        db.session.refresh(officer)

        assert (
            officer.telecommunicator_service_start_date
            == date(2023, 4, 14)
        )
        assert (
            result["telecommunicator_license_rows"]
            == 1
        )
        assert (
            result[
                "telecommunicator_service_dates_populated"
            ]
            == 1
        )


def test_telecommunicator_license_date_is_authoritative(app):
    with app.app_context():
        agency, officer = make_officer()

        officer.telecommunicator_service_start_date = (
            date(2022, 1, 1)
        )
        db.session.commit()

        content = (
            HEADER
            + "555555,DISPATCHER,JANE,,,F,White,"
            "0001,01/01/1990,License,"
            "Telecommunicator License,04/14/2023\n"
        )

        result = import_licensee_search(
            agency.id,
            content,
        )

        db.session.refresh(officer)

        assert (
            officer.telecommunicator_service_start_date
            == date(2023, 4, 14)
        )
        assert (
            result[
                "telecommunicator_service_dates_updated"
            ]
            == 1
        )


def test_non_telecommunicator_record_is_ignored(app):
    with app.app_context():
        agency, officer = make_officer()

        content = (
            HEADER
            + "555555,DISPATCHER,JANE,,,F,White,"
            "0001,01/01/1990,Course,"
            "2019 Basic Telecommunicator Course,"
            "04/14/2023\n"
            + "555555,DISPATCHER,JANE,,,F,White,"
            "0001,01/01/1990,License,"
            "Telecommunicator License,04/14/2023\n"
        )

        result = import_licensee_search(
            agency.id,
            content,
        )

        assert result["rows_processed"] == 2
        assert result["supported_license_rows"] == 1
        assert (
            officer.telecommunicator_service_start_date
            == date(2023, 4, 14)
        )
