# Paradigm Training Manager Changelog

All notable PTM releases are documented here.

## v0.2.13 - 2026-08-10

### County Jailer Compliance
- Added County Jailer legislative compliance evaluation.
- Added current-unit evaluation for Interacting with Veterans in a Jail Setting (#4902).
- Added current-cycle evaluation for Cultural Diversity (#3939).
- Added agency-verified Jailer Cultural Diversity exemption handling.
- Added safe migration support for the new exemption fact with existing employees defaulting to false.
- Added dynamic TCOLE unit and cycle handling for County Jailer requirements.
- Added automatic reset of unit-based requirements across unit boundaries.
- Added automatic reset of cycle-based requirements across four-year cycle boundaries.
- Added County Jailer as a first-class component in the unified employee compliance profile.
- Added support for employees holding both Peace Officer and County Jailer licenses without cross-license interference.

### Validation
- Added County Jailer compliance regression tests.
- Added unified profile tests for County Jailer and dual-license employees.
- Full backend test suite passed with 256 tests.

## v0.2.12 - 2026-08-10

### Peace Officer Proficiency Certification
- Added data-driven Basic, Intermediate, Advanced, and Master Peace Officer proficiency certification rules.
- Added next-proficiency-certificate eligibility evaluation.
- Added service-and-training, education, and military qualification pathways.
- Added best-available service and training pathway diagnostics.
- Added exact service-year and training-hour deficiencies.
- Added Completed and Missing status for required proficiency courses.
- Added accepted TCOLE course numbers and the actual course used to satisfy completed requirements.
- Added clear distinction between TCOLE-awarded proficiency certificates and PTM-calculated eligibility.
- Added employee workspace proficiency presentation with visible eligibility, pathway, quantitative deficiencies, and course evidence.

### Qualification Information
- Added agency-verified education as a fallback when TCOLE does not report education.
- Added qualifying military service tracking.
- Military service defaults to no qualifying military service unless an administrator records otherwise.
- Added tenant-scoped qualification-facts API and employee workspace controls.
- Qualification changes immediately recalculate proficiency eligibility.

### TCOLE Import
- Expanded the standard PTM TCOLE import from three reports to four reports.
- Added Department Licensee Search Report import support.
- Added Peace Officer License date extraction.
- Added peace-officer service start date population from the TCOLE Peace Officer License date.
- Added import tracking for Licensee Search rows, Peace Officer License rows, service dates populated, updated, unchanged, and unmatched records.
- Updated the browser import interface for all four official TCOLE CSV reports.

### Validation
- Added regression coverage for proficiency pathways, qualification facts, course requirements, and service/training deficiencies.
- Full backend test suite passed with 238 tests at release validation.
- Frontend production build passed.

## v0.2.11 - 2026-08-09
- Added employee compliance workspace.
- Added employee compliance email functionality.
- Added assignment and credential information within the employee workspace.

## v0.2.10
- Added highest-certificate executive dashboard filters.

## v0.2.9
- Added executive compliance dashboard.

## v0.2.8
- Added unified officer compliance profiles.

## v0.2.7
- Added supervisor compliance rules and evidence-based findings.

## v0.2.6
- Added Public Information Officer compliance and TDEM credential verification.

## v0.2.5
- Added Police Chief compliance rules and course equivalencies.

## v0.2.4
- Added officer assignment management.

## v0.2.3
- Added workforce context and dynamic TCOLE calendar.

## v0.2.2
- Added Peace Officer compliance engine.

## v0.2.1
- Added first PTM browser import interface.

## v0.2.0
- Added required three-file TCOLE import workflow.

## v0.1.9
- Added TCOLE cycle-hours reconciliation.

## v0.1.8
- Validated real TCOLE two-file import.

## v0.1.7
- Added TCOLE import API.

## v0.1.6
- Added import summary and validation results.

## v0.1.5
- Added atomic TCOLE import batch tracking.

## v0.1.4
- See Git history for release details.

## v0.1.3
- See Git history for release details.

## v0.1.2
- See Git history for release details.

## v0.1.1
- See Git history for release details.

## v0.1.0
- Initial PTM project baseline.
