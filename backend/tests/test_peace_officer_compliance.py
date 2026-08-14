from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.credentials import (
    get_highest_peace_officer_certificate,
)
from app.compliance.peace_officer_unit import (
    evaluate_agency_peace_officers,
    evaluate_peace_officer_unit,
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
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def make_officer():
    agency = Agency(name="Test Police Department")
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="JOHN",
        last_name="SMITH",
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

    return agency, officer


def add_award(
    agency,
    officer,
    name,
    award_date,
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


def add_training(
    agency,
    officer,
    course_number,
    course_date,
    hours,
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=course_number,
            course_title=f"Course {course_number}",
            course_date=course_date,
            credited_hours=Decimal(str(hours)),
            hours_source="TCOLE_CYCLE_REPORT",
        )
    )


def add_complete_unit_training(agency, officer):
    add_training(
        agency, officer, "3311",
        date(2024, 1, 1), 16
    )
    add_training(
        agency, officer, "3189",
        date(2026, 1, 10), 8
    )
    add_training(
        agency, officer, "7006",
        date(2026, 2, 10), 8
    )
    add_training(
        agency, officer, "3369",
        date(2026, 3, 10), 16
    )
    add_training(
        agency, officer, "9999",
        date(2026, 4, 10), 8
    )


def test_highest_certificate_uses_hierarchy(app):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Basic Peace Officer",
            date(2020, 1, 1),
        )
        add_award(
            agency,
            officer,
            "Master Peace Officer",
            date(2025, 1, 1),
        )
        add_award(
            agency,
            officer,
            "Advanced Peace Officer",
            date(2026, 1, 1),
        )

        db.session.commit()

        result = get_highest_peace_officer_certificate(
            officer
        )

        assert (
            result["highest_certificate"]
            == "Master Peace Officer"
        )
        assert result["certificate_level"] == "MASTER"
        assert (
            result["highest_certificate_date"]
            == "2025-01-01"
        )


def test_complete_officer(app):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Advanced Peace Officer",
            date(2024, 1, 1),
        )

        add_complete_unit_training(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["unit_status"] == "COMPLETE"
        assert result["requirement_status"] == "SATISFIED"
        assert result["highest_certificate"] == (
            "Advanced Peace Officer"
        )
        assert result["certificate_level"] == "ADVANCED"
        assert result["total_hours"] == 40.0
        assert result["alerrt_hours"] == 16.0
        assert result["requirements"] == []


def test_missing_requirements_are_outstanding_before_due_date(app):
    with app.app_context():
        _, officer = make_officer()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["unit_status"] == "OUTSTANDING"
        assert result["requirement_status"] == "OUTSTANDING"
        assert result["due_date"] == "2027-08-31"

        assert all(
            item["status"] == "OUTSTANDING"
            for item in result["requirements"]
        )


def test_requirements_reset_into_new_unit_after_prior_due_date(app):
    with app.app_context():
        _, officer = make_officer()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2027, 9, 1),
        )

        assert result["unit_number"] == 2
        assert result["unit_start"] == "2027-09-01"
        assert result["unit_end"] == "2029-08-31"
        assert result["unit_status"] == "OUTSTANDING"
        assert result["requirement_status"] == "OUTSTANDING"

        assert all(
            item["status"] == "OUTSTANDING"
            for item in result["requirements"]
        )


