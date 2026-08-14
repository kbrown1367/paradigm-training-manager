# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import json
from datetime import date
from pathlib import Path


RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "jailer_proficiency_basic.json"
)


JAILER_CERTIFICATE_SEQUENCE = (
    "Basic Jailer",
    "Intermediate Jailer",
    "Advanced Jailer",
    "Master Jailer",
)


JAILER_CERTIFICATE_ALIASES = {
    "Basic Jailer": {
        "Basic Jailer",
    },
    "Intermediate Jailer": {
        "Intermediate Jailer",
        "Intermediate Jailer Proficiency",
    },
    "Advanced Jailer": {
        "Advanced Jailer",
        "Advanced Jailer Proficiency",
    },
    "Master Jailer": {
        "Master Jailer",
        "Master Jailer Proficiency",
    },
}


def load_basic_jailer_rule():
    with RULE_PATH.open() as file:
        return json.load(file)


def _normalize_award_name(value):
    return " ".join(
        (value or "").strip().split()
    )


def get_highest_jailer_certificate(officer):
    certificate_dates = {}

    for award in officer.awards:
        if award.award_type != "Certificate":
            continue

        normalized_name = _normalize_award_name(
            award.award_name
        )

        for canonical, aliases in (
            JAILER_CERTIFICATE_ALIASES.items()
        ):
            if normalized_name not in aliases:
                continue

            existing = certificate_dates.get(canonical)

            if (
                existing is None
                or award.award_date > existing
            ):
                certificate_dates[canonical] = (
                    award.award_date
                )

    highest = None

    for certificate in JAILER_CERTIFICATE_SEQUENCE:
        if certificate in certificate_dates:
            highest = certificate

    if highest is None:
        return {
            "highest_certificate": None,
            "highest_certificate_date": None,
            "certificate_level": None,
        }

    return {
        "highest_certificate": highest,
        "highest_certificate_date": (
            certificate_dates[highest].isoformat()
        ),
        "certificate_level": (
            highest
            .replace(" Jailer", "")
            .upper()
        ),
    }


def has_jailer_license(officer):
    return any(
        award.award_type == "License"
        and _normalize_award_name(
            award.award_name
        )
        in {
            "Jailer License",
            "County Jailer License",
        }
        for award in officer.awards
    )


def _service_years(
    officer,
    evaluation_date,
):
    start_date = officer.jailer_service_start_date

    if start_date is None:
        return None

    if start_date > evaluation_date:
        return None

    years = evaluation_date.year - start_date.year

    if (
        evaluation_date.month,
        evaluation_date.day,
    ) < (
        start_date.month,
        start_date.day,
    ):
        years -= 1

    return years


def _find_course(
    officer,
    course_number,
):
    matches = [
        record
        for record in officer.training_records
        if record.course_number == course_number
    ]

    if not matches:
        return None

    return min(
        matches,
        key=lambda record: record.course_date,
    )


def _course_requirement_result(
    officer,
    requirement,
    jailer_license_date,
):
    applicability = requirement.get(
        "applicability"
    ) or {}

    applicability_type = applicability.get("type")

    required = True
    insufficient_data = False

    if (
        applicability_type
        == "LICENSE_DATE_ON_OR_AFTER"
    ):
        if jailer_license_date is None:
            required = False
            insufficient_data = True
        else:
            threshold = date.fromisoformat(
                applicability["date"]
            )
            required = (
                jailer_license_date >= threshold
            )

    match = (
        _find_course(
            officer,
            requirement["course_number"],
        )
        if required
        else None
    )

    if insufficient_data:
        status = "INSUFFICIENT_DATA"
    elif not required:
        status = "NOT_APPLICABLE"
    elif match is not None:
        status = "COMPLETE"
    else:
        status = "MISSING"

    return {
        "course_number":
            requirement["course_number"],
        "name": requirement["name"],
        "required": required,
        "status": status,
        "applicability":
            applicability,
        "matched_course": (
            {
                "course_number":
                    match.course_number,
                "course_title":
                    match.course_title,
                "course_date":
                    match.course_date.isoformat(),
            }
            if match is not None
            else None
        ),
    }


