from datetime import date

import pytest

from app import create_app
from app.extensions import db
from app.models import Agency, Officer, OfficerAward
from app.compliance.officer_profile import (
    evaluate_officer_compliance_profile,
)
from app.services.license_tracking import (
    LicenseTrackingError,
    detected_license_types,
    is_license_tracking_enabled,
    set_license_tracking,
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


def make_dual_license_officer():
    agency = Agency(
        name="PTM-002 Test Agency",
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="PTM002",
        first_name="DUAL",
        last_name="LICENSE",
        peace_officer_service_start_date=date(
            2020, 1, 1
        ),
        telecommunicator_service_start_date=date(
            2020, 1, 1
        ),
    )
    db.session.add(officer)
    db.session.flush()

    db.session.add_all(
        [
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Peace Officer License",
                award_date=date(2020, 1, 1),
            ),
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Telecommunicator License",
                award_date=date(2020, 1, 1),
            ),
        ]
    )

    db.session.commit()

    return agency, officer


def test_multi_license_defaults_to_tracking_all(app):
    with app.app_context():
        _, officer = make_dual_license_officer()

        assert set(detected_license_types(officer)) == {
            "PEACE_OFFICER",
            "TELECOMMUNICATOR",
        }

        assert is_license_tracking_enabled(
            officer,
            "PEACE_OFFICER",
        ) is True

        assert is_license_tracking_enabled(
            officer,
            "TELECOMMUNICATOR",
        ) is True


def test_disabling_telecommunicator_removes_its_requirements(app):
    with app.app_context():
        agency, officer = make_dual_license_officer()

        before = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 12),
        )

        assert any(
            item.get("course_number") == "786"
            for item in before[
                "outstanding_requirements"
            ]
        )

        set_license_tracking(
            agency_id=agency.id,
            officer_id=officer.id,
            license_type="TELECOMMUNICATOR",
            tracking_enabled=False,
            changed_by="Pilot Admin",
            reason="Employee moved to Peace Officer role",
        )

        after = evaluate_officer_compliance_profile(
            officer,
            evaluation_date=date(2026, 8, 12),
        )

        assert (
            is_license_tracking_enabled(
                officer,
                "TELECOMMUNICATOR",
            )
            is False
        )

        assert "TELECOMMUNICATOR" in (
            detected_license_types(officer)
        )

        assert not any(
            item.get("course_number") == "786"
            for item in after[
                "outstanding_requirements"
            ]
        )

        assert (
            after["components"][
                "TELECOMMUNICATOR"
            ]["applicable"]
            is False
        )

        assert (
            after["components"][
                "PEACE_OFFICER"
            ]["applicable"]
            is True
        )


def test_tracking_can_be_resumed(app):
    with app.app_context():
        agency, officer = make_dual_license_officer()

        set_license_tracking(
            agency_id=agency.id,
            officer_id=officer.id,
            license_type="TELECOMMUNICATOR",
            tracking_enabled=False,
            changed_by="Pilot Admin",
        )

        set_license_tracking(
            agency_id=agency.id,
            officer_id=officer.id,
            license_type="TELECOMMUNICATOR",
            tracking_enabled=True,
            changed_by="Pilot Admin",
        )

        assert is_license_tracking_enabled(
            officer,
            "TELECOMMUNICATOR",
        ) is True


def test_cannot_disable_final_tracked_license(app):
    with app.app_context():
        agency, officer = make_dual_license_officer()

        set_license_tracking(
            agency_id=agency.id,
            officer_id=officer.id,
            license_type="TELECOMMUNICATOR",
            tracking_enabled=False,
            changed_by="Pilot Admin",
        )

        with pytest.raises(
            LicenseTrackingError,
            match="At least one license must remain tracked",
        ):
            set_license_tracking(
                agency_id=agency.id,
                officer_id=officer.id,
                license_type="PEACE_OFFICER",
                tracking_enabled=False,
                changed_by="Pilot Admin",
            )


def test_single_license_tracking_cannot_be_disabled(app):
    with app.app_context():
        agency = Agency(
            name="Single License Test Agency"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="SINGLE001",
            first_name="SINGLE",
            last_name="LICENSE",
            peace_officer_service_start_date=date(
                2020, 1, 1
            ),
        )
        db.session.add(officer)
        db.session.flush()

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="License",
                award_name="Peace Officer License",
                award_date=date(2020, 1, 1),
            )
        )

        db.session.commit()

        with pytest.raises(
            LicenseTrackingError,
            match="multiple license types",
        ):
            set_license_tracking(
                agency_id=agency.id,
                officer_id=officer.id,
                license_type="PEACE_OFFICER",
                tracking_enabled=False,
                changed_by="Pilot Admin",
            )
