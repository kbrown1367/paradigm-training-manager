from datetime import date

from app.compliance.credentials import (
    get_highest_peace_officer_certificate,
)
from app.compliance.county_jailer import (
    evaluate_county_jailer,
    has_county_jailer_license,
)
from app.compliance.peace_officer_unit import (
    evaluate_peace_officer_unit,
    has_peace_officer_license,
)
from app.compliance.police_chief import (
    evaluate_police_chief,
)
from app.compliance.public_information_officer import (
    evaluate_public_information_officer,
)
from app.compliance.supervisor import (
    evaluate_supervisor,
)


def _raw_component_status(component_name, result):
    status_fields = {
        "PEACE_OFFICER": "unit_status",
        "COUNTY_JAILER": "status",
        "POLICE_CHIEF": "chief_status",
        "SUPERVISOR": "status",
        "PUBLIC_INFORMATION_OFFICER": "status",
    }

    field = status_fields.get(component_name)

    if field is None:
        return None

    return result.get(field)


def _component_status(component_name, result):
    if result.get("applicable") is False:
        return "NOT_APPLICABLE"

    raw_status = _raw_component_status(
        component_name,
        result,
    )

    if raw_status in {
        "OVERDUE",
        "FAILED",
        "NONCOMPLIANT",
    }:
        return "NONCOMPLIANT"

    if raw_status in {
        "UNVERIFIED",
        "PENDING_REVIEW",
    }:
        return "PENDING_REVIEW"

    if raw_status in {
        "OUTSTANDING",
        "DUE",
        "FUTURE_REQUIREMENT",
    }:
        return "DUE"

    if raw_status in {
        "COMPLETE",
        "COMPLIANT",
    }:
        return "COMPLIANT"

    if raw_status == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"

    return "PENDING_REVIEW"


def _requirements_for(component_name, result):
    if component_name == "PUBLIC_INFORMATION_OFFICER":
        return result.get("deficiencies", [])

    return result.get(
        "requirements",
        result.get("deficiencies", []),
    )


def _requirement_status(item):
    raw_status = item.get("status")

    if raw_status in {
        "OVERDUE",
        "FAILED",
        "NONCOMPLIANT",
    }:
        return "OVERDUE"

    if raw_status in {
        "UNVERIFIED",
        "PENDING_REVIEW",
    }:
        return "PENDING_REVIEW"

    if raw_status in {
        "OUTSTANDING",
        "DUE",
    }:
        return "OUTSTANDING"

    return raw_status


def _normalize_component(
    component_name,
    result,
):
    applicable = result.get("applicable", True)
    requirements = []

    for item in _requirements_for(
        component_name,
        result,
    ):
        normalized = dict(item)
        normalized["source_component"] = component_name
        normalized["normalized_status"] = (
            _requirement_status(item)
        )
        requirements.append(normalized)

    return {
        "component": component_name,
        "applicable": applicable,
        "status": _component_status(
            component_name,
            result,
        ),
        "raw_status": _raw_component_status(
            component_name,
            result,
        ),
        "requirements": requirements,
        "result": result,
    }


def _parse_due_date(value):
    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def evaluate_officer_compliance_profile(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    if has_peace_officer_license(officer):
        peace_officer = evaluate_peace_officer_unit(
            officer,
            evaluation_date=evaluation_date,
        )
    else:
        peace_officer = {
            "applicable": False,
            "unit_status": "NOT_APPLICABLE",
            "requirements": [],
            "deficiencies": [],
        }

    if has_county_jailer_license(officer):
        county_jailer = evaluate_county_jailer(
            officer,
            evaluation_date=evaluation_date,
        )
    else:
        county_jailer = {
            "applicable": False,
            "status": "NOT_APPLICABLE",
            "requirements": [],
            "deficiencies": [],
        }

    police_chief = evaluate_police_chief(
        officer,
        evaluation_date=evaluation_date,
    )

    supervisor = evaluate_supervisor(
        officer,
        evaluation_date=evaluation_date,
    )

    pio = evaluate_public_information_officer(
        officer,
        evaluation_date=evaluation_date,
    )

    components = [
        _normalize_component(
            "PEACE_OFFICER",
            peace_officer,
        ),
        _normalize_component(
            "COUNTY_JAILER",
            county_jailer,
        ),
        _normalize_component(
            "POLICE_CHIEF",
            police_chief,
        ),
        _normalize_component(
            "SUPERVISOR",
            supervisor,
        ),
        _normalize_component(
            "PUBLIC_INFORMATION_OFFICER",
            pio,
        ),
    ]

    applicable_components = [
        component
        for component in components
        if component["applicable"]
    ]

    all_requirements = [
        requirement
        for component in applicable_components
        for requirement in component["requirements"]
    ]

    overdue = [
        item
        for item in all_requirements
        if item["normalized_status"] == "OVERDUE"
    ]

    outstanding = [
        item
        for item in all_requirements
        if item["normalized_status"] == "OUTSTANDING"
    ]

    pending_review = [
        item
        for item in all_requirements
        if (
            item["normalized_status"]
            == "PENDING_REVIEW"
        )
    ]

    agency_review = [
        item
        for item in all_requirements
        if item.get(
            "agency_review_recommended",
            False,
        )
    ]

    component_statuses = {
        component["status"]
        for component in applicable_components
    }

    evaluated_component_count = len(
        applicable_components
    )

    applicable_component_names = [
        component["component"]
        for component in applicable_components
    ]

    coverage_status = (
        "EVALUATED"
        if evaluated_component_count > 0
        else "NOT_EVALUATED"
    )

    if evaluated_component_count == 0:
        overall_status = "NOT_EVALUATED"
    elif "NONCOMPLIANT" in component_statuses:
        overall_status = "NONCOMPLIANT"
    elif "PENDING_REVIEW" in component_statuses:
        overall_status = "PENDING_REVIEW"
    elif "DUE" in component_statuses:
        overall_status = "DUE"
    else:
        overall_status = "COMPLIANT"

    due_dates = []

    for requirement in all_requirements:
        due_date = _parse_due_date(
            requirement.get("due_date")
        )

        if (
            due_date is not None
            and due_date >= evaluation_date
        ):
            due_dates.append(due_date)

    next_due_date = (
        min(due_dates).isoformat()
        if due_dates
        else None
    )

    credential = (
        get_highest_peace_officer_certificate(
            officer
        )
    )

    return {
        "officer": {
            "id": str(officer.id),
            "agency_id": str(officer.agency_id),
            "tcole_pid": officer.tcole_pid,
            "first_name": officer.first_name,
            "middle_name": officer.middle_name,
            "last_name": officer.last_name,
            "highest_certificate":
                credential["highest_certificate"],
            "certificate_level":
                credential["certificate_level"],
            "highest_certificate_date":
                credential[
                    "highest_certificate_date"
                ],
        },
        "evaluation_date":
            evaluation_date.isoformat(),
        "overall_status": overall_status,
        "evaluation_coverage": {
            "coverage_status": coverage_status,
            "evaluated_component_count":
                evaluated_component_count,
            "applicable_components":
                applicable_component_names,
        },
        "review_required": bool(agency_review),
        "overdue_count": len(overdue),
        "outstanding_count": len(outstanding),
        "pending_review_count":
            len(pending_review),
        "agency_review_count":
            len(agency_review),
        "next_due_date": next_due_date,
        "requirements": all_requirements,
        "overdue_requirements": overdue,
        "outstanding_requirements": outstanding,
        "pending_review_requirements":
            pending_review,
        "agency_review_requirements":
            agency_review,
        "components": {
            component["component"]: component
            for component in components
        },
    }