def test_prior_3313_satisfies_level_one_history(app):
    with app.app_context():
        agency, officer = make_officer()

        add_training(
            agency, officer, "3313",
            date(2022, 5, 1), 16
        )
        add_training(
            agency, officer, "3189",
            date(2026, 1, 10), 8
        )
        add_training(
            agency, officer, "7006",
            date(2026, 2, 10), 8
        )
        add_training(
            agency, officer, "3369",
            date(2026, 3, 10), 16
        )
        add_training(
            agency, officer, "9999",
            date(2026, 4, 10), 8
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["prior_level_one_found"] is True
        assert result["alerrt_level_one_satisfied"] is True
        assert result["unit_status"] == "COMPLETE"


def test_bpoc_736_prior_completion_satisfies_level_one(app):
    with app.app_context():
        agency, officer = make_officer()

        add_training(
            agency, officer, "1000736",
            date(2024, 12, 3), 736
        )
        add_training(
            agency, officer, "3189",
            date(2026, 1, 10), 8
        )
        add_training(
            agency, officer, "7006",
            date(2026, 2, 10), 8
        )
        add_training(
            agency, officer, "3369",
            date(2026, 3, 10), 16
        )
        add_training(
            agency, officer, "9999",
            date(2026, 4, 10), 8
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["prior_level_one_found"] is True
        assert result["alerrt_level_one_satisfied"] is True
        assert not any(
            item["type"] == "ALERRT_LEVEL_ONE"
            for item in result["requirements"]
        )


def test_bpoc_736_current_unit_supplies_embedded_alerrt(app):
    with app.app_context():
        agency, officer = make_officer()

        add_training(
            agency, officer, "1000736",
            date(2025, 12, 4), 736
        )
        add_training(
            agency, officer, "3189",
            date(2026, 1, 10), 8
        )
        add_training(
            agency, officer, "7006",
            date(2026, 2, 10), 8
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["alerrt_level_one_satisfied"] is True
        assert result["alerrt_hours"] == 16.0
        assert result["remaining_alerrt_hours"] == 0.0

        assert not any(
            item["type"] in {
                "ALERRT_LEVEL_ONE",
                "ALERRT_HOURS",
            }
            for item in result["requirements"]
        )



def test_training_outside_unit_does_not_count(app):
    with app.app_context():
        agency, officer = make_officer()

        add_training(
            agency, officer, "3311",
            date(2024, 1, 1), 16
        )
        add_training(
            agency, officer, "3189",
            date(2026, 1, 10), 8
        )
        add_training(
            agency, officer, "7006",
            date(2026, 2, 10), 8
        )
        add_training(
            agency, officer, "3369",
            date(2026, 3, 10), 16
        )
        add_training(
            agency, officer, "9999",
            date(2024, 5, 1), 100
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["total_hours"] == 32.0
        assert result["remaining_total_hours"] == 8.0
        assert result["unit_status"] == "OUTSTANDING"


def test_license_applicability_is_provisional(app):
    with app.app_context():
        _, officer = make_officer()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        assert (
            result["applicability_status"]
            == "PROVISIONAL"
        )
        assert result["license_status"] == "UNVERIFIED"


def test_non_peace_officer_excluded_from_agency_results(app):
    with app.app_context():
        agency = Agency(name="Test Police Department")
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

        result = evaluate_agency_peace_officers(
            agency.id,
            evaluation_date=date(2026, 8, 8),
        )

        assert result["officer_count"] == 0
        assert result["officers"] == []


def test_unit_requirements_reset_when_second_unit_begins(app):
    with app.app_context():
        agency, officer = make_officer()

        add_training(
            agency, officer, "3311",
            date(2024, 1, 1), 16
        )
        add_training(
            agency, officer, "3189",
            date(2026, 1, 10), 8
        )
        add_training(
            agency, officer, "7006",
            date(2026, 2, 10), 8
        )
        add_training(
            agency, officer, "3369",
            date(2026, 3, 10), 16
        )
        add_training(
            agency, officer, "9999",
            date(2026, 4, 10), 8
        )

        db.session.commit()

        first_unit = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        second_unit = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2027, 9, 1),
        )

        assert first_unit["unit_status"] == "COMPLETE"

        assert second_unit["unit_number"] == 2
        assert second_unit["unit_start"] == "2027-09-01"
        assert second_unit["unit_end"] == "2029-08-31"

        assert second_unit["total_hours"] == 0.0
        assert second_unit["remaining_total_hours"] == 40.0

        assert second_unit["required_courses"][0]["status"] == "OUTSTANDING"
        assert second_unit["required_courses"][1]["status"] == "OUTSTANDING"

        assert second_unit["alerrt_hours"] == 0.0
        assert second_unit["remaining_alerrt_hours"] == 16.0


def test_compliance_engine_moves_into_next_four_year_cycle(app):
    with app.app_context():
        _, officer = make_officer()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2030, 1, 1),
        )

        assert result["cycle_start"] == "2029-09-01"
        assert result["cycle_end"] == "2033-08-31"
        assert result["unit_number"] == 1
        assert result["unit_start"] == "2029-09-01"
        assert result["unit_end"] == "2031-08-31"


