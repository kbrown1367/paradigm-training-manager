from app.extensions import db
from app.models import Officer


EDUCATION_LEVELS = {
    "ASSOCIATE",
    "BACHELOR",
    "MASTER",
    "DOCTORATE",
}


class QualificationFactsError(ValueError):
    pass


def _serialize(officer):
    return {
        "officer_id": str(officer.id),
        "verified_education_level":
            officer.verified_education_level,
        "verified_military_months":
            officer.verified_military_months,
    }


def get_qualification_facts(
    agency_id,
    officer_id,
):
    officer = Officer.query.filter_by(
        id=officer_id,
        agency_id=agency_id,
    ).one_or_none()

    if officer is None:
        return None

    return _serialize(officer)


def update_qualification_facts(
    agency_id,
    officer_id,
    *,
    verified_education_level=None,
    verified_military_months=None,
    education_supplied=False,
    military_supplied=False,
):
    officer = Officer.query.filter_by(
        id=officer_id,
        agency_id=agency_id,
    ).one_or_none()

    if officer is None:
        return None

    if education_supplied:
        education = verified_education_level

        if isinstance(education, str):
            education = education.strip().upper()

        if education == "":
            education = None

        if (
            education is not None
            and education not in EDUCATION_LEVELS
        ):
            raise QualificationFactsError(
                "verified_education_level must be one of "
                "ASSOCIATE, BACHELOR, MASTER, DOCTORATE, "
                "or null."
            )

        officer.verified_education_level = education

    if military_supplied:
        months = verified_military_months

        if isinstance(months, bool):
            raise QualificationFactsError(
                "verified_military_months must be a "
                "non-negative integer."
            )

        try:
            months = int(months)
        except (TypeError, ValueError):
            raise QualificationFactsError(
                "verified_military_months must be a "
                "non-negative integer."
            )

        if months < 0:
            raise QualificationFactsError(
                "verified_military_months must be a "
                "non-negative integer."
            )

        officer.verified_military_months = months

    db.session.commit()

    return _serialize(officer)
