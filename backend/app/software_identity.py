"""
Paradigm Training Manager™ software identity.

Copyright © 2026 Paradigm Strategic Partners, LLC.
All Rights Reserved.

Paradigm Training Manager™ is proprietary and confidential software.
"""

from datetime import date
from pathlib import Path


PRODUCT_NAME = "Paradigm Training Manager"
PRODUCT_MARK = "Paradigm Training Manager™"
PRODUCT_ABBREVIATION = "PTM"

OWNER = "Paradigm Strategic Partners, LLC"
COPYRIGHT_START_YEAR = 2026

SOFTWARE_ID = "PTM-PSP-2026"


def get_copyright_notice(year=None):
    current_year = year or date.today().year

    if current_year <= COPYRIGHT_START_YEAR:
        year_text = str(COPYRIGHT_START_YEAR)
    else:
        year_text = (
            f"{COPYRIGHT_START_YEAR}-{current_year}"
        )

    return (
        f"© {year_text} {OWNER}. "
        "All Rights Reserved."
    )


def get_version():
    version_path = (
        Path(__file__).resolve().parents[2]
        / "VERSION"
    )

    if not version_path.exists():
        return "unknown"

    return version_path.read_text().strip()


def get_software_identity(
    version=None,
    year=None,
):
    return {
        "product_name": PRODUCT_NAME,
        "product_mark": PRODUCT_MARK,
        "product_abbreviation": PRODUCT_ABBREVIATION,
        "software_id": SOFTWARE_ID,
        "owner": OWNER,
        "copyright": get_copyright_notice(
            year=year,
        ),
        "version": (
            version
            if version is not None
            else get_version()
        ),
    }
