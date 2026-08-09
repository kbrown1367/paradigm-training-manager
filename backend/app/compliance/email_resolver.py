import re
import unicodedata


SUPPORTED_EMAIL_PATTERNS = {
    "FIRST_INITIAL_LAST",
    "FIRST_DOT_LAST",
    "FIRST_LAST",
    "LAST_FIRST_INITIAL",
}


def _normalize_name_part(value):
    """
    Normalize a person's name for use in an email address.

    Examples:
        O'Brien -> obrien
        De La Cruz -> delacruz
        José -> jose
        Smith-Jones -> smithjones
    """
    if not value:
        return ""

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    return re.sub(
        r"[^a-zA-Z0-9]",
        "",
        value,
    ).lower()


def _normalize_domain(value):
    if not value:
        return None

    value = value.strip().lower()

    if value.startswith("@"):
        value = value[1:]

    return value or None


def resolve_officer_email(officer):
    """
    Resolve an officer's email address.

    Resolution precedence:

    1. Explicit officer email override.
    2. Agency email convention.
    3. No resolved email.

    Returns a dictionary so callers can distinguish an
    explicit address from a generated address.
    """

    if officer.email_override:
        override = officer.email_override.strip()

        if override:
            return {
                "email": override,
                "source": "OFFICER_OVERRIDE",
                "pattern": None,
            }

    agency = officer.agency

    if agency is None:
        return {
            "email": None,
            "source": None,
            "pattern": None,
        }

    domain = _normalize_domain(
        agency.email_domain
    )
    pattern = agency.email_pattern

    if (
        not domain
        or pattern not in SUPPORTED_EMAIL_PATTERNS
    ):
        return {
            "email": None,
            "source": None,
            "pattern": pattern,
        }

    first = _normalize_name_part(
        officer.first_name
    )
    last = _normalize_name_part(
        officer.last_name
    )

    if not first or not last:
        return {
            "email": None,
            "source": None,
            "pattern": pattern,
        }

    if pattern == "FIRST_INITIAL_LAST":
        local_part = first[0] + last

    elif pattern == "FIRST_DOT_LAST":
        local_part = f"{first}.{last}"

    elif pattern == "FIRST_LAST":
        local_part = first + last

    elif pattern == "LAST_FIRST_INITIAL":
        local_part = last + first[0]

    else:
        return {
            "email": None,
            "source": None,
            "pattern": pattern,
        }

    return {
        "email": f"{local_part}@{domain}",
        "source": "AGENCY_PATTERN",
        "pattern": pattern,
    }