def evaluate_basic_jailer_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_basic_jailer_rule()

    credential = get_highest_jailer_certificate(
        officer
    )

    has_license = has_jailer_license(officer)

    jailer_license_date = (
        officer.jailer_service_start_date
    )

    service_years = _service_years(
        officer,
        evaluation_date,
    )

    course_requirements = [
        _course_requirement_result(
            officer,
            requirement,
            jailer_license_date,
        )
        for requirement in rule["required_courses"]
    ]

    missing_courses = [
        item
        for item in course_requirements
        if item["status"] == "MISSING"
    ]

    insufficient_courses = [
        item
        for item in course_requirements
        if item["status"] == "INSUFFICIENT_DATA"
    ]

    minimum_service_years = (
        rule["minimum_service_years"]
    )

    service_requirement_met = (
        service_years is not None
        and service_years
        >= minimum_service_years
    )

    existing_level = (
        credential["certificate_level"]
    )

    if existing_level in {
        "BASIC",
        "INTERMEDIATE",
        "ADVANCED",
        "MASTER",
    }:
        status = "AWARDED"

    elif not has_license:
        status = "NOT_APPLICABLE"

    elif (
        jailer_license_date is None
        or service_years is None
        or insufficient_courses
    ):
        status = "INSUFFICIENT_DATA"

    elif not service_requirement_met:
        status = "NOT_ELIGIBLE"

    elif missing_courses:
        status = "NOT_ELIGIBLE"

    else:
        status = "ELIGIBLE"

    missing_requirements = []

    if (
        has_license
        and service_years is not None
        and not service_requirement_met
    ):
        missing_requirements.append(
            (
                f"{minimum_service_years} year "
                "of qualifying County Jailer service"
            )
        )

    missing_requirements.extend(
        (
            f"{item['name']} "
            f"(#{item['course_number']})"
        )
        for item in missing_courses
    )

    insufficient_data_requirements = []

    if has_license and jailer_license_date is None:
        insufficient_data_requirements.append(
            "County Jailer license/service start date"
        )

    insufficient_data_requirements.extend(
        (
            f"{item['name']} "
            f"(#{item['course_number']})"
        )
        for item in insufficient_courses
    )

    return {
        "certificate": "Basic Jailer",
        "status": status,
        "current_certificate":
            credential["highest_certificate"],
        "current_certificate_date":
            credential["highest_certificate_date"],
        "certificate_level":
            credential["certificate_level"],
        "has_jailer_license": has_license,
        "jailer_license_date": (
            jailer_license_date.isoformat()
            if jailer_license_date
            else None
        ),
        "service_years": service_years,
        "minimum_service_years":
            minimum_service_years,
        "service_requirement_met":
            service_requirement_met,
        "course_requirements":
            course_requirements,
        "missing_requirements":
            missing_requirements,
        "insufficient_data_requirements":
            insufficient_data_requirements,
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["rule_version"],
    }


INTERMEDIATE_RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "jailer_proficiency_intermediate.json"
)


JAILER_EDUCATION_RANK = {
    "ASSOCIATE": 1,
    "BACHELOR": 2,
    "MASTER": 3,
    "DOCTORATE": 4,
}


def load_intermediate_jailer_rule():
    with INTERMEDIATE_RULE_PATH.open() as file:
        return json.load(file)


def _jailer_certificate_dates(officer):
    certificate_dates = {}

    for award in officer.awards:
        if award.award_type != "Certificate":
            continue

        normalized_name = _normalize_award_name(
            award.award_name
        )

        for canonical, aliases in (
            JAILER_CERTIFICATE_ALIASES.items()
        ):
            if normalized_name not in aliases:
                continue

            existing = certificate_dates.get(canonical)

            if (
                existing is None
                or award.award_date > existing
            ):
                certificate_dates[canonical] = (
                    award.award_date
                )

    return certificate_dates


def _jailer_training_hours(officer):
    total = 0.0

    for record in officer.training_records:
        if record.credited_hours is None:
            continue

        total += float(record.credited_hours)

    return total


def _jailer_education_level(officer):
    """
    Resolve education using the same factual hierarchy
    as the Peace Officer proficiency engine:

    1. Specific TCOLE academic recognition.
    2. Agency-verified education when TCOLE does not
       report a specific degree level.

    A generic Academic Recognition Award does not tell
    PTM which degree level was earned.
    """

    recognized = {
        "Academic Recognition Award - Associate Degree":
            "ASSOCIATE",
        "Academic Recognition Award - Bachelor Degree":
            "BACHELOR",
        "Academic Recognition Award - Master Degree":
            "MASTER",
        "Academic Recognition Award - Doctorate Degree":
            "DOCTORATE",
    }

    highest = None

    for award in officer.awards:
        normalized_name = _normalize_award_name(
            award.award_name
        )

        level = recognized.get(normalized_name)

        if level is None:
            continue

        if (
            highest is None
            or JAILER_EDUCATION_RANK[level]
            > JAILER_EDUCATION_RANK[highest]
        ):
            highest = level

    if highest is not None:
        return highest

    verified = officer.verified_education_level

    if verified in JAILER_EDUCATION_RANK:
        return verified

    return None


