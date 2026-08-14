# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

import json
from datetime import date
from pathlib import Path


RULE_DIR = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
)

RULE_FILES = {
    "Basic Peace Officer":
        "peace_officer_proficiency_basic_2026_02_09.json",
    "Intermediate Peace Officer":
        "peace_officer_proficiency_intermediate_2026_02_09.json",
    "Advanced Peace Officer":
        "peace_officer_proficiency_advanced_2026_02_09.json",
    "Master Peace Officer":
        "peace_officer_proficiency_master_2026_02_09.json",
}


def load_proficiency_rule(
    certificate,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    filename = RULE_FILES.get(certificate)

    if filename is None:
        raise ValueError(
            f"No proficiency rule for {certificate}."
        )

    path = RULE_DIR / filename

    with path.open() as file:
        rule = json.load(file)

    effective_date = date.fromisoformat(
        rule["effective_date"]
    )

    if evaluation_date < effective_date:
        raise ValueError(
            "No applicable proficiency rule version "
            f"for {certificate} on {evaluation_date}."
        )

    return rule
