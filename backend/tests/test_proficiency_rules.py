from datetime import date

import pytest

from app.compliance.proficiency_rules import (
    load_proficiency_rule,
)


def test_basic_rule_loads():
    rule = load_proficiency_rule(
        "Basic Peace Officer",
        evaluation_date=date(2026, 8, 9),
    )

    assert rule["rule_version"] == "2026-02-09"
    assert len(rule["required_courses"]) == 7


def test_intermediate_rule_has_18_categories():
    rule = load_proficiency_rule(
        "Intermediate Peace Officer",
        evaluation_date=date(2026, 8, 9),
    )

    assert len(rule["required_courses"]) == 18


def test_intermediate_special_topics_group():
    rule = load_proficiency_rule(
        "Intermediate Peace Officer",
        evaluation_date=date(2026, 8, 9),
    )

    special = next(
        requirement
        for requirement in rule["required_courses"]
        if requirement["id"]
        == "SPECIAL_INVESTIGATIVE_TOPICS"
    )

    group = special["accepted_course_groups"][0]

    assert group["courses"] == [
        "3261",
        "3262",
        "3263",
    ]
    assert group["require_all"] is True
    assert group["same_two_year_unit"] is True


def test_intermediate_legacy_sit_cutoff():
    rule = load_proficiency_rule(
        "Intermediate Peace Officer",
        evaluation_date=date(2026, 8, 9),
    )

    special = next(
        requirement
        for requirement in rule["required_courses"]
        if requirement["id"]
        == "SPECIAL_INVESTIGATIVE_TOPICS"
    )

    legacy = special["dated_equivalencies"][0]

    assert legacy["completed_before"] == "2013-12-31"
    assert set(legacy["courses"]) == {
        "3214",
        "3224",
        "3244",
        "3254",
    }


def test_advanced_rule_has_8_categories():
    rule = load_proficiency_rule(
        "Advanced Peace Officer",
        evaluation_date=date(2026, 8, 9),
    )

    assert len(rule["required_courses"]) == 8


def test_master_requires_ics_300_and_400():
    rule = load_proficiency_rule(
        "Master Peace Officer",
        evaluation_date=date(2026, 8, 9),
    )

    courses = {
        item["accepted_courses"][0]
        for item in rule["required_courses"]
    }

    assert courses == {"66300", "66400"}


def test_rule_refuses_pre_effective_date():
    with pytest.raises(ValueError):
        load_proficiency_rule(
            "Intermediate Peace Officer",
            evaluation_date=date(2026, 2, 8),
        )