def test_bpoc_736_prior_completion_satisfies_3189(app):
    with app.app_context():
        agency, officer = make_officer()

        add_training(
            agency,
            officer,
            "1000736",
            date(2024, 12, 3),
            736,
        )
        add_training(
            agency,
            officer,
            "7006",
            date(2026, 2, 10),
            8,
        )
        add_training(
            agency,
            officer,
            "3369",
            date(2026, 3, 10),
            16,
        )
        add_training(
            agency,
            officer,
            "9999",
            date(2026, 4, 10),
            16,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        legislative_update = next(
            item
            for item in result["required_courses"]
            if item["course_number"] == "3189"
        )

        assert legislative_update["completed"] is True
        assert (
            legislative_update["satisfaction_basis"]
            == "EQUIVALENCY"
        )

        assert not any(
            item.get("course_number") == "3189"
            for item in result["requirements"]
        )

        # Historical BPOC must not add 736 hours
        # to the current training-unit total.
        assert result["total_hours"] == 40.0

        # Preserve the existing BPOC/ALERRT behavior.
        assert result["prior_level_one_found"] is True
        assert (
            result["alerrt_level_one_satisfied"]
            is True
        )


def test_bpoc_736_current_unit_satisfies_3189(app):
    with app.app_context():
        agency, officer = make_officer()

        add_training(
            agency,
            officer,
            "1000736",
            date(2025, 12, 4),
            736,
        )
        add_training(
            agency,
            officer,
            "7006",
            date(2026, 2, 10),
            8,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        legislative_update = next(
            item
            for item in result["required_courses"]
            if item["course_number"] == "3189"
        )

        assert legislative_update["completed"] is True
        assert (
            legislative_update["satisfaction_basis"]
            == "EQUIVALENCY"
        )

        assert (
            result["alerrt_level_one_satisfied"]
            is True
        )
        assert result["alerrt_hours"] == 16.0


def test_3189_remains_outstanding_without_direct_or_bpoc_credit(
    app,
):
    with app.app_context():
        agency, officer = make_officer()

        add_training(
            agency,
            officer,
            "7006",
            date(2026, 2, 10),
            8,
        )
        add_training(
            agency,
            officer,
            "3369",
            date(2026, 3, 10),
            16,
        )
        add_training(
            agency,
            officer,
            "9999",
            date(2026, 4, 10),
            16,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        legislative_update = next(
            item
            for item in result["required_courses"]
            if item["course_number"] == "3189"
        )

        assert legislative_update["completed"] is False
        assert (
            legislative_update["satisfaction_basis"]
            is None
        )

        assert any(
            item.get("course_number") == "3189"
            for item in result["requirements"]
        )


def test_direct_3189_still_reports_direct_satisfaction(app):
    with app.app_context():
        agency, officer = make_officer()

        add_training(
            agency,
            officer,
            "3189",
            date(2026, 1, 10),
            8,
        )
        add_training(
            agency,
            officer,
            "7006",
            date(2026, 2, 10),
            8,
        )
        add_training(
            agency,
            officer,
            "3369",
            date(2026, 3, 10),
            16,
        )
        add_training(
            agency,
            officer,
            "9999",
            date(2026, 4, 10),
            8,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 8),
        )

        legislative_update = next(
            item
            for item in result["required_courses"]
            if item["course_number"] == "3189"
        )

        assert legislative_update["completed"] is True
        assert (
            legislative_update["satisfaction_basis"]
            == "DIRECT"
        )


def test_below_intermediate_requires_four_cycle_courses(app):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Basic Peace Officer",
            date(2025, 1, 1),
        )

        add_complete_unit_training(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        assert (
            result["cycle_requirements_applicable"]
            is True
        )
        assert result["unit_status"] == "COMPLETE"
        assert result["cycle_status"] == "OUTSTANDING"
        assert (
            result["compliance_status"]
            == "OUTSTANDING"
        )

        required = {
            item["id"]
            for item in result[
                "cycle_required_courses"
            ]
        }

        assert required == {
            "CRISIS_INTERVENTION",
            "CULTURAL_DIVERSITY",
            "SPECIAL_INVESTIGATIVE_TOPICS",
            "DE_ESCALATION",
        }

        assert len(
            result["cycle_requirements"]
        ) == 4

        assert all(
            item["due_date"] == "2029-08-31"
            for item in result[
                "cycle_requirements"
            ]
        )


def test_prior_cycle_cit_does_not_satisfy_current_cycle(app):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Basic Peace Officer",
            date(2025, 1, 1),
        )

        add_training(
            agency,
            officer,
            "1850",
            date(2024, 12, 3),
            40,
        )

        add_complete_unit_training(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        cit = next(
            item
            for item in result[
                "cycle_required_courses"
            ]
            if item["id"] == "CRISIS_INTERVENTION"
        )

        assert cit["completed"] is False

        assert any(
            item["type"]
            == "PEACE_OFFICER_CYCLE_COURSE"
            and item["accepted_courses"]
            == ["3843", "1850"]
            for item in result[
                "cycle_requirements"
            ]
        )


@pytest.mark.parametrize(
    "cit_course",
    [
        "3843",
        "1850",
    ],
)
def test_current_cycle_cit_options_satisfy_cycle_requirement(
    app,
    cit_course,
):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Basic Peace Officer",
            date(2025, 1, 1),
        )

        add_complete_unit_training(
            agency,
            officer,
        )

        add_training(
            agency,
            officer,
            cit_course,
            date(2026, 5, 1),
            8,
        )
        add_training(
            agency,
            officer,
            "3939",
            date(2026, 5, 2),
            8,
        )
        add_training(
            agency,
            officer,
            "3232",
            date(2026, 5, 3),
            8,
        )
        add_training(
            agency,
            officer,
            "1849",
            date(2026, 5, 4),
            8,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        assert result["cycle_status"] == "COMPLETE"
        assert result["cycle_requirements"] == []
        assert (
            result["compliance_status"]
            == "COMPLETE"
        )


def test_cycle_course_completed_in_unit_one_counts_in_unit_two(
    app,
):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Basic Peace Officer",
            date(2025, 1, 1),
        )

        add_training(
            agency,
            officer,
            "1850",
            date(2026, 5, 1),
            40,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2028, 1, 1),
        )

        assert result["unit_number"] == 2

        cit = next(
            item
            for item in result[
                "cycle_required_courses"
            ]
            if item["id"] == "CRISIS_INTERVENTION"
        )

        assert cit["completed"] is True


