#!/usr/bin/env python3
"""
Build the Paradigm Training Manager v0.4.19 U.S. Copyright Office
trade-secret source-code deposit package.

This script is intended to be run from the root of the
paradigm-training-manager Git repository.

Deposit strategy:
- Treat PTM source code as containing trade secret/confidential material.
- Use the U.S. Copyright Office option permitting the first 10 pages and
  last 10 pages of source code with no blocking/redaction.
- Use the Office's rule of thumb of 40 lines of code per page.
- Therefore select the first 400 and last 400 lines of a deterministic
  production-source corpus.
- Include a separate copyright-notice page.
"""

from pathlib import Path
import hashlib
import json
import sys
import zipfile

EXPECTED_VERSION = "0.4.19"
LINES_PER_PAGE = 40
PAGES_EACH_END = 10
LINES_EACH_END = LINES_PER_PAGE * PAGES_EACH_END

REPO = Path.cwd()
OUT = REPO / "copyright_deposit_v0.4.19"
SOURCE_TXT = OUT / "PTM_v0.4.19_Source_Code_Deposit.txt"
NOTICE_TXT = OUT / "PTM_v0.4.19_Copyright_Notice.txt"
STATEMENT_TXT = OUT / "PTM_v0.4.19_Trade_Secret_Statement.txt"
MANIFEST_JSON = OUT / "PTM_v0.4.19_Deposit_Manifest.json"
ZIP_PATH = REPO / "PTM_v0.4.19_Copyright_Deposit.zip"

COPYRIGHT_NOTICE = (
    "Copyright © 2026 Paradigm Strategic Partners, LLC. "
    "All Rights Reserved."
)
PRODUCT = "Paradigm Training Manager™"
SOFTWARE_ID = "PTM-PSP-2026"


def stop(msg):
    raise SystemExit(f"STOP: {msg}")


def source_files():
    files = []

    files.extend(
        sorted(
            p for p in (REPO / "backend" / "app").rglob("*.py")
            if "__pycache__" not in p.parts
            and ".before-" not in p.name
        )
    )

    run_py = REPO / "backend" / "run.py"
    if run_py.exists():
        files.append(run_py)

    files.extend(
        sorted(
            p for p in (REPO / "frontend" / "src").rglob("*")
            if p.is_file()
            and p.suffix in {".js", ".jsx", ".ts", ".tsx", ".css"}
            and ".before-" not in p.name
        )
    )

    vite = REPO / "frontend" / "vite.config.js"
    if vite.exists():
        files.append(vite)

    # Deliberately exclude:
    # frontend/index.html (Copyright Office does not treat HTML as a
    # computer program for this purpose)
    # backend/app/rules/data (TCOLE/government-derived rule data)
    # backend/migrations (generated migration files)
    # tests, fixtures, backups, dist, node_modules, .venv

    return files


def rel(path):
    return path.relative_to(REPO).as_posix()


def corpus_lines(files):
    lines = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        lines.append(f"===== FILE: {rel(path)} =====")
        lines.extend(text.splitlines())
        lines.append(f"===== END FILE: {rel(path)} =====")
        lines.append("")

    return lines


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


version_file = REPO / "VERSION"
if not version_file.exists():
    stop("VERSION file not found. Run this from the PTM repository root.")

version = version_file.read_text().strip()
if version != EXPECTED_VERSION:
    stop(f"Expected VERSION {EXPECTED_VERSION}, found {version!r}.")

files = source_files()
if not files:
    stop("No PTM production source files found.")

OUT.mkdir(exist_ok=True)

all_lines = corpus_lines(files)
if len(all_lines) < LINES_EACH_END * 2:
    stop(
        f"Source corpus contains only {len(all_lines)} lines. "
        "The first/last 10-page method expects at least 800 lines."
    )

first_lines = all_lines[:LINES_EACH_END]
last_lines = all_lines[-LINES_EACH_END:]

header = [
    PRODUCT,
    f"Version {EXPECTED_VERSION}",
    f"Software ID: {SOFTWARE_ID}",
    COPYRIGHT_NOTICE,
    "",
    "U.S. COPYRIGHT OFFICE SOURCE-CODE DEPOSIT",
    "TRADE SECRET / CONFIDENTIAL MATERIAL",
    "",
    (
        "This deposit uses the trade-secret option consisting of the "
        "first 10 pages and last 10 pages of source code with no "
        "blocked-out portions."
    ),
    (
        "For equivalent-unit calculation, this package uses 40 lines "
        "of code per page, for 400 lines from the beginning and "
        "400 lines from the end of the source-code corpus."
    ),
    "",
    "BEGIN FIRST 10 PAGES / 400 LINES",
    "",
]