def _find_any_course(
    officer,
    accepted_courses,
):
    accepted = set(accepted_courses)

    matches = [
        record
        for record in officer.training_records
        if record.course_number in accepted
    ]

    if not matches:
        return None

    return min(
        matches,
        key=lambda record: record.course_date,
    )


def _intermediate_course_requirement_result(
    officer,
    requirement,
    basic_certificate_date,
):
    applicability = (
        requirement.get("applicability") or {}
    )

    applicability_type = applicability.get("type")

    required = True
    insufficient_data = False

    if (
        applicability_type
        == "BASIC_CERTIFICATE_ON_OR_AFTER"
    ):
        if basic_certificate_date is None:
            required = False
            insufficient_data = True
        else:
            threshold = date.fromisoformat(
                applicability["date"]
            )

            # The controlling chart states "after
            # March 1, 1993." A certificate dated
            # March 1 itself therefore does not trigger
            # the additional course categories.
            required = (
                basic_certificate_date > threshold
            )

    match = (
        _find_any_course(
            officer,
            requirement["accepted_courses"],
        )
        if required
        else None
    )

    if insufficient_data:
        status = "INSUFFICIENT_DATA"
    elif not required:
        status = "NOT_APPLICABLE"
    elif match is not None:
        status = "COMPLETE"
    else:
        status = "MISSING"

    return {
        "id": requirement["id"],
        "name": requirement["name"],
        "accepted_courses":
            requirement["accepted_courses"],
        "required": required,
        "status": status,
        "applicability": applicability,
        "matched_course": (
            {
                "course_number":
                    match.course_number,
                "course_title":
                    match.course_title,
                "course_date":
                    match.course_date.isoformat(),
            }
            if match is not None
            else None
        ),
    }


def _intermediate_service_training_results(
    pathways,
    service_years,
    training_hours,
):
    results = []

    for pathway in pathways:
        required_service = pathway[
            "service_years"
        ]
        required_hours = pathway[
            "training_hours"
        ]

        service_short = (
            None
            if service_years is None
            else max(
                required_service - service_years,
                0,
            )
        )

        hours_short = max(
            float(required_hours) - training_hours,
            0.0,
        )

        satisfied = (
            service_years is not None
            and service_years >= required_service
            and training_hours >= required_hours
        )

        results.append(
            {
                "type": "SERVICE_TRAINING",
                "service_years":
                    required_service,
                "training_hours":
                    required_hours,
                "actual_service_years":
                    service_years,
                "actual_training_hours":
                    training_hours,
                "service_years_short":
                    service_short,
                "training_hours_short":
                    hours_short,
                "satisfied": satisfied,
            }
        )

    return results


def _intermediate_education_results(
    pathways,
    service_years,
    education_level,
):
    results = []

    actual_rank = (
        JAILER_EDUCATION_RANK.get(
            education_level
        )
    )

    for pathway in pathways:
        required_service = pathway[
            "service_years"
        ]
        required_level = pathway[
            "education_level"
        ]
        required_rank = JAILER_EDUCATION_RANK[
            required_level
        ]

        service_short = (
            None
            if service_years is None
            else max(
                required_service - service_years,
                0,
            )
        )

        education_met = (
            actual_rank is not None
            and actual_rank >= required_rank
        )

        satisfied = (
            service_years is not None
            and service_years >= required_service
            and education_met
        )

        results.append(
            {
                "type": "EDUCATION",
                "service_years":
                    required_service,
                "education_level":
                    required_level,
                "actual_service_years":
                    service_years,
                "actual_education_level":
                    education_level,
                "service_years_short":
                    service_short,
                "education_met":
                    education_met,
                "satisfied": satisfied,
            }
        )

    return results


def _best_intermediate_pathway(
    service_training_results,
    education_results,
):
    all_results = (
        service_training_results
        + education_results
    )

    satisfied = [
        result
        for result in all_results
        if result["satisfied"]
    ]

    if satisfied:
        return satisfied[0]

    # First prefer an education pathway only when the
    # employee already possesses the required education.
    #
    # An unearned degree must not numerically outrank a
    # service/training pathway merely because an arbitrary
    # education penalty of 1 is smaller than a number of
    # training hours remaining.
    education_with_degree = [
        result
        for result in education_results
        if result["education_met"]
    ]

    if education_with_degree:
        return min(
            education_with_degree,
            key=lambda result: (
                (
                    result["service_years_short"]
                    if result["service_years_short"]
                    is not None
                    else 999
                ),
                -result["service_years"],
            ),
        )

    # If the employee does not currently satisfy an
    # education pathway, identify the closest published
    # service/training combination.
    service_feasible = [
        result
        for result in service_training_results
        if result["service_years_short"] == 0
    ]

    if service_feasible:
        return min(
            service_feasible,
            key=lambda result: (
                result["training_hours_short"],
                result["training_hours"],
                -result["service_years"],
            ),
        )

    # No pathway is presently service-feasible. Select the
    # service/training combination requiring the least
    # additional service, then the least additional
    # training.
    if service_training_results:
        return min(
            service_training_results,
            key=lambda result: (
                (
                    result["service_years_short"]
                    if result["service_years_short"]
                    is not None
                    else 999
                ),
                result["training_hours_short"],
                result["training_hours"],
            ),
        )

    # This should be unusual because Intermediate Jailer
    # currently publishes service/training pathways, but
    # retain a safe fallback for future rule changes.
    if education_results:
        return min(
            education_results,
            key=lambda result: (
                (
                    result["service_years_short"]
                    if result["service_years_short"]
                    is not None
                    else 999
                ),
                0 if result["education_met"] else 1,
            ),
        )

    return None