@pytest.mark.parametrize(
    "certificate_name",
    [
        "Intermediate Peace Officer",
        "Advanced Peace Officer",
        "Master Peace Officer",
    ],
)
def test_intermediate_or_higher_suppresses_cycle_courses(
    app,
    certificate_name,
):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            certificate_name,
            date(2025, 1, 1),
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        assert (
            result["cycle_requirements_applicable"]
            is False
        )
        assert (
            result["cycle_status"]
            == "NOT_APPLICABLE"
        )
        assert result["cycle_requirements"] == []
        assert result["cycle_required_courses"] == []


def test_historical_bpoc_736_does_not_satisfy_current_cycle_courses(
    app,
):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Basic Peace Officer",
            date(2025, 1, 1),
        )

        add_training(
            agency,
            officer,
            "1000736",
            date(2024, 8, 20),
            736,
        )

        add_complete_unit_training(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        assert (
            result["cycle_requirements_applicable"]
            is True
        )
        assert result["cycle_status"] == "OUTSTANDING"

        assert len(
            result["cycle_requirements"]
        ) == 4

        assert all(
            item["completed"] is False
            for item in result[
                "cycle_required_courses"
            ]
        )


def test_current_cycle_bpoc_736_satisfies_all_cycle_courses(
    app,
):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Basic Peace Officer",
            date(2026, 6, 1),
        )

        add_training(
            agency,
            officer,
            "1000736",
            date(2026, 5, 26),
            736,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2026, 8, 14),
        )

        assert (
            result["cycle_requirements_applicable"]
            is True
        )

        assert result["cycle_status"] == "COMPLETE"
        assert result["cycle_requirements"] == []

        assert len(
            result["cycle_required_courses"]
        ) == 4

        for requirement in result[
            "cycle_required_courses"
        ]:
            assert requirement["completed"] is True
            assert (
                requirement[
                    "completed_equivalent_courses"
                ]
                == ["1000736"]
            )


def test_bpoc_736_in_unit_one_counts_in_unit_two_cycle_courses(
    app,
):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Basic Peace Officer",
            date(2026, 6, 1),
        )

        add_training(
            agency,
            officer,
            "1000736",
            date(2026, 5, 26),
            736,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2028, 1, 1),
        )

        assert result["unit_number"] == 2
        assert result["cycle_status"] == "COMPLETE"
        assert result["cycle_requirements"] == []

        assert all(
            item["completed"] is True
            for item in result[
                "cycle_required_courses"
            ]
        )


def test_prior_cycle_bpoc_736_does_not_carry_into_next_cycle(
    app,
):
    with app.app_context():
        agency, officer = make_officer()

        add_award(
            agency,
            officer,
            "Basic Peace Officer",
            date(2026, 6, 1),
        )

        add_training(
            agency,
            officer,
            "1000736",
            date(2026, 5, 26),
            736,
        )

        db.session.commit()

        result = evaluate_peace_officer_unit(
            officer,
            evaluation_date=date(2029, 9, 1),
        )

        assert result["cycle_start"] == "2029-09-01"
        assert result["cycle_end"] == "2033-08-31"

        assert (
            result["cycle_requirements_applicable"]
            is True
        )

        assert result["cycle_status"] == "OUTSTANDING"

        assert len(
            result["cycle_requirements"]
        ) == 4

        assert all(
            item["completed"] is False
            for item in result[
                "cycle_required_courses"
            ]
        )
