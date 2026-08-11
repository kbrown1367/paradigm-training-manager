from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.jailer_proficiency import (
    evaluate_advanced_jailer_proficiency,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAward,
    TrainingRecord,
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


def make_jailer(
    service_start=date(2016, 1, 1),
    include_basic=True,
    include_intermediate=True,
):
    agency = Agency(
        name="Test Sheriff's Office"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="JOHN",
        last_name="SMITH",
        jailer_service_start_date=service_start,
    )
    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Jailer License",
            award_date=service_start,
        )
    )

    if include_basic:
        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Basic Jailer",
                award_date=date(2018, 1, 1),
            )
        )

    if include_intermediate:
        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name=(
                    "Intermediate Jailer Proficiency"
                ),
                award_date=date(2020, 1, 1),
            )
        )

    db.session.commit()

    return agency, officer


def add_training(
    agency,
    officer,
    hours,
    course_number="9000",
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=course_number,
            course_title=f"Course {course_number}",
            course_date=date(2025, 1, 1),
            credited_hours=Decimal(str(hours)),
            hours_source="TCOLE_CYCLE_REPORT",
            source="TCOLE",
        )
    )


def add_certificate(
    agency,
    officer,
    name,
    award_date=date(2025, 1, 1),
):
    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="Certificate",
            award_name=name,
            award_date=award_date,
        )
    )


def test_eight_year_800_hour_pathway(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2018, 1, 1),
        )

        add_training(
            agency,
            officer,
            800,
        )
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["type"] == (
            "SERVICE_TRAINING"
        )
        assert pathway["service_years"] == 8
        assert pathway["training_hours"] == 800


def test_six_year_1200_hour_pathway(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2020, 1, 1),
        )

        add_training(
            agency,
            officer,
            1200,
        )
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["service_years"] == 6
        assert pathway["training_hours"] == 1200


def test_four_year_2400_hour_pathway(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2022, 1, 1),
        )

        add_training(
            agency,
            officer,
            2400,
        )
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["service_years"] == 4
        assert pathway["training_hours"] == 2400


def test_associate_degree_six_year_pathway(app):
    with app.app_context():
        _, officer = make_jailer(
            service_start=date(2020, 1, 1),
        )

        officer.verified_education_level = "ASSOCIATE"
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["type"] == "EDUCATION"
        assert pathway["service_years"] == 6
        assert pathway["education_level"] == (
            "ASSOCIATE"
        )


def test_bachelor_degree_four_year_pathway(app):
    with app.app_context():
        _, officer = make_jailer(
            service_start=date(2022, 1, 1),
        )

        officer.verified_education_level = "BACHELOR"
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["type"] == "EDUCATION"
        assert pathway["service_years"] == 4
        assert pathway["education_level"] == (
            "BACHELOR"
        )


def test_two_year_military_six_year_pathway(app):
    with app.app_context():
        _, officer = make_jailer(
            service_start=date(2020, 1, 1),
        )

        officer.verified_military_months = 24
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["type"] == "MILITARY"
        assert pathway["service_years"] == 6
        assert pathway["military_years"] == 2


def test_four_year_military_four_year_pathway(app):
    with app.app_context():
        _, officer = make_jailer(
            service_start=date(2022, 1, 1),
        )

        officer.verified_military_months = 48
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["type"] == "MILITARY"
        assert pathway["service_years"] == 4
        assert pathway["military_years"] == 4


def test_military_month_boundary_is_enforced(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2020, 1, 1),
        )

        officer.verified_military_months = 23

        add_training(
            agency,
            officer,
            100,
        )

        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "NOT_ELIGIBLE"

        military = result[
            "pathway_results"
        ]["military"][0]

        assert military[
            "required_military_months"
        ] == 24
        assert military[
            "actual_military_months"
        ] == 23
        assert military[
            "military_months_short"
        ] == 1
        assert military["satisfied"] is False


def test_intermediate_certificate_is_required(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2016, 1, 1),
            include_basic=True,
            include_intermediate=False,
        )

        add_training(
            agency,
            officer,
            1000,
        )
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert (
            "Intermediate Jailer certificate"
            in result["missing_requirements"]
        )


def test_missing_basic_and_intermediate_are_both_reported(
    app,
):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2016, 1, 1),
            include_basic=False,
            include_intermediate=False,
        )

        add_training(
            agency,
            officer,
            1000,
        )
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "NOT_ELIGIBLE"

        assert (
            "Basic Jailer certificate"
            in result["missing_requirements"]
        )
        assert (
            "Intermediate Jailer certificate"
            in result["missing_requirements"]
        )


def test_best_service_training_path_reports_hours_short(
    app,
):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2020, 1, 1),
        )

        officer.verified_military_months = 0

        add_training(
            agency,
            officer,
            1000,
        )
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "NOT_ELIGIBLE"

        best = result[
            "best_available_pathway"
        ]

        assert best["type"] == (
            "SERVICE_TRAINING"
        )
        assert best["service_years"] == 6
        assert best["training_hours"] == 1200
        assert best["training_hours_short"] == 200.0

        assert (
            "200 additional training hours"
            in result["missing_requirements"]
        )


def test_known_qualifying_military_path_can_be_best(
    app,
):
    with app.app_context():
        _, officer = make_jailer(
            service_start=date(2020, 1, 1),
        )

        officer.verified_military_months = 23
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        military = result[
            "pathway_results"
        ]["military"][0]

        assert military["service_years_short"] == 0
        assert military["military_months_short"] == 1


def test_tcole_degree_award_is_used(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2020, 1, 1),
        )

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name=(
                    "Academic Recognition Award - "
                    "Associate Degree"
                ),
                award_date=date(2025, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["education_level"] == (
            "ASSOCIATE"
        )
        assert result["status"] == "ELIGIBLE"


def test_master_certificate_satisfies_advanced(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_certificate(
            agency,
            officer,
            "Master Jailer Proficiency",
        )
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "AWARDED"
        assert (
            result["current_certificate"]
            == "Master Jailer"
        )


def test_advanced_certificate_is_awarded(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_certificate(
            agency,
            officer,
            "Advanced Jailer Proficiency",
        )
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "AWARDED"
        assert (
            result["current_certificate"]
            == "Advanced Jailer"
        )


def test_missing_service_date_is_insufficient_data(app):
    with app.app_context():
        _, officer = make_jailer()

        officer.jailer_service_start_date = None
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == (
            "INSUFFICIENT_DATA"
        )
        assert (
            "County Jailer license/service start date"
            in result[
                "insufficient_data_requirements"
            ]
        )


def test_non_jailer_is_not_applicable(app):
    with app.app_context():
        agency = Agency(
            name="Test Police Department"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="999999",
            first_name="JANE",
            last_name="DOE",
        )
        db.session.add(officer)
        db.session.commit()

        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == (
            "NOT_APPLICABLE"
        )