middle = [
    "",
    "END FIRST 10 PAGES / 400 LINES",
    "",
    "BEGIN LAST 10 PAGES / 400 LINES",
    "",
]

footer = [
    "",
    "END LAST 10 PAGES / 400 LINES",
    "",
    COPYRIGHT_NOTICE,
    f"Software ID: {SOFTWARE_ID}",
]

SOURCE_TXT.write_text(
    "\n".join(header + first_lines + middle + last_lines + footer) + "\n",
    encoding="utf-8",
)

NOTICE_TXT.write_text(
    "\n".join([
        PRODUCT,
        f"Version {EXPECTED_VERSION}",
        f"Software ID: {SOFTWARE_ID}",
        "",
        COPYRIGHT_NOTICE,
        "",
        "Copyright Owner:",
        "Paradigm Strategic Partners, LLC",
        "",
        "Author:",
        "Kenneth R. Brown, Jr.",
        "",
    ]),
    encoding="utf-8",
)

STATEMENT_TXT.write_text(
    "\n".join([
        "TRADE SECRET / CONFIDENTIAL MATERIAL STATEMENT",
        "",
        f"Work: {PRODUCT}",
        f"Version: {EXPECTED_VERSION}",
        f"Software ID: {SOFTWARE_ID}",
        "",
        (
            "The source code for this computer program contains trade "
            "secret and confidential material."
        ),
        (
            "The deposit accompanying this application consists of the "
            "first ten pages and last ten pages of source code with no "
            "blocked-out portions, using the U.S. Copyright Office "
            "trade-secret deposit option."
        ),
        "",
        "Copyright Claimant:",
        "Paradigm Strategic Partners, LLC",
        "",
        COPYRIGHT_NOTICE,
        "",
    ]),
    encoding="utf-8",
)

manifest = {
    "work": "Paradigm Training Manager",
    "product_mark": PRODUCT,
    "version": EXPECTED_VERSION,
    "software_id": SOFTWARE_ID,
    "copyright_owner": "Paradigm Strategic Partners, LLC",
    "author": "Kenneth R. Brown, Jr.",
    "deposit_method": (
        "Trade-secret option: first 10 and last 10 pages of source code, "
        "no blocking/redaction"
    ),
    "equivalent_unit_rule": "40 lines of code = 1 page",
    "first_lines": LINES_EACH_END,
    "last_lines": LINES_EACH_END,
    "total_source_corpus_lines": len(all_lines),
    "production_source_files_considered": [rel(p) for p in files],
    "excluded_categories": [
        "TCOLE/government-derived rule data",
        "database migrations",
        "test code and fixtures",
        "frontend HTML as computer-program source",
        "generated build output",
        "third-party dependencies",
        "backup files",
    ],
    "files": {},
}

for p in [SOURCE_TXT, NOTICE_TXT, STATEMENT_TXT]:
    manifest["files"][p.name] = {
        "sha256": sha256(p),
        "bytes": p.stat().st_size,
    }

MANIFEST_JSON.write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
)

if ZIP_PATH.exists():
    ZIP_PATH.unlink()

with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    for p in [SOURCE_TXT, NOTICE_TXT, STATEMENT_TXT, MANIFEST_JSON]:
        z.write(p, arcname=p.name)

print("")
print("PTM COPYRIGHT DEPOSIT PACKAGE CREATED")
print(f"Version: {EXPECTED_VERSION}")
print(f"Production source files considered: {len(files)}")
print(f"Total source corpus lines: {len(all_lines)}")
print(f"First lines deposited: {len(first_lines)}")
print(f"Last lines deposited: {len(last_lines)}")
print("")
print(f"Primary deposit file: {SOURCE_TXT}")
print(f"Trade-secret statement: {STATEMENT_TXT}")
print(f"Copyright notice file: {NOTICE_TXT}")
print(f"Manifest: {MANIFEST_JSON}")
print(f"ZIP package: {ZIP_PATH}")
print("")
print("IMPORTANT:")
print("For the Copyright Office upload, use the primary source-code deposit")
print("file and the trade-secret statement as appropriate. The ZIP is an")
print("internal archival package and should not be uploaded unless you have")
print("a specific reason to submit a compressed file.")
