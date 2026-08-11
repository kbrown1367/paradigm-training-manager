from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.jailer_proficiency import (
    evaluate_master_jailer_proficiency,
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
    service_start=date(2000, 1, 1),
    include_basic=True,
    include_intermediate=True,
    include_advanced=True,
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
                award_date=date(2002, 1, 1),
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
                award_date=date(2005, 1, 1),
            )
        )

    if include_advanced:
        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name=(
                    "Advanced Jailer Proficiency"
                ),
                award_date=date(2010, 1, 1),
            )
        )

    db.session.commit()

    return agency, officer


def add_training(
    agency,
    officer,
    hours,
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="9000",
            course_title="Training",
            course_date=date(2025, 1, 1),
            credited_hours=Decimal(str(hours)),
            hours_source="TCOLE_CYCLE_REPORT",
            source="TCOLE",
        )
    )


@pytest.mark.parametrize(
    (
        "service_start",
        "hours",
        "expected_years",
    ),
    [
        (date(2006, 1, 1), 1200, 20),
        (date(2011, 1, 1), 2400, 15),
        (date(2014, 1, 1), 3300, 12),
        (date(2016, 1, 1), 4000, 10),
    ],
)
def test_service_training_pathways(
    app,
    service_start,
    hours,
    expected_years,
):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=service_start
        )

        add_training(
            agency,
            officer,
            hours,
        )
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["type"] == (
            "SERVICE_TRAINING"
        )
        assert pathway["service_years"] == (
            expected_years
        )
        assert pathway["training_hours"] == hours


@pytest.mark.parametrize(
    (
        "service_start",
        "education",
        "expected_years",
    ),
    [
        (date(2014, 1, 1), "ASSOCIATE", 12),
        (date(2017, 1, 1), "BACHELOR", 9),
        (date(2019, 1, 1), "MASTER", 7),
        (date(2021, 1, 1), "DOCTORATE", 5),
    ],
)
def test_education_pathways(
    app,
    service_start,
    education,
    expected_years,
):
    with app.app_context():
        _, officer = make_jailer(
            service_start=service_start
        )

        officer.verified_education_level = education
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["type"] == "EDUCATION"
        assert pathway["service_years"] == (
            expected_years
        )
        assert pathway["education_level"] == education


@pytest.mark.parametrize(
    (
        "service_start",
        "months",
        "expected_years",
        "expected_military_years",
    ),
    [
        (date(2014, 1, 1), 24, 12, 2),
        (date(2017, 1, 1), 48, 9, 4),
        (date(2019, 1, 1), 60, 7, 5),
        (date(2021, 1, 1), 96, 5, 8),
    ],
)
def test_military_pathways(
    app,
    service_start,
    months,
    expected_years,
    expected_military_years,
):
    with app.app_context():
        _, officer = make_jailer(
            service_start=service_start
        )

        officer.verified_military_months = months
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        pathway = result["qualifying_pathway"]

        assert pathway["type"] == "MILITARY"
        assert pathway["service_years"] == (
            expected_years
        )
        assert pathway["military_years"] == (
            expected_military_years
        )


@pytest.mark.parametrize(
    (
        "service_start",
        "months",
        "required_months",
    ),
    [
        (date(2014, 1, 1), 23, 24),
        (date(2017, 1, 1), 47, 48),
        (date(2019, 1, 1), 59, 60),
        (date(2021, 1, 1), 95, 96),
    ],
)
def test_military_month_boundaries(
    app,
    service_start,
    months,
    required_months,
):
    with app.app_context():
        _, officer = make_jailer(
            service_start=service_start
        )

        officer.verified_military_months = months
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        pathway = next(
            item
            for item in result[
                "pathway_results"
            ]["military"]
            if item[
                "required_military_months"
            ] == required_months
        )

        assert pathway[
            "actual_military_months"
        ] == months
        assert pathway[
            "military_months_short"
        ] == 1
        assert pathway["satisfied"] is False


def test_advanced_certificate_is_required(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2000, 1, 1),
            include_advanced=False,
        )

        add_training(
            agency,
            officer,
            5000,
        )
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert (
            "Advanced Jailer certificate"
            in result["missing_requirements"]
        )


def test_all_missing_prerequisites_are_reported(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2000, 1, 1),
            include_basic=False,
            include_intermediate=False,
            include_advanced=False,
        )

        add_training(
            agency,
            officer,
            5000,
        )
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
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
        assert (
            "Advanced Jailer certificate"
            in result["missing_requirements"]
        )


def test_higher_degree_satisfies_lower_pathway(app):
    with app.app_context():
        _, officer = make_jailer(
            service_start=date(2014, 1, 1),
        )

        officer.verified_education_level = (
            "DOCTORATE"
        )
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"

        associate = result[
            "pathway_results"
        ]["education"][0]

        assert associate["education_met"] is True


def test_master_certificate_is_awarded(app):
    with app.app_context():
        agency, officer = make_jailer()

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name=(
                    "Master Jailer Proficiency"
                ),
                award_date=date(2025, 1, 1),
            )
        )
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "AWARDED"
        assert (
            result["current_certificate"]
            == "Master Jailer"
        )


def test_missing_service_date_is_insufficient_data(
    app,
):
    with app.app_context():
        _, officer = make_jailer()

        officer.jailer_service_start_date = None
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
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

        result = evaluate_master_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == (
            "NOT_APPLICABLE"
        )


def test_best_service_training_path_reports_hours_short(
    app,
):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2014, 1, 1),
        )

        officer.verified_military_months = 0

        add_training(
            agency,
            officer,
            3200,
        )
        db.session.commit()

        result = evaluate_master_jailer_proficiency(
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
        assert best["service_years"] == 12
        assert best["training_hours"] == 3300
        assert best["training_hours_short"] == 100.0

        assert (
            "100 additional training hours"
            in result["missing_requirements"]
        )