def evaluate_intermediate_jailer_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_intermediate_jailer_rule()

    credential = get_highest_jailer_certificate(
        officer
    )

    certificate_dates = (
        _jailer_certificate_dates(officer)
    )

    has_license = has_jailer_license(officer)

    service_years = _service_years(
        officer,
        evaluation_date,
    )

    training_hours = _jailer_training_hours(
        officer
    )

    education_level = _jailer_education_level(
        officer
    )

    basic_certificate_date = (
        certificate_dates.get("Basic Jailer")
    )

    current_level = credential[
        "certificate_level"
    ]

    basic_prerequisite_met = (
        current_level in {
            "BASIC",
            "INTERMEDIATE",
            "ADVANCED",
            "MASTER",
        }
    )

    service_training_results = (
        _intermediate_service_training_results(
            rule["pathways"]["service_training"],
            service_years,
            training_hours,
        )
    )

    education_results = (
        _intermediate_education_results(
            rule["pathways"]["education"],
            service_years,
            education_level,
        )
    )

    all_pathway_results = (
        service_training_results
        + education_results
    )

    qualifying_pathway = next(
        (
            result
            for result in all_pathway_results
            if result["satisfied"]
        ),
        None,
    )

    best_available_pathway = (
        _best_intermediate_pathway(
            service_training_results,
            education_results,
        )
    )

    course_requirements = [
        _intermediate_course_requirement_result(
            officer,
            requirement,
            basic_certificate_date,
        )
        for requirement in rule[
            "required_courses"
        ]
    ]

    missing_courses = [
        item
        for item in course_requirements
        if item["status"] == "MISSING"
    ]

    insufficient_courses = [
        item
        for item in course_requirements
        if item["status"] == "INSUFFICIENT_DATA"
    ]

    if current_level in {
        "INTERMEDIATE",
        "ADVANCED",
        "MASTER",
    }:
        status = "AWARDED"

    elif not has_license:
        status = "NOT_APPLICABLE"

    elif service_years is None:
        status = "INSUFFICIENT_DATA"

    elif not basic_prerequisite_met:
        status = "NOT_ELIGIBLE"

    elif insufficient_courses:
        status = "INSUFFICIENT_DATA"

    elif qualifying_pathway is None:
        status = "NOT_ELIGIBLE"

    elif missing_courses:
        status = "NOT_ELIGIBLE"

    else:
        status = "ELIGIBLE"

    missing_requirements = []

    if (
        has_license
        and not basic_prerequisite_met
    ):
        missing_requirements.append(
            "Basic Jailer certificate"
        )

    if (
        has_license
        and service_years is not None
        and qualifying_pathway is None
        and best_available_pathway is not None
    ):
        if (
            best_available_pathway["type"]
            == "SERVICE_TRAINING"
        ):
            years_short = best_available_pathway[
                "service_years_short"
            ]
            hours_short = best_available_pathway[
                "training_hours_short"
            ]

            if years_short:
                missing_requirements.append(
                    (
                        f"{years_short} additional year"
                        f"{'s' if years_short != 1 else ''} "
                        "of qualifying County Jailer service"
                    )
                )

            if hours_short:
                missing_requirements.append(
                    (
                        f"{hours_short:g} additional "
                        "training hours"
                    )
                )

        elif (
            best_available_pathway["type"]
            == "EDUCATION"
        ):
            years_short = best_available_pathway[
                "service_years_short"
            ]

            if years_short:
                missing_requirements.append(
                    (
                        f"{years_short} additional year"
                        f"{'s' if years_short != 1 else ''} "
                        "of qualifying County Jailer service"
                    )
                )

            if not best_available_pathway[
                "education_met"
            ]:
                required_level = (
                    best_available_pathway[
                        "education_level"
                    ]
                    .replace("_", " ")
                    .title()
                )

                missing_requirements.append(
                    (
                        f"{required_level} degree "
                        "education pathway requirement"
                    )
                )

    missing_requirements.extend(
        item["name"]
        for item in missing_courses
    )

    insufficient_data_requirements = []

    if has_license and service_years is None:
        insufficient_data_requirements.append(
            "County Jailer license/service start date"
        )

    if (
        has_license
        and basic_prerequisite_met
        and basic_certificate_date is None
        and current_level == "BASIC"
    ):
        insufficient_data_requirements.append(
            "Basic Jailer certificate award date"
        )

    insufficient_data_requirements.extend(
        item["name"]
        for item in insufficient_courses
    )

    return {
        "certificate": "Intermediate Jailer",
        "status": status,
        "current_certificate":
            credential["highest_certificate"],
        "current_certificate_date":
            credential["highest_certificate_date"],
        "certificate_level":
            credential["certificate_level"],
        "has_jailer_license": has_license,
        "basic_prerequisite_met":
            basic_prerequisite_met,
        "basic_certificate_date": (
            basic_certificate_date.isoformat()
            if basic_certificate_date
            else None
        ),
        "service_years": service_years,
        "training_hours": training_hours,
        "education_level": education_level,
        "qualifying_pathway":
            qualifying_pathway,
        "best_available_pathway":
            best_available_pathway,
        "pathway_results": {
            "service_training":
                service_training_results,
            "education":
                education_results,
        },
        "course_requirements":
            course_requirements,
        "missing_requirements":
            missing_requirements,
        "insufficient_data_requirements":
            insufficient_data_requirements,
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["rule_version"],
    }


