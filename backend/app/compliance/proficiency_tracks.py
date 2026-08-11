from datetime import date

from app.compliance.jailer_proficiency import (
    evaluate_jailer_proficiency,
    has_jailer_license,
)
from app.compliance.peace_officer_proficiency import (
    evaluate_peace_officer_proficiency,
)
from app.compliance.peace_officer_unit import (
    has_peace_officer_license,
)
from app.compliance.telecommunicator_proficiency import (
    evaluate_telecommunicator_proficiency,
)


def build_proficiency_advancement(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    peace_officer = (
        evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=evaluation_date,
        )
        if has_peace_officer_license(officer)
        else None
    )

    jailer = (
        evaluate_jailer_proficiency(
            officer,
            evaluation_date=evaluation_date,
        )
        if has_jailer_license(officer)
        else None
    )

    telecommunicator = (
        evaluate_telecommunicator_proficiency(
            officer,
            evaluation_date=evaluation_date,
        )
    )

    if (
        telecommunicator.get("status")
        == "NOT_APPLICABLE"
    ):
        telecommunicator = None

    return {
        "peace_officer": peace_officer,
        "jailer": jailer,
        "telecommunicator": telecommunicator,
    }
