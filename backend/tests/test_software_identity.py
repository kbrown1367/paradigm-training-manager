from app.software_identity import (
    COPYRIGHT_START_YEAR,
    OWNER,
    PRODUCT_ABBREVIATION,
    PRODUCT_MARK,
    PRODUCT_NAME,
    SOFTWARE_ID,
    get_copyright_notice,
    get_software_identity,
    get_version,
)


def test_software_identity_constants():
    assert PRODUCT_NAME == "Paradigm Training Manager"
    assert PRODUCT_MARK == "Paradigm Training Manager™"
    assert PRODUCT_ABBREVIATION == "PTM"

    assert (
        OWNER
        == "Paradigm Strategic Partners, LLC"
    )

    assert COPYRIGHT_START_YEAR == 2026
    assert SOFTWARE_ID == "PTM-PSP-2026"


def test_copyright_notice_start_year():
    assert get_copyright_notice(
        year=2026,
    ) == (
        "© 2026 Paradigm Strategic Partners, LLC. "
        "All Rights Reserved."
    )


def test_copyright_notice_future_year():
    assert get_copyright_notice(
        year=2028,
    ) == (
        "© 2026-2028 "
        "Paradigm Strategic Partners, LLC. "
        "All Rights Reserved."
    )


def test_version_reads_root_version_file():
    assert get_version() == "0.6.2"


def test_software_identity_payload():
    identity = get_software_identity(
        version="0.4.19",
        year=2026,
    )

    assert identity == {
        "product_name": "Paradigm Training Manager",
        "product_mark": "Paradigm Training Manager™",
        "product_abbreviation": "PTM",
        "software_id": "PTM-PSP-2026",
        "owner": "Paradigm Strategic Partners, LLC",
        "copyright": (
            "© 2026 Paradigm Strategic Partners, LLC. "
            "All Rights Reserved."
        ),
        "version": "0.4.19",
    }


def test_default_identity_reads_current_version():
    identity = get_software_identity(
        year=2026,
    )

    assert identity["version"] == "0.6.2"
    assert identity["software_id"] == "PTM-PSP-2026"