ADVANCED_RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "jailer_proficiency_advanced.json"
)


def load_advanced_jailer_rule():
    with ADVANCED_RULE_PATH.open() as file:
        return json.load(file)


def _jailer_military_months(officer):
    months = officer.verified_military_months

    if months is None:
        return None

    if months < 0:
        return None

    return months


def _advanced_military_results(
    pathways,
    service_years,
    military_months,
):
    results = []

    for pathway in pathways:
        required_service = pathway[
            "service_years"
        ]
        required_military_years = pathway[
            "military_years"
        ]
        required_months = (
            required_military_years * 12
        )

        service_short = (
            None
            if service_years is None
            else max(
                required_service - service_years,
                0,
            )
        )

        military_months_short = (
            None
            if military_months is None
            else max(
                required_months - military_months,
                0,
            )
        )

        military_met = (
            military_months is not None
            and military_months
            >= required_months
        )

        satisfied = (
            service_years is not None
            and service_years >= required_service
            and military_met
        )

        results.append(
            {
                "type": "MILITARY",
                "service_years":
                    required_service,
                "military_years":
                    required_military_years,
                "required_military_months":
                    required_months,
                "actual_service_years":
                    service_years,
                "actual_military_months":
                    military_months,
                "service_years_short":
                    service_short,
                "military_months_short":
                    military_months_short,
                "military_met":
                    military_met,
                "satisfied":
                    satisfied,
            }
        )

    return results


def _best_advanced_pathway(
    service_training_results,
    education_results,
    military_results,
):
    all_results = (
        service_training_results
        + education_results
        + military_results
    )

    satisfied = [
        result
        for result in all_results
        if result["satisfied"]
    ]

    if satisfied:
        return satisfied[0]

    # Education competes as a realistic pathway only
    # when the employee already possesses the required
    # degree.
    education_with_degree = [
        result
        for result in education_results
        if result["education_met"]
    ]

    if education_with_degree:
        return min(
            education_with_degree,
            key=lambda result: (
                (
                    result["service_years_short"]
                    if result["service_years_short"]
                    is not None
                    else 999
                ),
                -result["service_years"],
            ),
        )

    # Military competes as a realistic pathway when
    # military history is known. Prefer the published
    # combination requiring the least remaining service
    # and military credit.
    military_known = [
        result
        for result in military_results
        if result["actual_military_months"]
        is not None
    ]

    military_feasible = [
        result
        for result in military_known
        if result["service_years_short"] == 0
    ]

    service_feasible = [
        result
        for result in service_training_results
        if result["service_years_short"] == 0
    ]

    candidates = []

    for result in service_feasible:
        candidates.append(
            (
                result["training_hours_short"],
                0,
                result,
            )
        )

    for result in military_feasible:
        candidates.append(
            (
                result["military_months_short"],
                1,
                result,
            )
        )

    if candidates:
        # These units are intentionally not treated as
        # interchangeable measures of effort. Prefer the
        # service/training path in a tie and otherwise use
        # only this ranking as presentation guidance.
        #
        # The actual eligibility calculation remains
        # independent for every published pathway.
        service_candidates = [
            result
            for result in service_feasible
        ]

        if service_candidates:
            return min(
                service_candidates,
                key=lambda result: (
                    result[
                        "training_hours_short"
                    ],
                    result["training_hours"],
                    -result["service_years"],
                ),
            )

        return min(
            military_feasible,
            key=lambda result: (
                (
                    result[
                        "military_months_short"
                    ]
                    if result[
                        "military_months_short"
                    ] is not None
                    else 9999
                ),
                -result["service_years"],
            ),
        )

    if service_training_results:
        return min(
            service_training_results,
            key=lambda result: (
                (
                    result["service_years_short"]
                    if result["service_years_short"]
                    is not None
                    else 999
                ),
                result["training_hours_short"],
                result["training_hours"],
            ),
        )

    if military_known:
        return min(
            military_known,
            key=lambda result: (
                (
                    result["service_years_short"]
                    if result["service_years_short"]
                    is not None
                    else 999
                ),
                (
                    result["military_months_short"]
                    if result[
                        "military_months_short"
                    ] is not None
                    else 9999
                ),
            ),
        )

    if education_results:
        return min(
            education_results,
            key=lambda result: (
                (
                    result["service_years_short"]
                    if result["service_years_short"]
                    is not None
                    else 999
                ),
                0 if result["education_met"] else 1,
            ),
        )

    return None


