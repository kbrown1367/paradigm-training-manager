from datetime import date

import pytest

from app import create_app
from app.extensions import db
from app.importers.tcole_licensee_search import (
    LicenseeSearchImportError,
    import_licensee_search,
)
from app.models import Agency, Officer


HEADER = (
    "P_ID,LNAME,FNAME,MNAME,SFX,SEX,RACE,"
    "AGENCY,DOB,RecordDesc,RecordName,RecordDate\n"
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


def make_officer(
    agency,
    pid="123456",
):
    officer = Officer(
        agency_id=agency.id,
        tcole_pid=pid,
        first_name="JOHN",
        last_name="SMITH",
    )
    db.session.add(officer)
    db.session.commit()

    return officer


def test_jailer_only_report_is_valid(app):
    with app.app_context():
        agency = Agency(name="Test Sheriff's Office")
        db.session.add(agency)
        db.session.commit()

        officer = make_officer(
            agency,
            pid="123456",
        )

        content = (
            HEADER
            + "123456,SMITH,JOHN,,,M,White,0001,"
            "01/01/1990,License,Jailer License,"
            "02/17/2021\n"
        )

        result = import_licensee_search(
            agency.id,
            content,
        )

        assert result["peace_officer_license_rows"] == 0
        assert result["jailer_license_rows"] == 1
        assert (
            result["jailer_service_dates_populated"]
            == 1
        )

        db.session.refresh(officer)

        assert officer.jailer_service_start_date == date(
            2021,
            2,
            17,
        )
        assert (
            officer.peace_officer_service_start_date
            is None
        )


def test_dual_license_dates_remain_independent(app):
    with app.app_context():
        agency = Agency(name="Test Department")
        db.session.add(agency)
        db.session.commit()

        officer = make_officer(
            agency,
            pid="222222",
        )

        content = (
            HEADER
            + "222222,SMITH,JOHN,,,M,White,0001,"
            "01/01/1990,License,Peace Officer License,"
            "01/15/2018\n"
            + "222222,SMITH,JOHN,,,M,White,0001,"
            "01/01/1990,License,Jailer License,"
            "06/03/2020\n"
        )

        result = import_licensee_search(
            agency.id,
            content,
        )

        assert result["peace_officer_license_rows"] == 1
        assert result["jailer_license_rows"] == 1

        db.session.refresh(officer)

        assert (
            officer.peace_officer_service_start_date
            == date(2018, 1, 15)
        )
        assert (
            officer.jailer_service_start_date
            == date(2020, 6, 3)
        )


def test_county_jailer_alias_is_supported(app):
    with app.app_context():
        agency = Agency(name="Test Sheriff's Office")
        db.session.add(agency)
        db.session.commit()

        officer = make_officer(
            agency,
            pid="333333",
        )

        content = (
            HEADER
            + "333333,DOE,JANE,,,F,White,0001,"
            "01/01/1990,License,County Jailer License,"
            "09/12/2006\n"
        )

        result = import_licensee_search(
            agency.id,
            content,
        )

        assert result["jailer_license_rows"] == 1

        db.session.refresh(officer)

        assert officer.jailer_service_start_date == date(
            2006,
            9,
            12,
        )


def test_existing_jailer_date_is_updated_from_tcole(app):
    with app.app_context():
        agency = Agency(name="Test Sheriff's Office")
        db.session.add(agency)
        db.session.commit()

        officer = make_officer(
            agency,
            pid="444444",
        )

        officer.jailer_service_start_date = date(
            2020,
            1,
            1,
        )
        db.session.commit()

        content = (
            HEADER
            + "444444,DOE,JANE,,,F,White,0001,"
            "01/01/1990,License,Jailer License,"
            "01/30/2020\n"
        )

        result = import_licensee_search(
            agency.id,
            content,
        )

        assert (
            result["jailer_service_dates_updated"]
            == 1
        )

        db.session.refresh(officer)

        assert officer.jailer_service_start_date == date(
            2020,
            1,
            30,
        )


def test_report_without_supported_license_is_rejected(app):
    with app.app_context():
        agency = Agency(name="Test Department")
        db.session.add(agency)
        db.session.commit()

        content = (
            HEADER
            + "555555,DOE,JANE,,,F,White,0001,"
            "01/01/1990,Certificate,Some Certificate,"
            "01/30/2020\n"
        )

        with pytest.raises(
            LicenseeSearchImportError,
            match="No supported license records",
        ):
            import_licensee_search(
                agency.id,
                content,
            )


def test_duplicate_logical_jailer_license_is_rejected(app):
    with app.app_context():
        agency = Agency(name="Test Sheriff's Office")
        db.session.add(agency)
        db.session.commit()

        make_officer(
            agency,
            pid="666666",
        )

        content = (
            HEADER
            + "666666,DOE,JANE,,,F,White,0001,"
            "01/01/1990,License,Jailer License,"
            "01/30/2020\n"
            + "666666,DOE,JANE,,,F,White,0001,"
            "01/01/1990,License,County Jailer License,"
            "01/30/2020\n"
        )

        with pytest.raises(
            LicenseeSearchImportError,
            match="more than one Jailer license",
        ):
            import_licensee_search(
                agency.id,
                content,
            )
