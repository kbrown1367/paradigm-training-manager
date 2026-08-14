# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

PEACE_OFFICER_CERTIFICATES = {
    "Basic Peace Officer": 1,
    "Intermediate Peace Officer": 2,
    "Advanced Peace Officer": 3,
    "Master Peace Officer": 4,
}

CERTIFICATE_LEVELS = {
    1: "BASIC",
    2: "INTERMEDIATE",
    3: "ADVANCED",
    4: "MASTER",
}


def get_highest_peace_officer_certificate(officer):
    qualifying = [
        award
        for award in officer.awards
        if (
            award.award_type == "Certificate"
            and award.award_name in PEACE_OFFICER_CERTIFICATES
        )
    ]

    if not qualifying:
        return {
            "highest_certificate": None,
            "certificate_level": None,
            "highest_certificate_date": None,
        }

    highest_rank = max(
        PEACE_OFFICER_CERTIFICATES[award.award_name]
        for award in qualifying
    )

    highest_awards = [
        award
        for award in qualifying
        if PEACE_OFFICER_CERTIFICATES[
            award.award_name
        ] == highest_rank
    ]

    highest_award = max(
        highest_awards,
        key=lambda award: award.award_date,
    )

    return {
        "highest_certificate": highest_award.award_name,
        "certificate_level": CERTIFICATE_LEVELS[
            highest_rank
        ],
        "highest_certificate_date": (
            highest_award.award_date.isoformat()
        ),
    }