def evaluate_advanced_jailer_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_advanced_jailer_rule()

    credential = get_highest_jailer_certificate(
        officer
    )

    has_license = has_jailer_license(officer)

    service_years = _service_years(
        officer,
        evaluation_date,
    )

    training_hours = _jailer_training_hours(
        officer
    )

    education_level = _jailer_education_level(
        officer
    )

    military_months = _jailer_military_months(
        officer
    )

    current_level = credential[
        "certificate_level"
    ]

    basic_prerequisite_met = (
        current_level in {
            "BASIC",
            "INTERMEDIATE",
            "ADVANCED",
            "MASTER",
        }
    )

    intermediate_prerequisite_met = (
        current_level in {
            "INTERMEDIATE",
            "ADVANCED",
            "MASTER",
        }
    )

    service_training_results = (
        _intermediate_service_training_results(
            rule["pathways"]["service_training"],
            service_years,
            training_hours,
        )
    )

    education_results = (
        _intermediate_education_results(
            rule["pathways"]["education"],
            service_years,
            education_level,
        )
    )

    military_results = (
        _advanced_military_results(
            rule["pathways"]["military"],
            service_years,
            military_months,
        )
    )

    all_pathway_results = (
        service_training_results
        + education_results
        + military_results
    )

    qualifying_pathway = next(
        (
            result
            for result in all_pathway_results
            if result["satisfied"]
        ),
        None,
    )

    best_available_pathway = (
        _best_advanced_pathway(
            service_training_results,
            education_results,
            military_results,
        )
    )

    if current_level in {
        "ADVANCED",
        "MASTER",
    }:
        status = "AWARDED"

    elif not has_license:
        status = "NOT_APPLICABLE"

    elif service_years is None:
        status = "INSUFFICIENT_DATA"

    elif not intermediate_prerequisite_met:
        status = "NOT_ELIGIBLE"

    elif qualifying_pathway is None:
        status = "NOT_ELIGIBLE"

    else:
        status = "ELIGIBLE"

    missing_requirements = []

    if has_license and not basic_prerequisite_met:
        missing_requirements.append(
            "Basic Jailer certificate"
        )

    if (
        has_license
        and not intermediate_prerequisite_met
    ):
        missing_requirements.append(
            "Intermediate Jailer certificate"
        )

    if (
        has_license
        and service_years is not None
        and qualifying_pathway is None
        and best_available_pathway is not None
    ):
        pathway_type = best_available_pathway[
            "type"
        ]

        years_short = best_available_pathway[
            "service_years_short"
        ]

        if years_short:
            missing_requirements.append(
                (
                    f"{years_short} additional year"
                    f"{'s' if years_short != 1 else ''} "
                    "of qualifying County Jailer service"
                )
            )

        if pathway_type == "SERVICE_TRAINING":
            hours_short = best_available_pathway[
                "training_hours_short"
            ]

            if hours_short:
                missing_requirements.append(
                    (
                        f"{hours_short:g} additional "
                        "training hours"
                    )
                )

        elif pathway_type == "EDUCATION":
            if not best_available_pathway[
                "education_met"
            ]:
                level = (
                    best_available_pathway[
                        "education_level"
                    ]
                    .replace("_", " ")
                    .title()
                )

                missing_requirements.append(
                    (
                        f"{level} degree education "
                        "pathway requirement"
                    )
                )

        elif pathway_type == "MILITARY":
            military_short = (
                best_available_pathway[
                    "military_months_short"
                ]
            )

            if military_short:
                missing_requirements.append(
                    (
                        f"{military_short} additional "
                        "months of qualifying military "
                        "service/training credit"
                    )
                )

    insufficient_data_requirements = []

    if has_license and service_years is None:
        insufficient_data_requirements.append(
            "County Jailer license/service start date"
        )

    return {
        "certificate": "Advanced Jailer",
        "status": status,
        "current_certificate":
            credential["highest_certificate"],
        "current_certificate_date":
            credential["highest_certificate_date"],
        "certificate_level":
            credential["certificate_level"],
        "has_jailer_license": has_license,
        "basic_prerequisite_met":
            basic_prerequisite_met,
        "intermediate_prerequisite_met":
            intermediate_prerequisite_met,
        "service_years": service_years,
        "training_hours": training_hours,
        "education_level": education_level,
        "verified_military_months":
            military_months,
        "qualifying_pathway":
            qualifying_pathway,
        "best_available_pathway":
            best_available_pathway,
        "pathway_results": {
            "service_training":
                service_training_results,
            "education":
                education_results,
            "military":
                military_results,
        },
        "course_requirements": [],
        "missing_requirements":
            missing_requirements,
        "insufficient_data_requirements":
            insufficient_data_requirements,
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["rule_version"],
    }


