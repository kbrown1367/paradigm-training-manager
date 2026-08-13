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
        "verified_college_credit_hours":
            officer.verified_college_credit_hours,
        "verified_military_months":
            officer.verified_military_months,
        "verified_jailer_cultural_diversity_exemption":
            officer.verified_jailer_cultural_diversity_exemption,
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
    verified_college_credit_hours=None,
    verified_military_months=None,
    education_supplied=False,
    college_hours_supplied=False,
    military_supplied=False,
    verified_jailer_cultural_diversity_exemption=None,
    jailer_exemption_supplied=False,
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

    if college_hours_supplied:
        college_hours = verified_college_credit_hours

        if college_hours in {None, ""}:
            college_hours = None
        else:
            if isinstance(college_hours, bool):
                raise QualificationFactsError(
                    "verified_college_credit_hours must be a "
                    "non-negative integer or null."
                )

            try:
                college_hours = int(college_hours)
            except (TypeError, ValueError):
                raise QualificationFactsError(
                    "verified_college_credit_hours must be a "
                    "non-negative integer or null."
                )

            if college_hours < 0:
                raise QualificationFactsError(
                    "verified_college_credit_hours must be a "
                    "non-negative integer or null."
                )

        officer.verified_college_credit_hours = (
            college_hours
        )

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

    if jailer_exemption_supplied:
        exemption = (
            verified_jailer_cultural_diversity_exemption
        )

        if not isinstance(exemption, bool):
            raise QualificationFactsError(
                "verified_jailer_cultural_diversity_exemption "
                "must be true or false."
            )

        officer.verified_jailer_cultural_diversity_exemption = (
            exemption
        )

    db.session.commit()

    return _serialize(officer)
