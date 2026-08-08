from datetime import date

from app.compliance.officer_profile import (
    evaluate_officer_compliance_profile,
)
from app.compliance.training_calendar import (
    get_cycle,
    get_unit,
)
from app.models import Agency, Officer


STATUS_PRIORITY = {
    "NONCOMPLIANT": 0,
    "PENDING_REVIEW": 1,
    "DUE": 2,
    "COMPLIANT": 3,
    "NOT_EVALUATED": 4,
}


def _active_assignments(
    officer,
    evaluation_date,
):
    return sorted(
        [
            assignment.assignment_type
            for assignment in officer.assignments
            if (
                assignment.effective_date
                <= evaluation_date
                and (
                    assignment.end_date is None
                    or assignment.end_date
                    >= evaluation_date
                )
            )
        ]
    )


def _requirement_due_date(requirement):
    value = requirement.get("due_date")

    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _priority_findings(profile, limit=3):
    findings = []

    for requirement in profile["requirements"]:
        normalized = requirement.get(
            "normalized_status"
        )

        if normalized not in {
            "OVERDUE",
            "PENDING_REVIEW",
            "OUTSTANDING",
        }:
            continue

        due_date = _requirement_due_date(
            requirement
        )

        status_priority = {
            "OVERDUE": 0,
            "PENDING_REVIEW": 1,
            "OUTSTANDING": 2,
        }.get(normalized, 9)

        findings.append(
            (
                status_priority,
                due_date or date.max,
                requirement,
            )
        )

    findings.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2].get(
                "source_component",
                "",
            ),
            item[2].get("type", ""),
        )
    )

    return [
        item[2]
        for item in findings[:limit]
    ]


def _employee_sort_key(employee):
    status = employee["overall_status"]

    if status == "NONCOMPLIANT":
        dates = [
            _requirement_due_date(item)
            for item in employee[
                "overdue_requirements"
            ]
        ]
    elif status == "PENDING_REVIEW":
        dates = [
            _requirement_due_date(item)
            for item in employee[
                "pending_review_requirements"
            ]
        ]
    else:
        dates = [
            date.fromisoformat(
                employee["next_due_date"]
            )
        ] if employee["next_due_date"] else []

    dates = [
        value
        for value in dates
        if value is not None
    ]

    priority_date = (
        min(dates)
        if dates
        else date.max
    )

    return (
        STATUS_PRIORITY.get(status, 99),
        priority_date,
        employee["last_name"].lower(),
        employee["first_name"].lower(),
    )


def evaluate_agency_compliance_dashboard(
    agency_id,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    agency = Agency.query.filter_by(
        id=agency_id
    ).one_or_none()

    if agency is None:
        return None

    officers = (
        Officer.query
        .filter_by(
            agency_id=agency_id,
            employment_status="active",
        )
        .order_by(
            Officer.last_name,
            Officer.first_name,
        )
        .all()
    )

    employees = []

    for officer in officers:
        profile = (
            evaluate_officer_compliance_profile(
                officer,
                evaluation_date=evaluation_date,
            )
        )

        employee = {
            **profile["officer"],
            "assignments": _active_assignments(
                officer,
                evaluation_date,
            ),
            "overall_status":
                profile["overall_status"],
            "evaluation_coverage":
                profile["evaluation_coverage"],
            "review_required":
                profile["review_required"],
            "overdue_count":
                profile["overdue_count"],
            "outstanding_count":
                profile["outstanding_count"],
            "pending_review_count":
                profile[
                    "pending_review_count"
                ],
            "agency_review_count":
                profile[
                    "agency_review_count"
                ],
            "next_due_date":
                profile["next_due_date"],
            "priority_findings":
                _priority_findings(profile),
            "overdue_requirements":
                profile[
                    "overdue_requirements"
                ],
            "pending_review_requirements":
                profile[
                    "pending_review_requirements"
                ],
        }

        employees.append(employee)

    employees.sort(key=_employee_sort_key)

    cycle = get_cycle(evaluation_date)
    unit = get_unit(evaluation_date)

    summary = {
        "active_employee_count":
            len(employees),
        "compliant_count": sum(
            employee["overall_status"]
            == "COMPLIANT"
            for employee in employees
        ),
        "due_count": sum(
            employee["overall_status"]
            == "DUE"
            for employee in employees
        ),
        "noncompliant_count": sum(
            employee["overall_status"]
            == "NONCOMPLIANT"
            for employee in employees
        ),
        "pending_review_count": sum(
            employee["overall_status"]
            == "PENDING_REVIEW"
            for employee in employees
        ),
        "not_evaluated_count": sum(
            employee["overall_status"]
            == "NOT_EVALUATED"
            for employee in employees
        ),
        "agency_review_required_count":
            sum(
                employee[
                    "review_required"
                ]
                for employee in employees
            ),
    }

    return {
        "agency": {
            "id": str(agency.id),
            "name": agency.name,
        },
        "evaluation_date":
            evaluation_date.isoformat(),
        "training_cycle": {
            "start":
                cycle["start"].isoformat(),
            "end":
                cycle["end"].isoformat(),
        },
        "training_unit": {
            "number":
                unit["unit_number"],
            "start":
                unit["start"].isoformat(),
            "end":
                unit["end"].isoformat(),
        },
        "summary": summary,
        "employees": employees,
    }