MASTER_JAILER_RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "jailer_proficiency_master.json"
)


def load_master_jailer_rule():
    with MASTER_JAILER_RULE_PATH.open() as file:
        return json.load(file)


def evaluate_master_jailer_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_master_jailer_rule()

    credential = get_highest_jailer_certificate(
        officer
    )

    has_license = has_jailer_license(officer)

    service_years = _service_years(
        officer,
        evaluation_date,
    )

    training_hours = _jailer_training_hours(
        officer
    )

    education_level = _jailer_education_level(
        officer
    )

    military_months = _jailer_military_months(
        officer
    )

    current_level = credential[
        "certificate_level"
    ]

    basic_prerequisite_met = (
        current_level in {
            "BASIC",
            "INTERMEDIATE",
            "ADVANCED",
            "MASTER",
        }
    )

    intermediate_prerequisite_met = (
        current_level in {
            "INTERMEDIATE",
            "ADVANCED",
            "MASTER",
        }
    )

    advanced_prerequisite_met = (
        current_level in {
            "ADVANCED",
            "MASTER",
        }
    )

    service_training_results = (
        _intermediate_service_training_results(
            rule["pathways"]["service_training"],
            service_years,
            training_hours,
        )
    )

    education_results = (
        _intermediate_education_results(
            rule["pathways"]["education"],
            service_years,
            education_level,
        )
    )

    military_results = (
        _advanced_military_results(
            rule["pathways"]["military"],
            service_years,
            military_months,
        )
    )

    all_pathway_results = (
        service_training_results
        + education_results
        + military_results
    )

    qualifying_pathway = next(
        (
            result
            for result in all_pathway_results
            if result["satisfied"]
        ),
        None,
    )

    best_available_pathway = (
        _best_advanced_pathway(
            service_training_results,
            education_results,
            military_results,
        )
    )

    if current_level == "MASTER":
        status = "AWARDED"

    elif not has_license:
        status = "NOT_APPLICABLE"

    elif service_years is None:
        status = "INSUFFICIENT_DATA"

    elif not advanced_prerequisite_met:
        status = "NOT_ELIGIBLE"

    elif qualifying_pathway is None:
        status = "NOT_ELIGIBLE"

    else:
        status = "ELIGIBLE"

    missing_requirements = []

    if has_license and not basic_prerequisite_met:
        missing_requirements.append(
            "Basic Jailer certificate"
        )

    if (
        has_license
        and not intermediate_prerequisite_met
    ):
        missing_requirements.append(
            "Intermediate Jailer certificate"
        )

    if (
        has_license
        and not advanced_prerequisite_met
    ):
        missing_requirements.append(
            "Advanced Jailer certificate"
        )

    if (
        has_license
        and service_years is not None
        and qualifying_pathway is None
        and best_available_pathway is not None
    ):
        pathway_type = best_available_pathway[
            "type"
        ]

        years_short = best_available_pathway[
            "service_years_short"
        ]

        if years_short:
            missing_requirements.append(
                (
                    f"{years_short} additional year"
                    f"{'s' if years_short != 1 else ''} "
                    "of qualifying County Jailer service"
                )
            )

        if pathway_type == "SERVICE_TRAINING":
            hours_short = best_available_pathway[
                "training_hours_short"
            ]

            if hours_short:
                missing_requirements.append(
                    (
                        f"{hours_short:g} additional "
                        "training hours"
                    )
                )

        elif pathway_type == "EDUCATION":
            if not best_available_pathway[
                "education_met"
            ]:
                level = (
                    best_available_pathway[
                        "education_level"
                    ]
                    .replace("_", " ")
                    .title()
                )

                missing_requirements.append(
                    (
                        f"{level} degree education "
                        "pathway requirement"
                    )
                )

        elif pathway_type == "MILITARY":
            military_short = (
                best_available_pathway[
                    "military_months_short"
                ]
            )

            if military_short:
                missing_requirements.append(
                    (
                        f"{military_short} additional "
                        "months of qualifying military "
                        "service/training credit"
                    )
                )

    insufficient_data_requirements = []

    if has_license and service_years is None:
        insufficient_data_requirements.append(
            "County Jailer license/service start date"
        )

    return {
        "certificate": "Master Jailer",
        "status": status,
        "current_certificate":
            credential["highest_certificate"],
        "current_certificate_date":
            credential["highest_certificate_date"],
        "certificate_level":
            credential["certificate_level"],
        "has_jailer_license": has_license,
        "basic_prerequisite_met":
            basic_prerequisite_met,
        "intermediate_prerequisite_met":
            intermediate_prerequisite_met,
        "advanced_prerequisite_met":
            advanced_prerequisite_met,
        "service_years": service_years,
        "training_hours": training_hours,
        "education_level": education_level,
        "verified_military_months":
            military_months,
        "qualifying_pathway":
            qualifying_pathway,
        "best_available_pathway":
            best_available_pathway,
        "pathway_results": {
            "service_training":
                service_training_results,
            "education":
                education_results,
            "military":
                military_results,
        },
        "course_requirements": [],
        "missing_requirements":
            missing_requirements,
        "insufficient_data_requirements":
            insufficient_data_requirements,
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["rule_version"],
    }


def evaluate_jailer_proficiency(
    officer,
    evaluation_date=None,
):
    """
    Evaluate the employee's next applicable County Jailer
    proficiency certificate.

    This is the public progression evaluator used by PTM.
    Individual certificate evaluators remain available for
    rule-level testing and auditability.
    """

    if evaluation_date is None:
        evaluation_date = date.today()

    credential = get_highest_jailer_certificate(
        officer
    )

    current_certificate = credential[
        "highest_certificate"
    ]

    if not has_jailer_license(officer):
        return {
            "status": "NOT_APPLICABLE",
            "current_certificate": None,
            "current_certificate_date": None,
            "certificate_level": None,
            "next_certificate": None,
            "service_years": None,
            "training_hours": 0.0,
            "education_level": None,
            "verified_military_months": None,
            "qualifying_pathway": None,
            "best_available_pathway": None,
            "pathway_results": {},
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_set_id": None,
            "rule_version": None,
        }

    if current_certificate is None:
        result = evaluate_basic_jailer_proficiency(
            officer,
            evaluation_date=evaluation_date,
        )
        next_certificate = "Basic Jailer"

    elif current_certificate == "Basic Jailer":
        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=evaluation_date,
        )
        next_certificate = "Intermediate Jailer"

    elif current_certificate == "Intermediate Jailer":
        result = evaluate_advanced_jailer_proficiency(
            officer,
            evaluation_date=evaluation_date,
        )
        next_certificate = "Advanced Jailer"

    elif current_certificate == "Advanced Jailer":
        result = evaluate_master_jailer_proficiency(
            officer,
            evaluation_date=evaluation_date,
        )
        next_certificate = "Master Jailer"

    elif current_certificate == "Master Jailer":
        return {
            "status": "HIGHEST_CERTIFICATE",
            "current_certificate": "Master Jailer",
            "current_certificate_date":
                credential["highest_certificate_date"],
            "certificate_level": "MASTER",
            "next_certificate": None,
            "service_years": _service_years(
                officer,
                evaluation_date,
            ),
            "training_hours":
                _jailer_training_hours(officer),
            "education_level":
                _jailer_education_level(officer),
            "verified_military_months":
                _jailer_military_months(officer),
            "qualifying_pathway": None,
            "best_available_pathway": None,
            "pathway_results": {},
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_set_id": None,
            "rule_version": None,
        }

    else:
        raise ValueError(
            "Unsupported County Jailer certificate: "
            f"{current_certificate}"
        )

    advancement = dict(result)

    advancement["next_certificate"] = (
        next_certificate
    )

    return advancement
