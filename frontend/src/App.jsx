import { useEffect, useState } from "react";
import "./App.css";

function FileField({ label, description, file, onChange }) {
  return (
    <div className="file-field">
      <div className="file-copy">
        <label>{label}</label>
        <p>{description}</p>
      </div>

      <div className="file-control">
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(event) =>
            onChange(event.target.files?.[0] || null)
          }
        />

        {file && (
          <div className="selected-file">
            Selected: {file.name}
          </div>
        )}
      </div>
    </div>
  );
}

function ResultCard({ label, value }) {
  return (
    <div className="result-card">
      <div className="result-value">{value ?? 0}</div>
      <div className="result-label">{label}</div>
    </div>
  );
}

function DashboardSummaryCard({
  label,
  value,
  status,
  active,
  onClick,
}) {
  return (
    <button
      type="button"
      className={
        `dashboard-summary-card ${status || ""}` +
        (active ? " active" : "")
      }
      onClick={onClick}
    >
      <div className="dashboard-summary-value">
        {value ?? 0}
      </div>
      <div className="dashboard-summary-label">
        {label}
      </div>
    </button>
  );
}

function formatDashboardDate(value) {
  if (!value) {
    return "None";
  }

  const [year, month, day] = value.split("-");

  if (!year || !month || !day) {
    return value;
  }

  return `${Number(month)}/${Number(day)}/${year}`;
}

function formatAssignment(value) {
  return value
    .toLowerCase()
    .split("_")
    .map(
      (word) =>
        word.charAt(0).toUpperCase() + word.slice(1)
    )
    .join(" ");
}

function EmployeeComplianceCard({
  employee,
  onOpen,
}) {
  const name = [
    employee.first_name,
    employee.middle_name,
    employee.last_name,
    employee.suffix,
  ]
    .filter(Boolean)
    .join(" ");

  const assignments = employee.assignments?.length
    ? employee.assignments
        .map(formatAssignment)
        .join(" • ")
    : "No additional assignments";

  return (
    <article
      className={
        `employee-compliance-card ` +
        employee.overall_status.toLowerCase()
      }
      role="button"
      tabIndex={0}
      onClick={() => onOpen(employee)}
      onKeyDown={(event) => {
        if (
          event.key === "Enter" ||
          event.key === " "
        ) {
          event.preventDefault();
          onOpen(employee);
        }
      }}
    >
      <div className="employee-card-header">
        <div>
          <div className="employee-name-row">
            <h3>{name}</h3>

            {employee.review_required && (
              <span className="review-flag">
                Agency Review
              </span>
            )}
          </div>

          <div className="employee-meta">
            <span>PID {employee.tcole_pid}</span>
            <span>•</span>
            <span>
              {formatEmployeeCertificates(
                employee,
                employee.proficiency_advancement
              )}
            </span>
            <span>•</span>
            <span>{assignments}</span>
          </div>
        </div>

        <span
          className={
            `employee-status ` +
            employee.overall_status.toLowerCase()
          }
        >
          {employee.overall_status === "NONCOMPLIANT"
            ? "NONCOMPLIANT"
            : employee.overall_status === "DUE"
              ? "TRAINING DUE"
              : employee.overall_status === "NOT_EVALUATED"
                ? "NOT EVALUATED"
                : employee.overall_status.replaceAll("_", " ")}
        </span>
      </div>

      {employee.priority_findings?.length > 0 ? (
        <div className="priority-findings">
          {employee.priority_findings.map(
            (finding, index) => (
              <div
                className="priority-finding"
                key={`${finding.type}-${index}`}
              >
                <span
                  className={
                    `finding-status ` +
                    finding.normalized_status.toLowerCase()
                  }
                >
                  {finding.normalized_status === "OUTSTANDING"
                    ? "DUE"
                    : finding.normalized_status.replaceAll(
                        "_",
                        " "
                      )}
                </span>

                <span className="finding-message">
                  {finding.message ||
                    finding.type?.replaceAll("_", " ")}
                </span>
              </div>
            )
          )}
        </div>
      ) : employee.overall_status === "NOT_EVALUATED" ? (
        <div className="not-evaluated-message">
          PTM does not currently have an applicable
          compliance rule set for this employee.
        </div>
      ) : (
        <div className="no-findings">
          No outstanding compliance requirements.
        </div>
      )}

      <div className="employee-card-footer">
        <div>
          {employee.overdue_count > 0 && (
            <span>
              {employee.overdue_count} overdue
            </span>
          )}

          {employee.outstanding_count > 0 && (
            <span>
              {employee.outstanding_count} outstanding
            </span>
          )}
        </div>

        <div>
          Next due:{" "}
          <strong>
            {formatDashboardDate(
              employee.next_due_date
            )}
          </strong>
        </div>
      </div>
    </article>
  );
}

function WorkspaceStatus({ status }) {
  const label =
    status === "DUE"
      ? "TRAINING DUE"
      : status === "NOT_EVALUATED"
        ? "NOT EVALUATED"
        : status?.replaceAll("_", " ");

  return (
    <span
      className={
        `employee-status ` +
        (status || "pending_review").toLowerCase()
      }
    >
      {label}
    </span>
  );
}

function RequirementList({
  title,
  items,
  emptyMessage,
}) {
  return (
    <section className="workspace-panel">
      <div className="workspace-panel-heading">
        <h3>{title}</h3>
        <span>{items?.length || 0}</span>
      </div>

      {items?.length ? (
        <div className="workspace-requirements">
          {items.map((item, index) => (
            <div
              className="workspace-requirement"
              key={`${item.type || "requirement"}-${index}`}
            >
              <div>
                <strong>
                  {item.message ||
                    item.type?.replaceAll("_", " ") ||
                    "Compliance requirement"}
                </strong>

                {item.due_date && (
                  <span>
                    Due{" "}
                    {formatDashboardDate(
                      item.due_date
                    )}
                  </span>
                )}
              </div>

              <span
                className={
                  `finding-status ` +
                  (
                    item.normalized_status ||
                    item.status ||
                    "pending_review"
                  ).toLowerCase()
                }
              >
                {(
                  item.normalized_status ||
                  item.status ||
                  "REVIEW"
                )
                  .replaceAll("_", " ")}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="workspace-empty">
          {emptyMessage}
        </div>
      )}
    </section>
  );
}

function formatEmployeeCertificates(
  employee,
  proficiencyAdvancement = null
) {
  const certificates = [];

  const addCertificate = (label, certificate) => {
    if (!certificate) {
      return;
    }

    const value = `${label}: ${certificate}`;

    if (!certificates.includes(value)) {
      certificates.push(value);
    }
  };

  if (proficiencyAdvancement?.peace_officer) {
    addCertificate(
      "Peace Officer",
      proficiencyAdvancement.peace_officer.current_certificate
    );
  } else if (
    employee.highest_certificate &&
    employee.highest_certificate.includes("Peace Officer")
  ) {
    addCertificate(
      "Peace Officer",
      employee.highest_certificate
    );
  }

  if (proficiencyAdvancement?.jailer) {
    addCertificate(
      "County Jailer",
      proficiencyAdvancement.jailer.current_certificate
    );
  }

  if (proficiencyAdvancement?.telecommunicator) {
    addCertificate(
      "Telecommunicator",
      proficiencyAdvancement.telecommunicator.current_certificate
    );
  }

  if (certificates.length === 0) {
    return "No proficiency certificate";
  }

  return certificates.join(" • ");
}

function formatProficiencyStatus(status) {
  const labels = {
    ELIGIBLE: "Eligible",
    NOT_ELIGIBLE: "Not Yet Eligible",
    PENDING_COURSE_EVALUATION: "Course Review Needed",
    INSUFFICIENT_DATA: "Insufficient Data",
    NOT_APPLICABLE: "Not Applicable",
    TERMINAL: "Highest Certificate Achieved",
  };

  return (
    labels[status] ||
    status?.replaceAll("_", " ").toLowerCase() ||
    "Unknown"
  );
}

function formatProficiencyPathway(pathway) {
  if (!pathway) {
    return null;
  }

  const labels = {
    SERVICE: "Service",
    SERVICE_TRAINING: "Service + Training",
    EDUCATION: "Education",
    MILITARY: "Military Service",
  };

  return labels[pathway.type] || pathway.type;
}

function ProficiencyAdvancementPanel({
  advancement,
  trackLabel,
}) {
  if (!advancement) {
    return null;
  }

  const status = advancement.status;
  const pathway = formatProficiencyPathway(
    advancement.qualifying_pathway
  );

  const bestPathway =
    advancement.best_available_pathway;

  const displayPathway =
    advancement.qualifying_pathway || bestPathway;

  const displayPathwayLabel =
    formatProficiencyPathway(displayPathway);

  const serviceRequirement =
    displayPathway?.service_years ?? null;

  const trainingRequirement =
    displayPathway?.type === "SERVICE_TRAINING"
      ? displayPathway.training_hours
      : null;

  const militaryRequirement =
    displayPathway?.type === "MILITARY"
      ? displayPathway.military_years
      : null;

  const serviceShort =
    displayPathway?.service_years_short != null
      ? Number(displayPathway.service_years_short)
      : 0;

  const trainingShort =
    displayPathway?.type === "SERVICE_TRAINING"
      ? Number(
          displayPathway.training_hours_short || 0
        )
      : 0;

  const militaryMonths =
    Number(
      advancement.verified_military_months || 0
    );

  const militaryYears =
    militaryMonths / 12;

  const militaryMonthsShort =
    displayPathway?.type === "MILITARY"
      ? Number(
          displayPathway.military_months_short || 0
        )
      : 0;

  if (status === "NOT_APPLICABLE") {
    return (
      <section className="workspace-panel proficiency-preview">
        <div className="workspace-panel-heading">
          <h3>Next Proficiency Certificate</h3>
        </div>

        <div className="workspace-empty">
          {trackLabel} proficiency certification does not
          apply to this employee.
        </div>
      </section>
    );
  }

  return (
    <section className="workspace-panel proficiency-preview">
      <div className="workspace-panel-heading">
        <div>
          <h3>{trackLabel} Proficiency</h3>
          <p>
            TCOLE proficiency advancement based on currently
            available agency records.
          </p>
        </div>

        <span
          className={`proficiency-status ${status || ""}`}
        >
          {formatProficiencyStatus(status)}
        </span>
      </div>

      <div className="proficiency-certificate-row">
        <div>
          <span>Current Certificate</span>
          <strong>
            {advancement.current_certificate ||
              "No proficiency certificate"}
          </strong>
        </div>

        <div className="proficiency-arrow">→</div>

        <div>
          <span>Next Certificate</span>
          <strong>
            {advancement.next_certificate ||
              "No higher certificate"}
          </strong>
        </div>
      </div>

      <div className="proficiency-facts">
        <div
          className={
            serviceShort > 0
              ? "proficiency-fact deficient"
              : serviceRequirement != null
                ? "proficiency-fact satisfied"
                : "proficiency-fact"
          }
        >
          <span>{trackLabel} Service</span>

          <strong>
            {advancement.service_years != null
              ? serviceRequirement != null
                ? `${advancement.service_years} / ${serviceRequirement} years required`
                : `${advancement.service_years} years`
              : "Not available"}
          </strong>

          {serviceRequirement != null && (
            <small>
              {serviceShort > 0
                ? `${serviceShort} ${
                    serviceShort === 1
                      ? "year"
                      : "years"
                  } short`
                : "✓ Service requirement met"}
            </small>
          )}
        </div>

        <div className="proficiency-fact">
          <span>
            Total Career/Professional Hours
          </span>
          <strong>
            {Number(
              advancement
                .career_professional_hours || 0
            ).toLocaleString()}
          </strong>
        </div>

        <div
          className={
            trackLabel === "Telecommunicator" &&
            trainingShort > 0
              ? "proficiency-fact deficient"
              : trackLabel === "Telecommunicator" &&
                  trainingRequirement != null
                ? "proficiency-fact satisfied"
                : "proficiency-fact"
          }
        >
          <span>Total TCOLE Course Hours</span>

          <strong>
            {advancement.training_hours != null
              ? trackLabel === "Telecommunicator" &&
                  trainingRequirement != null
                ? `${Number(
                    advancement.training_hours
                  ).toLocaleString()} / ${Number(
                    trainingRequirement
                  ).toLocaleString()} required`
                : Number(
                    advancement.training_hours
                  ).toLocaleString()
              : "Not available"}
          </strong>

          <small className="proficiency-source-note">
            Source: TCOLE rptCycleT_All.csv
          </small>



          {trackLabel === "Telecommunicator" &&
            trainingRequirement != null && (
              <small>
                {trainingShort > 0
                  ? `${trainingShort.toLocaleString()} hours short`
                  : "✓ Training requirement met"}
              </small>
            )}
        </div>

        <div
          className={
            trackLabel === "Peace Officer" &&
            trainingShort > 0
              ? "proficiency-fact deficient"
              : trackLabel === "Peace Officer" &&
                  trainingRequirement != null
                ? "proficiency-fact satisfied"
                : "proficiency-fact"
          }
        >
          <span>Total Hours</span>

          <strong>
            {advancement.total_hours != null
              ? trackLabel === "Peace Officer" &&
                  trainingRequirement != null
                ? `${Number(
                    advancement.total_hours
                  ).toLocaleString()} / ${Number(
                    trainingRequirement
                  ).toLocaleString()} required`
                : Number(
                    advancement.total_hours
                  ).toLocaleString()
              : "Not available"}
          </strong>

          <small className="proficiency-source-note">
            Calculated from the values shown
          </small>

          {trackLabel === "Peace Officer" &&
            trainingRequirement != null && (
              <small>
                {trainingShort > 0
                  ? `${trainingShort.toLocaleString()} hours short`
                  : "✓ Training requirement met"}
              </small>
            )}
        </div>

        {displayPathway?.type === "MILITARY" && (
          <div
            className={
              militaryMonthsShort > 0
                ? "proficiency-fact deficient"
                : "proficiency-fact satisfied"
            }
          >
            <span>Qualifying Military Service</span>

            <strong>
              {`${militaryYears.toLocaleString(
                undefined,
                {
                  maximumFractionDigits: 2,
                }
              )} / ${militaryRequirement} years required`}
            </strong>

            <small>
              {militaryMonthsShort > 0
                ? `${militaryMonthsShort} ${
                    militaryMonthsShort === 1
                      ? "month"
                      : "months"
                  } short`
                : "✓ Military service requirement met"}
            </small>
          </div>
        )}

        <div className="proficiency-fact">
          <span>Education</span>
          <strong>
            {advancement.education_level
              ? formatEducationLevel(
                  advancement.education_level
                )
              : advancement.college_credit_hours != null
                ? `${Number(
                    advancement.college_credit_hours
                  ).toLocaleString()} college hours`
                : "Not reported"}
          </strong>
        </div>

        <div
          className={
            status === "NOT_ELIGIBLE" &&
            !advancement.qualifying_pathway &&
            displayPathway
              ? "proficiency-fact deficient"
              : "proficiency-fact"
          }
        >
          <span>Qualifying Pathway</span>

          <strong>
            {status === "TERMINAL"
              ? "Complete"
              : displayPathwayLabel ||
                pathway ||
                "Not yet established"}
          </strong>

          {status === "NOT_ELIGIBLE" &&
            !advancement.qualifying_pathway &&
            displayPathway && (
              <small>
                Requirements not yet met
              </small>
            )}
        </div>
      </div>

      {advancement.course_requirements?.length > 0 && (
        <div className="proficiency-section">
          <strong>Required Proficiency Courses</strong>

          <div className="proficiency-requirements">
            {advancement.course_requirements.map(
              (requirement, index) => (
                <div
                  className="proficiency-requirement"
                  key={
                    requirement.course_number ||
                    requirement.label ||
                    index
                  }
                >
                  <div className="proficiency-course-info">
                    <strong>
                      {requirement.label ||
                        requirement.name ||
                        requirement.course_name ||
                        requirement.course_number ||
                        "Required course"}
                    </strong>

                    {requirement.accepted_courses?.length > 0 && (
                      <span className="proficiency-course-number">
                        {requirement.accepted_courses.length === 1
                          ? `Required: TCOLE Course #${requirement.accepted_courses[0]}`
                          : `Accepted: ${requirement.accepted_courses
                              .map((course) => `#${course}`)
                              .join(" or ")}`}
                      </span>
                    )}

                    {["MET", "COMPLETE"].includes(
                        requirement.status
                      ) &&
                      requirement.satisfied_by?.courses?.length > 0 && (
                        <span className="proficiency-course-match">
                          Satisfied by:{" "}
                          {requirement.satisfied_by.courses
                            .map(
                              (course) =>
                                `TCOLE Course #${course.course_number}`
                            )
                            .join(" + ")}
                        </span>
                      )}
                  </div>

                  <span
                    className={
                      "proficiency-course-status " +
                      (["MET", "COMPLETE"].includes(
                        requirement.status
                      )
                        ? "completed"
                        : requirement.status === "NOT_APPLICABLE"
                          ? "not-applicable"
                          : requirement.status ===
                              "INSUFFICIENT_DATA"
                            ? "insufficient"
                            : "missing")
                    }
                  >
                    {["MET", "COMPLETE"].includes(
                        requirement.status
                      )
                      ? "Completed"
                      : requirement.status === "NOT_APPLICABLE"
                        ? "Not Applicable"
                        : requirement.status ===
                            "INSUFFICIENT_DATA"
                          ? "Needs Information"
                          : "Missing"}
                  </span>
                </div>
              )
            )}
          </div>
        </div>
      )}



      {advancement.insufficient_data_requirements?.length >
        0 && (
        <div className="proficiency-section">
          <strong>Additional Information Needed</strong>

          <ul className="proficiency-missing-list">
            {advancement.insufficient_data_requirements.map(
              (requirement, index) => (
                <li key={index}>{requirement}</li>
              )
            )}
          </ul>
        </div>
      )}
    </section>
  );
}

function formatEducationLevel(level) {
  const labels = {
    ASSOCIATE: "Associate Degree",
    BACHELOR: "Bachelor's Degree",
    MASTER: "Master's Degree",
    DOCTORATE: "Doctorate",
  };

  return labels[level] || "Not reported";
}

function QualificationInformationPanel({
  facts,
  advancement,
  busy,
  error,
  onSave,
}) {
  const [education, setEducation] = useState("");
  const [collegeHours, setCollegeHours] = useState("");
  const [
    militaryTrainingCreditHours,
    setMilitaryTrainingCreditHours,
  ] = useState("");
  const [militaryEnabled, setMilitaryEnabled] =
    useState(false);
  const [militaryYears, setMilitaryYears] =
    useState("0");
  const [militaryMonths, setMilitaryMonths] =
    useState("0");

  useEffect(() => {
    if (!facts) {
      return;
    }

    setEducation(
      facts.verified_education_level || ""
    );

    setCollegeHours(
      facts.verified_college_credit_hours != null
        ? String(facts.verified_college_credit_hours)
        : ""
    );

    setMilitaryTrainingCreditHours(
      facts.verified_military_training_credit_hours != null
        ? String(
            facts.verified_military_training_credit_hours
          )
        : ""
    );

    const totalMonths = Number(
      facts.verified_military_months || 0
    );

    setMilitaryEnabled(totalMonths > 0);
    setMilitaryYears(
      String(Math.floor(totalMonths / 12))
    );
    setMilitaryMonths(
      String(totalMonths % 12)
    );
  }, [
    facts?.officer_id,
    facts?.verified_education_level,
    facts?.verified_college_credit_hours,
    facts?.verified_military_training_credit_hours,
    facts?.verified_military_months,
  ]);

  if (!facts) {
    return (
      <section className="workspace-panel">
        <div className="workspace-panel-heading">
          <div>
            <h3>Qualification Information</h3>
            <p>
              Supplemental information used for TCOLE
              proficiency advancement.
            </p>
          </div>
        </div>

        <div className="workspace-empty">
          Loading qualification information...
        </div>
      </section>
    );
  }

  const effectiveEducation =
    advancement?.education_level || null;

  const totalMilitaryMonths =
    militaryEnabled
      ? Math.max(
          0,
          Number.parseInt(
            militaryYears || "0",
            10
          ) || 0
        ) *
          12 +
        Math.max(
          0,
          Math.min(
            11,
            Number.parseInt(
              militaryMonths || "0",
              10
            ) || 0
          )
        )
      : 0;

  async function handleSubmit(event) {
    event.preventDefault();

    await onSave({
      verified_education_level:
        education || null,
      verified_college_credit_hours:
        collegeHours === ""
          ? null
          : Math.max(
              0,
              Number.parseInt(collegeHours, 10) || 0
            ),
      verified_military_training_credit_hours:
        militaryTrainingCreditHours === ""
          ? null
          : Math.max(
              0,
              Number.parseInt(
                militaryTrainingCreditHours,
                10
              ) || 0
            ),
      verified_military_months:
        totalMilitaryMonths,
    });
  }

  return (
    <section className="workspace-panel qualification-panel">
      <div className="workspace-panel-heading">
        <div>
          <h3>Qualification Information</h3>
          <p>
            Agency-managed facts used when evaluating
            alternate TCOLE proficiency pathways.
          </p>
        </div>
      </div>

      {error && (
        <div className="message error-message">
          {error}
        </div>
      )}

      <form
        className="qualification-form"
        onSubmit={handleSubmit}
      >
        <div className="qualification-block">
          <div className="qualification-heading">
            <div>
              <strong>Education</strong>
              <span>
                TCOLE-reported education takes precedence.
                The agency value below is used only as a
                fallback when TCOLE does not report one.
              </span>
            </div>

            <div className="qualification-effective">
              <span>Effective Education</span>
              <strong>
                {formatEducationLevel(
                  effectiveEducation
                )}
              </strong>
            </div>
          </div>

          <label className="qualification-field">
            <span>Agency-Verified Education</span>

            <select
              value={education}
              disabled={busy}
              onChange={(event) =>
                setEducation(event.target.value)
              }
            >
              <option value="">
                Not reported
              </option>
              <option value="ASSOCIATE">
                Associate Degree
              </option>
              <option value="BACHELOR">
                Bachelor's Degree
              </option>
              <option value="MASTER">
                Master's Degree
              </option>
              <option value="DOCTORATE">
                Doctorate
              </option>
            </select>
          </label>

          <label className="qualification-field">
            <span>College hours from PSR</span>
            <input
              type="number"
              min="0"
              step="1"
              value={collegeHours}
              disabled={busy}
              placeholder="Not reported"
              onChange={(event) =>
                setCollegeHours(event.target.value)
              }
            />
          </label>

          <div className="qualification-no-military">
            TCOLE calculates 20 Career/Professional Hours
            for each college credit hour.
          </div>
        </div>

        <div className="qualification-block">
          <div className="qualification-heading">
            <div>
              <strong>Military</strong>
              <span>
                Military training credit hours and qualifying
                military service duration are separate
                qualification factors.
              </span>
            </div>
          </div>

          <label className="qualification-field">
            <span>
              Additional Military Training Credit Hours
            </span>

            <small className="qualification-helper-text">
              Enter military training credit hours only when
              they are not already included in the employee's
              TCOLE training history. If TCOLE has already
              credited these hours, leave this field blank to
              avoid duplicate credit.
            </small>

            <input
              type="number"
              min="0"
              step="1"
              value={militaryTrainingCreditHours}
              disabled={busy}
              placeholder="Not reported"
              onChange={(event) =>
                setMilitaryTrainingCreditHours(
                  event.target.value
                )
              }
            />
          </label>

          <div className="qualification-heading">
            <div>
              <strong>
                Qualifying Military Service
              </strong>
              <span>
                Use this setting when the employee has
                qualifying military service that may reduce
                the service-time requirement for an alternate
                proficiency pathway. Enter the employee's
                qualifying years and additional months of
                military service.
              </span>
            </div>

            <button
              type="button"
              role="switch"
              aria-checked={militaryEnabled}
              className={
                "assignment-toggle" +
                (militaryEnabled
                  ? " active"
                  : "")
              }
              disabled={busy}
              onClick={() => {
                setMilitaryEnabled(
                  (current) => !current
                );
              }}
            >
              <span className="assignment-toggle-knob" />
              <span className="assignment-toggle-label">
                {militaryEnabled ? "On" : "Off"}
              </span>
            </button>
          </div>

          {militaryEnabled && (
            <div className="military-duration">
              <label className="qualification-field">
                <span>Years</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={militaryYears}
                  disabled={busy}
                  onChange={(event) =>
                    setMilitaryYears(
                      event.target.value
                    )
                  }
                />
              </label>

              <label className="qualification-field">
                <span>Additional Months</span>
                <input
                  type="number"
                  min="0"
                  max="11"
                  step="1"
                  value={militaryMonths}
                  disabled={busy}
                  onChange={(event) =>
                    setMilitaryMonths(
                      event.target.value
                    )
                  }
                />
              </label>
            </div>
          )}

          {!militaryEnabled && (
            <div className="qualification-no-military">
              No qualifying military service recorded.
            </div>
          )}
        </div>

        <div className="qualification-actions">
          <button
            type="submit"
            className="credential-button verify"
            disabled={busy}
          >
            {busy
              ? "Saving..."
              : "Save Qualification Information"}
          </button>
        </div>
      </form>
    </section>
  );
}

function EmployeeWorkspace({
  workspace,
  loading,
  error,
  onBack,
  assignmentSummary,
  assignmentBusy,
  assignmentError,
  credentialVerifications,
  credentialBusy,
  credentialError,
  qualificationFacts,
  qualificationBusy,
  qualificationError,
  onSaveQualificationFacts,
  onActivateAssignment,
  onEndAssignment,
  onVerifyTdem,
  onRevokeTdem,
  onEditEmail,
  onEmailEmployee,
  onArchiveEmployee,
  onRestoreEmployee,
  onSetLicenseTracking,
  lifecycleBusy,
}) {
  if (loading) {
    return (
      <section className="employee-workspace">
        <button
          type="button"
          className="workspace-back"
          onClick={onBack}
        >
          ← Back to Dashboard
        </button>

        <div className="dashboard-loading">
          Loading employee compliance workspace...
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="employee-workspace">
        <button
          type="button"
          className="workspace-back"
          onClick={onBack}
        >
          ← Back to Dashboard
        </button>

        <div className="message error-message">
          <strong>
            Employee workspace could not be loaded.
          </strong>
          <p>{error}</p>
        </div>
      </section>
    );
  }

  if (!workspace) {
    return null;
  }

  const officer = workspace.officer;

  const licenseTracking =
    workspace.license_tracking || [];

  const isLicenseTracked = (licenseType) => {
    const item = licenseTracking.find(
      (license) =>
        license.license_type === licenseType
    );

    return item
      ? item.tracking_enabled
      : true;
  };

  const name = [
    officer.first_name,
    officer.middle_name,
    officer.last_name,
    officer.suffix,
  ]
    .filter(Boolean)
    .join(" ");

  const activeAssignments =
    workspace.assignments?.filter(
      (assignment) => assignment.active
    ) || [];

  const employeeArchived =
    officer.employment_status === "archived";

  return (
    <section className="employee-workspace">
      <div className="workspace-top-actions">
        <button
          type="button"
          className="workspace-back"
          onClick={onBack}
        >
          ← Back to Dashboard
        </button>

        <div
          className="workspace-email-actions"
          style={{
            display: "flex",
            gap: "8px",
            flexWrap: "wrap",
            justifyContent: "flex-end",
          }}
        >
          {!employeeArchived &&
            isLicenseTracked("PEACE_OFFICER") &&
            workspace.proficiency_advancement
              ?.peace_officer && (
            <button
              type="button"
              className="workspace-email-button"
              disabled={
                !workspace.resolved_email?.email
              }
              title={
                workspace.resolved_email?.email
                  ? "Open a Peace Officer compliance email."
                  : "Configure an employee email address first."
              }
              onClick={() =>
                onEmailEmployee("peace_officer")
              }
            >
              Email Peace Officer Update
            </button>
          )}

          {!employeeArchived &&
            isLicenseTracked("COUNTY_JAILER") &&
            workspace.proficiency_advancement
              ?.jailer && (
            <button
              type="button"
              className="workspace-email-button"
              disabled={
                !workspace.resolved_email?.email
              }
              title={
                workspace.resolved_email?.email
                  ? "Open a County Jailer compliance email."
                  : "Configure an employee email address first."
              }
              onClick={() =>
                onEmailEmployee("jailer")
              }
            >
              Email County Jailer Update
            </button>
          )}


          {!employeeArchived &&
            isLicenseTracked("TELECOMMUNICATOR") &&
            workspace.proficiency_advancement
              ?.telecommunicator && (
            <button
              type="button"
              className="workspace-email-button"
              disabled={
                !workspace.resolved_email?.email
              }
              title={
                workspace.resolved_email?.email
                  ? "Open a Telecommunicator compliance email."
                  : "Configure an employee email address first."
              }
              onClick={() =>
                onEmailEmployee(
                  "telecommunicator"
                )
              }
            >
              Email Telecommunicator Update
            </button>
          )}

          {!employeeArchived && [
            isLicenseTracked("PEACE_OFFICER") &&
              workspace.proficiency_advancement
                ?.peace_officer,
            isLicenseTracked("COUNTY_JAILER") &&
              workspace.proficiency_advancement
                ?.jailer,
            isLicenseTracked("TELECOMMUNICATOR") &&
              workspace.proficiency_advancement
                ?.telecommunicator,
          ].filter(Boolean).length > 1 && (
              <button
                type="button"
                className="workspace-email-button"
                disabled={
                  !workspace.resolved_email?.email
                }
                title={
                  workspace.resolved_email?.email
                    ? "Open a combined compliance email."
                    : "Configure an employee email address first."
                }
                onClick={() =>
                  onEmailEmployee("combined")
                }
              >
                Email Combined Update
              </button>
            )}
          {officer.employment_status === "archived" ? (
            <button
              type="button"
              className="workspace-lifecycle-button restore"
              disabled={lifecycleBusy}
              onClick={onRestoreEmployee}
            >
              {lifecycleBusy
                ? "Restoring..."
                : "Restore Employee"}
            </button>
          ) : (
            <button
              type="button"
              className="workspace-lifecycle-button archive"
              disabled={lifecycleBusy}
              onClick={onArchiveEmployee}
            >
              {lifecycleBusy
                ? "Archiving..."
                : "Archive Employee"}
            </button>
          )}
        </div>
      </div>

      <div className="workspace-hero">
        <div>
          <div className="dashboard-kicker">
            Employee Compliance & Training Detail
          </div>

          <div className="workspace-name-row">
            <h2>{name}</h2>

            {officer.employment_status === "archived" ? (
              <span className="employee-status archived">
                ARCHIVED
              </span>
            ) : (
              <WorkspaceStatus
                status={workspace.overall_status}
              />
            )}
          </div>

          {officer.employment_status === "archived" && (
            <div className="workspace-archive-banner">
              <strong>
                This employee is archived.
              </strong>

              <span>
                Archived{" "}
                {officer.archived_at
                  ? formatPlatformDate(
                      officer.archived_at
                    )
                  : ""}
                {officer.archived_reason
                  ? ` · ${officer.archived_reason}`
                  : ""}
              </span>
            </div>
          )}

          <div className="workspace-identity">
            <span>PID {officer.tcole_pid}</span>
            <span>•</span>
            <span>
              {formatEmployeeCertificates(
                officer,
                workspace.proficiency_advancement
              )}
            </span>

            {activeAssignments.map(
              (assignment) => (
                <span key={assignment.id}>
                  •{" "}
                  {formatAssignment(
                    assignment.assignment_type
                  )}
                </span>
              )
            )}
          </div>

          <div className="workspace-email">
            <span>
              Email:{" "}
              <strong>
                {workspace.resolved_email?.email ||
                  "Not configured"}
              </strong>

              {workspace.resolved_email?.source && (
                <>
                  {" "}
                  ({workspace.resolved_email.source
                    .replaceAll("_", " ")
                    .toLowerCase()})
                </>
              )}
            </span>

            {!employeeArchived && (
              <button
                type="button"
                className="workspace-email-edit"
                onClick={onEditEmail}
              >
                Edit Email
              </button>
            )}
          </div>
        </div>

        <div className="workspace-next-due">
          <span>Next Due</span>
          <strong>
            {formatDashboardDate(
              workspace.next_due_date
            )}
          </strong>
        </div>
      </div>

      <div className="workspace-summary-grid">
        <div className="workspace-summary-card">
          <span>Current Unit Hours</span>
          <strong>
            {workspace.training_summary
              ?.current_unit_hours ?? 0}
          </strong>
        </div>

        <div className="workspace-summary-card">
          <span>Minimum Hours</span>
          <strong>
            {workspace.training_summary
              ?.minimum_total_hours ?? "N/A"}
          </strong>
        </div>

        <div className="workspace-summary-card">
          <span>Hours Remaining</span>
          <strong>
            {workspace.training_summary
              ?.remaining_total_hours ?? "N/A"}
          </strong>
        </div>

        <div className="workspace-summary-card">
          <span>Training Records</span>
          <strong>
            {workspace.training_summary
              ?.training_record_count ?? 0}
          </strong>
        </div>
      </div>

      <section className="workspace-unit-banner">
        <div>
          <span>Current TCOLE Training Unit</span>
          <strong>
            Unit {workspace.training_unit.unit_number}
          </strong>
        </div>

        <div>
          {formatDashboardDate(
            workspace.training_unit.unit_start
          )}{" "}
          through{" "}
          {formatDashboardDate(
            workspace.training_unit.unit_end
          )}
        </div>
      </section>

      <div className="workspace-two-column">
        <RequirementList
          title="Overdue Requirements"
          items={workspace.overdue_requirements}
          emptyMessage="No overdue requirements."
        />

        <RequirementList
          title="Outstanding Requirements"
          items={workspace.outstanding_requirements}
          emptyMessage="No outstanding requirements."
        />
      </div>

      {workspace.agency_review_requirements?.length >
        0 && (
        <RequirementList
          title="Agency Review Required"
          items={workspace.agency_review_requirements}
          emptyMessage="No agency review items."
        />
      )}

      {licenseTracking.length > 1 && (
        <section className="workspace-panel">
          <div className="workspace-panel-heading">
            <div>
              <h3>License Compliance Tracking</h3>
              <p>
                Choose which TCOLE license requirements
                this agency intends to maintain for this
                employee. Turning tracking off does not
                remove or change the TCOLE license.
              </p>
            </div>
          </div>

          <div className="workspace-assignment-controls">
            {licenseTracking.map((license) => (
              <div
                className="workspace-assignment-control"
                key={license.license_type}
              >
                <div className="workspace-assignment-copy">
                  <strong>
                    {license.license_name}
                  </strong>

                  <span>
                    {license.tracking_enabled
                      ? "Compliance requirements are being tracked."
                      : "License remains on record. Compliance tracking is off."}
                  </span>

                  {!license.tracking_enabled &&
                    license.last_disabled_reason && (
                    <span>
                      Reason:{" "}
                      {license.last_disabled_reason}
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  role="switch"
                  aria-checked={
                    license.tracking_enabled
                  }
                  className={
                    "assignment-toggle" +
                    (license.tracking_enabled
                      ? " active"
                      : "")
                  }
                  disabled={
                    !onSetLicenseTracking
                  }
                  title={
                    license.tracking_enabled
                      ? `Stop tracking ${license.license_name} compliance`
                      : `Resume tracking ${license.license_name} compliance`
                  }
                  onClick={() =>
                    onSetLicenseTracking(
                      license
                    )
                  }
                >
                  <span className="assignment-toggle-knob" />
                  <span className="assignment-toggle-label">
                    {license.tracking_enabled
                      ? "On"
                      : "Off"}
                  </span>
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="workspace-panel">
        <div className="workspace-panel-heading">
          <div>
            <h3>Compliance Assignments</h3>
            <p>
              Agency-managed assignments that activate
              additional TCOLE compliance requirements.
            </p>
          </div>
        </div>

        {assignmentError && (
          <div className="message error-message">
            {assignmentError}
          </div>
        )}

        {assignmentSummary ? (
          <div className="workspace-assignment-controls">
            {assignmentSummary.assignment_types
              .filter((assignment) =>
                [
                  "POLICE_CHIEF",
                  "SUPERVISOR",
                  "PUBLIC_INFORMATION_OFFICER",
                ].includes(assignment.assignment_type)
              )
              .map((assignment) => {
                const chiefHolder =
                  assignmentSummary.chief_holder;

                const chiefHeldByOther =
                  assignment.assignment_type ===
                    "POLICE_CHIEF" &&
                  !assignment.active &&
                  chiefHolder &&
                  chiefHolder.officer_id !==
                    workspace.officer.id;

                return (
                  <div
                    className={
                      "workspace-assignment-control" +
                      (chiefHeldByOther
                        ? " unavailable"
                        : "")
                    }
                    key={assignment.assignment_type}
                  >
                    <div className="workspace-assignment-copy">
                      <strong>
                        {assignment.assignment_name}
                      </strong>

                      <span>
                        {assignment.active
                          ? `Effective ${formatDashboardDate(
                              assignment.effective_date
                            )}`
                          : chiefHeldByOther
                            ? `Currently assigned to ${chiefHolder.name}`
                            : "Not assigned"}
                      </span>
                    </div>

                    <button
                      type="button"
                      role="switch"
                      aria-checked={assignment.active}
                      className={
                        "assignment-toggle" +
                        (assignment.active
                          ? " active"
                          : "")
                      }
                      disabled={
                        assignmentBusy ||
                        chiefHeldByOther
                      }
                      title={
                        chiefHeldByOther
                          ? `Police Chief is currently assigned to ${chiefHolder.name}.`
                          : assignment.active
                            ? `End ${assignment.assignment_name} assignment`
                            : `Activate ${assignment.assignment_name} assignment`
                      }
                      onClick={() =>
                        assignment.active
                          ? onEndAssignment(assignment)
                          : onActivateAssignment(
                              assignment
                            )
                      }
                    >
                      <span className="assignment-toggle-knob" />
                      <span className="assignment-toggle-label">
                        {assignment.active
                          ? "On"
                          : "Off"}
                      </span>
                    </button>
                  </div>
                );
              })}
          </div>
        ) : (
          <div className="workspace-empty">
            Loading compliance assignments...
          </div>
        )}

        {assignmentSummary?.assignment_types.find(
          (assignment) =>
            assignment.assignment_type ===
              "PUBLIC_INFORMATION_OFFICER" &&
            assignment.active
        ) && (
          <div className="workspace-tdem-panel">
            <div className="credential-heading">
              <div>
                <h3>TDEM PIO Certification</h3>
                <p>
                  Agency verification of the separate TDEM
                  certification requirement.
                </p>
              </div>

              <span
                className={
                  credentialVerifications.some(
                    (item) =>
                      item.credential_type ===
                        "TDEM_PIO_CERTIFICATION" &&
                      item.active
                  )
                    ? "credential-status verified"
                    : "credential-status unverified"
                }
              >
                {credentialVerifications.some(
                  (item) =>
                    item.credential_type ===
                      "TDEM_PIO_CERTIFICATION" &&
                    item.active
                )
                  ? "Verified"
                  : "Not Verified"}
              </span>
            </div>

            {credentialError && (
              <div className="message error-message">
                {credentialError}
              </div>
            )}

            {(() => {
              const verification =
                credentialVerifications.find(
                  (item) =>
                    item.credential_type ===
                      "TDEM_PIO_CERTIFICATION" &&
                    item.active
                );

              if (verification) {
                return (
                  <div className="credential-details">
                    <div>
                      <span>Effective Date</span>
                      <strong>
                        {formatDashboardDate(
                          verification.effective_date
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>Verified By</span>
                      <strong>
                        {verification.verified_by ||
                          "Not recorded"}
                      </strong>
                    </div>

                    <div>
                      <span>Reference</span>
                      <strong>
                        {verification.reference ||
                          "Not recorded"}
                      </strong>
                    </div>

                    <button
                      type="button"
                      className="credential-button revoke"
                      disabled={credentialBusy}
                      onClick={onRevokeTdem}
                    >
                      {credentialBusy
                        ? "Working..."
                        : "Revoke Verification"}
                    </button>
                  </div>
                );
              }

              return (
                <div className="credential-unverified">
                  <p>
                    PTM has no active agency verification
                    of this officer's TDEM PIO
                    certification.
                  </p>

                  <button
                    type="button"
                    className="credential-button verify"
                    disabled={credentialBusy}
                    onClick={onVerifyTdem}
                  >
                    {credentialBusy
                      ? "Working..."
                      : "Verify Certification"}
                  </button>
                </div>
              );
            })()}
          </div>
        )}
      </section>

      <section className="workspace-panel">
        <div className="workspace-panel-heading">
          <h3>Assignment History</h3>
          <span>
            {workspace.assignments?.length || 0}
          </span>
        </div>

        {workspace.assignments?.length ? (
          <div className="workspace-assignment-list">
            {workspace.assignments.map(
              (assignment) => (
                <div
                  className="workspace-assignment"
                  key={assignment.id}
                >
                  <strong>
                    {formatAssignment(
                      assignment.assignment_type
                    )}
                  </strong>

                  <span>
                    {formatDashboardDate(
                      assignment.effective_date
                    )}
                    {" through "}
                    {assignment.end_date
                      ? formatDashboardDate(
                          assignment.end_date
                        )
                      : "Present"}
                  </span>
                </div>
              )
            )}
          </div>
        ) : (
          <div className="workspace-empty">
            No additional assignments.
          </div>
        )}
      </section>

      <section className="workspace-panel">
        <div className="workspace-panel-heading">
          <h3>Current Unit Training</h3>
          <span>
            {workspace.current_unit_training?.length ||
              0}
          </span>
        </div>

        {workspace.current_unit_training?.length ? (
          <div className="training-table-wrap">
            <table className="training-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Course</th>
                  <th>Course Number</th>
                  <th>Hours</th>
                </tr>
              </thead>

              <tbody>
                {workspace.current_unit_training.map(
                  (record) => (
                    <tr key={record.id}>
                      <td>
                        {formatDashboardDate(
                          record.course_date
                        )}
                      </td>
                      <td>{record.course_title}</td>
                      <td>{record.course_number}</td>
                      <td>
                        {record.credited_hours ?? 0}
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="workspace-empty">
            No training records found in the current
            unit.
          </div>
        )}
      </section>

      <QualificationInformationPanel
        facts={qualificationFacts}
        advancement={workspace.proficiency_advancement}
        busy={qualificationBusy}
        error={qualificationError}
        onSave={onSaveQualificationFacts}
      />

      {workspace.proficiency_advancement?.peace_officer && (
        <ProficiencyAdvancementPanel
          advancement={
            workspace.proficiency_advancement.peace_officer
          }
          trackLabel="Peace Officer"
        />
      )}

      {workspace.proficiency_advancement?.jailer && (
        <ProficiencyAdvancementPanel
          advancement={
            workspace.proficiency_advancement.jailer
          }
          trackLabel="County Jailer"
        />
      )}


      {workspace.proficiency_advancement
        ?.telecommunicator && (
        <ProficiencyAdvancementPanel
          advancement={
            workspace.proficiency_advancement
              .telecommunicator
          }
          trackLabel="Telecommunicator"
        />
      )}

    </section>
  );
}

function formatCommunicationTrack(track) {
  const labels = {
    peace_officer: "Peace Officer",
    jailer: "County Jailer",
    telecommunicator: "Telecommunicator",
    combined: "Combined",
  };

  return labels[track] || "None";
}


function formatApplicableTracks(tracks) {
  if (!tracks?.length) {
    return "None";
  }

  return tracks
    .map(formatCommunicationTrack)
    .join(" + ");
}


function ComplianceCommunicationsWorkspace({
  preflight,
  loading,
  error,
  selectedIds,
  setSelectedIds,
  onBack,
}) {
  const [filter, setFilter] = useState("ALL");
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] =
    useState(false);
  const [previewError, setPreviewError] =
    useState("");
  const [batchReviewOpen, setBatchReviewOpen] =
    useState(false);
  const [
    batchOpenedIds,
    setBatchOpenedIds,
  ] = useState([]);
  const [
    batchOpening,
    setBatchOpening,
  ] = useState(false);
  const [
    batchOpenError,
    setBatchOpenError,
  ] = useState("");

  if (loading) {
    return (
      <section className="communications-workspace">
        <button
          type="button"
          className="workspace-back"
          onClick={onBack}
        >
          ← Back to Dashboard
        </button>

        <div className="dashboard-loading">
          Loading compliance communications...
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="communications-workspace">
        <button
          type="button"
          className="workspace-back"
          onClick={onBack}
        >
          ← Back to Dashboard
        </button>

        <div className="message error-message">
          <strong>
            Compliance communications could not be loaded.
          </strong>
          <p>{error}</p>
        </div>
      </section>
    );
  }

  if (!preflight) {
    return null;
  }

  const recipients = preflight.recipients || [];

  const filteredRecipients = recipients.filter(
    (recipient) =>
      filter === "ALL" ||
      recipient.overall_status === filter
  );

  const selectedCount = selectedIds.length;

  const toggleRecipient = (recipient) => {
    if (recipient.preflight_status !== "READY") {
      return;
    }

    setSelectedIds((current) =>
      current.includes(recipient.officer_id)
        ? current.filter(
            (id) => id !== recipient.officer_id
          )
        : [...current, recipient.officer_id]
    );
  };

  const selectAllEligible = () => {
    setSelectedIds(
      recipients
        .filter(
          (recipient) =>
            recipient.preflight_status === "READY"
        )
        .map((recipient) => recipient.officer_id)
    );
  };

  const clearSelection = () => {
    setSelectedIds([]);
  };

  const selectedRecipients = (
    preflight?.recipients || []
  ).filter(
    (recipient) =>
      selectedIds.includes(
        recipient.officer_id
      ) &&
      recipient.preflight_status === "READY"
  );

  const batchTrackCounts =
    selectedRecipients.reduce(
      (counts, recipient) => {
        const track =
          recipient.communication_track ||
          "unknown";

        counts[track] =
          (counts[track] || 0) + 1;

        return counts;
      },
      {}
    );

  const removeFromBatch = (officerId) => {
    setSelectedIds(
      selectedIds.filter(
        (id) => id !== officerId
      )
    );
  };

  const openBatchReview = () => {
    if (selectedRecipients.length === 0) {
      return;
    }

    setBatchOpenedIds([]);
    setBatchOpenError("");
    setBatchReviewOpen(true);
  };

  const closeBatchReview = () => {
    setBatchReviewOpen(false);
  };

  const openRecipientInEmailApp = async (
    recipient
  ) => {
    if (
      !recipient ||
      recipient.preflight_status !== "READY" ||
      !recipient.communication_track
    ) {
      return false;
    }

    setBatchOpening(true);
    setBatchOpenError("");

    try {
      const response = await fetch(
        `/api/agencies/${preflight.agency.id}` +
          `/officers/${recipient.officer_id}` +
          `/compliance-email` +
          `?track=${encodeURIComponent(
            recipient.communication_track
          )}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to prepare the compliance email."
        );
      }

      if (!data.can_email || !data.recipient) {
        throw new Error(
          "No employee email address is configured."
        );
      }

      const mailto =
        `mailto:${encodeURIComponent(data.recipient)}` +
        `?subject=${encodeURIComponent(data.subject)}` +
        `&body=${encodeURIComponent(data.body)}`;

      window.location.href = mailto;

      setBatchOpenedIds((current) =>
        current.includes(recipient.officer_id)
          ? current
          : [...current, recipient.officer_id]
      );

      return true;
    } catch (err) {
      setBatchOpenError(err.message);
      return false;
    } finally {
      setBatchOpening(false);
    }
  };


  const unopenedRecipients =
    selectedRecipients.filter(
      (recipient) =>
        !batchOpenedIds.includes(
          recipient.officer_id
        )
    );


  const nextRecipient =
    unopenedRecipients[0] || null;


  const openNextBatchEmail = async () => {
    if (!nextRecipient || batchOpening) {
      return;
    }

    await openRecipientInEmailApp(
      nextRecipient
    );
  };


  const openPreview = async (recipient) => {
    if (
      recipient.preflight_status !== "READY" ||
      !recipient.communication_track
    ) {
      return;
    }

    setPreviewLoading(true);
    setPreviewError("");
    setPreview(null);

    try {
      const response = await fetch(
        `/api/agencies/${preflight.agency.id}` +
          `/officers/${recipient.officer_id}` +
          `/compliance-email` +
          `?track=${encodeURIComponent(
            recipient.communication_track
          )}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to prepare compliance email preview."
        );
      }

      setPreview({
        ...data,
        overall_status: recipient.overall_status,
        communication_track:
          recipient.communication_track,
        applicable_tracks:
          recipient.applicable_tracks,
      });
    } catch (err) {
      setPreviewError(err.message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const closePreview = () => {
    setPreview(null);
    setPreviewError("");
    setPreviewLoading(false);
  };

  return (
    <section className="communications-workspace">
      <button
        type="button"
        className="workspace-back"
        onClick={onBack}
      >
        ← Back to Dashboard
      </button>

      <div className="communications-heading">
        <div>
          <div className="dashboard-kicker">
            Compliance Communications
          </div>

          <h2>
            {preflight.agency?.name ||
              "Agency Compliance Communications"}
          </h2>

          <p>
            Review employees who are ready to receive
            individualized TCOLE compliance updates.
          </p>
        </div>

        <div className="communications-as-of">
          <span>As of</span>
          <strong>
            {formatDashboardDate(
              preflight.evaluation_date
            )}
          </strong>
        </div>
      </div>

      <div className="communications-summary-grid">
        <div className="communications-summary-card">
          <span>Employees</span>
          <strong>
            {preflight.summary.total_employees}
          </strong>
        </div>

        <div className="communications-summary-card ready">
          <span>Ready</span>
          <strong>
            {preflight.summary.eligible_recipients}
          </strong>
        </div>

        <div className="communications-summary-card selected">
          <span>Selected</span>
          <strong>{selectedCount}</strong>
        </div>

        <div className="communications-summary-card action">
          <span>Action Required</span>
          <strong>
            {preflight.summary.action_required}
          </strong>
        </div>
      </div>

      <div className="communications-toolbar">
        <div
          className="communications-filter-tabs"
          role="group"
          aria-label="Filter compliance communications"
        >
          {[
            ["ALL", "All"],
            ["DUE", "Training Due"],
            ["NONCOMPLIANT", "Noncompliant"],
            ["COMPLIANT", "Compliant"],
            ["NOT_EVALUATED", "Not Evaluated"],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={
                "communications-filter-tab" +
                (filter === value ? " active" : "")
              }
              onClick={() => setFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="communications-selection-actions">
          <button
            type="button"
            className="settings-secondary-button"
            onClick={clearSelection}
          >
            Clear Selection
          </button>

          <button
            type="button"
            className="settings-primary-button"
            onClick={selectAllEligible}
          >
            Select All Eligible
          </button>
        </div>
      </div>

      <div className="communications-result-count">
        Showing{" "}
        <strong>{filteredRecipients.length}</strong>{" "}
        of <strong>{recipients.length}</strong>{" "}
        employees
      </div>

      <div className="communications-table-wrap">
        <table className="communications-table">
          <thead>
            <tr>
              <th className="communications-select-column">
                Select
              </th>
              <th>Employee</th>
              <th>Status</th>
              <th>License Track(s)</th>
              <th>Requirements</th>
              <th>Next Due</th>
              <th>Email</th>
              <th>Readiness</th>
              <th>Preview</th>
            </tr>
          </thead>

          <tbody>
            {filteredRecipients.map((recipient) => {
              const ready =
                recipient.preflight_status === "READY";

              const selected = selectedIds.includes(
                recipient.officer_id
              );

              const requirementCount =
                (recipient.overdue_count || 0) +
                (recipient.outstanding_count || 0) +
                (recipient.pending_review_count || 0);

              return (
                <tr
                  key={recipient.officer_id}
                  className={
                    ready
                      ? "communications-row-ready"
                      : "communications-row-action"
                  }
                >
                  <td className="communications-select-column">
                    <input
                      type="checkbox"
                      checked={selected}
                      disabled={!ready}
                      aria-label={
                        `Select ${recipient.employee_name}`
                      }
                      onChange={() =>
                        toggleRecipient(recipient)
                      }
                    />
                  </td>

                  <td>
                    <div className="communications-employee">
                      <strong>
                        {recipient.employee_name}
                      </strong>
                      <span>
                        PID {recipient.tcole_pid}
                      </span>
                    </div>
                  </td>

                  <td>
                    <WorkspaceStatus
                      status={recipient.overall_status}
                    />
                  </td>

                  <td>
                    {formatApplicableTracks(
                      recipient.applicable_tracks
                    )}
                  </td>

                  <td>
                    <strong>{requirementCount}</strong>
                  </td>

                  <td>
                    {formatDashboardDate(
                      recipient.next_due_date
                    )}
                  </td>

                  <td
                    className="communications-email-cell"
                    title={
                      recipient.email ||
                      "Not configured"
                    }
                  >
                    <span className="communications-email-text">
                      {recipient.email ||
                        "Not configured"}
                    </span>
                  </td>

                  <td>
                    {ready ? (
                      <span className="communications-ready-badge">
                        Ready
                      </span>
                    ) : (
                      <div className="communications-issues">
                        <span className="communications-action-badge">
                          Action Required
                        </span>

                        {recipient.preflight_issues?.map(
                          (issue) => (
                            <span
                              key={issue.code}
                              className="communications-issue"
                            >
                              {issue.message}
                            </span>
                          )
                        )}
                      </div>
                    )}
                  </td>

                  <td>
                    <button
                      type="button"
                      className="communications-preview-button"
                      disabled={!ready}
                      onClick={() =>
                        openPreview(recipient)
                      }
                    >
                      Preview
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredRecipients.length === 0 && (
          <div className="dashboard-empty">
            No employees match the current communication
            filter.
          </div>
        )}
      </div>

      <div className="communications-footer">
        <div>
          <strong>{selectedCount}</strong>{" "}
          employee{selectedCount === 1 ? "" : "s"} selected.
        </div>

        <button
          type="button"
          className="settings-primary-button"
          disabled={selectedRecipients.length === 0}
          onClick={openBatchReview}
        >
          Prepare Batch
        </button>
      </div>

      {batchReviewOpen && (
        <div
          className="communications-preview-overlay"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget
            ) {
              closeBatchReview();
            }
          }}
        >
          <section
            className="communications-batch-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Compliance communication batch review"
          >
            <div className="communications-preview-header">
              <div>
                <div className="dashboard-kicker">
                  Final Communication Review
                </div>

                <h3>
                  {selectedRecipients.length} Compliance{" "}
                  {selectedRecipients.length === 1
                    ? "Update"
                    : "Updates"}{" "}
                  Ready
                </h3>

                <p className="communications-batch-subtitle">
                  Review the final recipient batch before
                  continuing to the sending stage.
                </p>
              </div>

              <button
                type="button"
                className="communications-preview-close"
                onClick={closeBatchReview}
                aria-label="Close batch review"
              >
                ×
              </button>
            </div>

            <div className="communications-batch-summary">
              <div>
                <span>Total Ready</span>
                <strong>
                  {selectedRecipients.length}
                </strong>
              </div>

              <div>
                <span>Peace Officer</span>
                <strong>
                  {batchTrackCounts.peace_officer || 0}
                </strong>
              </div>

              <div>
                <span>County Jailer</span>
                <strong>
                  {batchTrackCounts.jailer || 0}
                </strong>
              </div>

              <div>
                <span>Telecommunicator</span>
                <strong>
                  {batchTrackCounts.telecommunicator || 0}
                </strong>
              </div>

              <div>
                <span>Combined</span>
                <strong>
                  {batchTrackCounts.combined || 0}
                </strong>
              </div>
            </div>

            <div className="communications-batch-confirmation">
              <strong>
                All {selectedRecipients.length} selected{" "}
                {selectedRecipients.length === 1
                  ? "employee has"
                  : "employees have"}{" "}
                passed communication preflight.
              </strong>

              <span>
                Each recipient has a valid email address
                and a supported individualized compliance
                communication type.
              </span>
            </div>

            <div className="communications-batch-table-wrap">
              <table className="communications-batch-table">
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Communication</th>
                    <th>Requirements</th>
                    <th>Next Due</th>
                    <th>Email</th>
                    <th>Email App</th>
                    <th>Remove</th>
                  </tr>
                </thead>

                <tbody>
                  {selectedRecipients.map(
                    (recipient) => (
                      <tr key={recipient.officer_id}>
                        <td>
                          <strong>
                            {recipient.employee_name}
                          </strong>
                          <span className="communications-batch-pid">
                            PID {recipient.tcole_pid}
                          </span>
                        </td>

                        <td>
                          {formatCommunicationTrack(
                            recipient.communication_track
                          )}
                        </td>

                        <td>
                          {recipient.requirement_count}
                        </td>

                        <td>
                          {recipient.next_due_date
                            ? formatDashboardDate(
                                recipient.next_due_date
                              )
                            : "None"}
                        </td>

                        <td
                          title={recipient.email}
                          className="communications-email-cell"
                        >
                          <span className="communications-email-text">
                            {recipient.email}
                          </span>
                        </td>

                        <td>
                          {batchOpenedIds.includes(
                            recipient.officer_id
                          ) ? (
                            <span className="communications-opened-badge">
                              Opened
                            </span>
                          ) : (
                            <button
                              type="button"
                              className="communications-open-email-button"
                              disabled={batchOpening}
                              onClick={() =>
                                openRecipientInEmailApp(
                                  recipient
                                )
                              }
                            >
                              Open
                            </button>
                          )}
                        </td>

                        <td>
                          <button
                            type="button"
                            className="communications-remove-button"
                            onClick={() =>
                              removeFromBatch(
                                recipient.officer_id
                              )
                            }
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>

            {selectedRecipients.length === 0 && (
              <div className="communications-batch-empty">
                No employees remain in this batch.
                Return to the Communications workspace
                to select recipients.
              </div>
            )}

            <div className="communications-batch-footer">
              <div>
                <strong>
                  {selectedRecipients.length}
                </strong>{" "}
                final{" "}
                {selectedRecipients.length === 1
                  ? "recipient"
                  : "recipients"}
              </div>

              <div className="communications-batch-actions">
                <button
                  type="button"
                  className="communications-secondary-button"
                  onClick={closeBatchReview}
                >
                  Back to Selection
                </button>

                <button
                  type="button"
                  className="settings-primary-button"
                  disabled={
                    !nextRecipient ||
                    batchOpening
                  }
                  onClick={openNextBatchEmail}
                >
                  {batchOpening
                    ? "Opening Email..."
                    : nextRecipient
                      ? `Open Next Email (${
                          batchOpenedIds.length + 1
                        } of ${
                          selectedRecipients.length
                        })`
                      : "All Emails Opened"}
                </button>
              </div>
            </div>

            <div className="communications-send-disabled-note">
              PTM opens each individualized message in your
              computer's default email application. Sending
              remains under your control in Outlook or your
              configured mail application.
            </div>

            {batchOpenError && (
              <div className="communications-batch-open-error">
                <strong>
                  Email could not be opened.
                </strong>
                <span>{batchOpenError}</span>
              </div>
            )}

            {selectedRecipients.length > 0 &&
              unopenedRecipients.length === 0 && (
              <div className="communications-batch-complete">
                <strong>
                  All {selectedRecipients.length} compliance
                  emails have been opened in the default email
                  application.
                </strong>
                <span>
                  PTM does not mark these messages as sent.
                  Your email application's Sent Items remains
                  the record of transmission.
                </span>
              </div>
            )}
          </section>
        </div>
      )}

      {(previewLoading ||
        previewError ||
        preview) && (
        <div
          className="communications-preview-overlay"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget
            ) {
              closePreview();
            }
          }}
        >
          <section
            className="communications-preview-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Compliance email preview"
          >
            <div className="communications-preview-header">
              <div>
                <div className="dashboard-kicker">
                  Compliance Email Preview
                </div>

                <h3>
                  {preview?.employee_name ||
                    "Preparing Preview"}
                </h3>
              </div>

              <button
                type="button"
                className="communications-preview-close"
                onClick={closePreview}
                aria-label="Close email preview"
              >
                ×
              </button>
            </div>

            {previewLoading && (
              <div className="dashboard-loading">
                Preparing individualized compliance
                update...
              </div>
            )}

            {previewError && (
              <div className="message error-message">
                <strong>
                  Email preview could not be prepared.
                </strong>
                <p>{previewError}</p>
              </div>
            )}

            {preview && !previewLoading && (
              <>
                <div className="communications-preview-meta">
                  <div>
                    <span>To</span>
                    <strong>
                      {preview.recipient ||
                        "No email address"}
                    </strong>
                  </div>

                  <div>
                    <span>Subject</span>
                    <strong>
                      {preview.subject}
                    </strong>
                  </div>

                  <div>
                    <span>Communication Type</span>
                    <strong>
                      {formatCommunicationTrack(
                        preview.communication_track
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>Status</span>
                    <strong>
                      {String(
                        preview.overall_status ||
                          "UNKNOWN"
                      )
                        .replaceAll("_", " ")
                        .toLowerCase()
                        .replace(
                          /\b\w/g,
                          (character) =>
                            character.toUpperCase()
                        )}
                    </strong>
                  </div>
                </div>

                <div className="communications-preview-body">
                  <pre>{preview.body}</pre>
                </div>

                <div className="communications-preview-footer">
                  <span>
                    This is the exact message PTM will use
                    for this employee.
                  </span>

                  <button
                    type="button"
                    className="settings-primary-button"
                    onClick={closePreview}
                  >
                    Close Preview
                  </button>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </section>
  );
}


function buildEmailConventionExample(
  pattern,
  domain,
) {
  if (!pattern || !domain) {
    return "Configure both fields to preview an address.";
  }

  const cleanDomain = domain
    .trim()
    .replace(/^@/, "")
    .toLowerCase();

  let localPart = "";

  if (pattern === "FIRST_INITIAL_LAST") {
    localPart = "jsmith";
  } else if (pattern === "FIRST_DOT_LAST") {
    localPart = "jane.smith";
  } else if (pattern === "FIRST_LAST") {
    localPart = "janesmith";
  } else if (pattern === "LAST_FIRST_INITIAL") {
    localPart = "smithj";
  } else {
    return "Select a supported email format.";
  }

  return `Jane Smith → ${localPart}@${cleanDomain}`;
}

function OperationalApp({
  currentUser,
  onLogout,
}) {
  const [agency, setAgency] = useState(null);
  const [selectedOfficerId, setSelectedOfficerId] = useState("");
  const [emailSettingsOpen, setEmailSettingsOpen] = useState(false);
  const [emailDomain, setEmailDomain] = useState("");
  const [emailPattern, setEmailPattern] = useState("");
  const [emailSettingsBusy, setEmailSettingsBusy] = useState(false);
  const [emailSettingsError, setEmailSettingsError] = useState("");

  const [accountOpen, setAccountOpen] = useState(false);

  const [
    onboardingComplete,
    setOnboardingComplete,
  ] = useState(
    Boolean(
      currentUser?.onboarding_completed_at
    )
  );

  const [
    gettingStartedOpen,
    setGettingStartedOpen,
  ] = useState(
    currentUser?.role === "AGENCY_ADMIN" &&
      !currentUser?.onboarding_completed_at
  );

  const [
    gettingStartedBusy,
    setGettingStartedBusy,
  ] = useState(false);

  const [
    gettingStartedError,
    setGettingStartedError,
  ] = useState("");

  const [
    dismissGettingStarted,
    setDismissGettingStarted,
  ] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordNotice, setPasswordNotice] = useState("");

  const [dashboard, setDashboard] = useState(null);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardFilter, setDashboardFilter] = useState("ALL");
  const [certificateFilter, setCertificateFilter] = useState("ALL");
  const [dashboardSearch, setDashboardSearch] = useState("");
  const [employeeWorkspace, setEmployeeWorkspace] = useState(null);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [workspaceError, setWorkspaceError] = useState("");
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [archivedEmployeesOpen, setArchivedEmployeesOpen] =
    useState(false);
  const [archivedEmployees, setArchivedEmployees] =
    useState([]);
  const [archivedEmployeesLoading, setArchivedEmployeesLoading] =
    useState(false);
  const [archivedEmployeesError, setArchivedEmployeesError] =
    useState("");
  const [archivedEmployeeSearch, setArchivedEmployeeSearch] =
    useState("");
  const [lifecycleBusy, setLifecycleBusy] =
    useState(false);
  const [
    communicationsOpen,
    setCommunicationsOpen,
  ] = useState(false);
  const [
    communicationsPreflight,
    setCommunicationsPreflight,
  ] = useState(null);
  const [
    communicationsLoading,
    setCommunicationsLoading,
  ] = useState(false);
  const [
    communicationsError,
    setCommunicationsError,
  ] = useState("");
  const [
    communicationsSelectedIds,
    setCommunicationsSelectedIds,
  ] = useState([]);
  const [assignmentSummary, setAssignmentSummary] = useState(null);
  const [credentialVerifications, setCredentialVerifications] = useState([]);
  const [qualificationFacts, setQualificationFacts] = useState(null);

  const [awardsFile, setAwardsFile] = useState(null);
  const [coursesFile, setCoursesFile] = useState(null);
  const [cycleFile, setCycleFile] = useState(null);
  const [licenseeSearchFile, setLicenseeSearchFile] = useState(null);

  const [loadingAgency, setLoadingAgency] = useState(true);
  const [assignmentBusy, setAssignmentBusy] = useState(false);
  const [credentialBusy, setCredentialBusy] = useState(false);
  const [qualificationBusy, setQualificationBusy] = useState(false);
  const [importing, setImporting] = useState(false);

  const [error, setError] = useState("");
  const [assignmentError, setAssignmentError] = useState("");
  const [credentialError, setCredentialError] = useState("");
  const [qualificationError, setQualificationError] = useState("");
  const [result, setResult] = useState(null);

  async function loadDashboard(agencyId) {
    setLoadingDashboard(true);
    setDashboardError("");

    try {
      const response = await fetch(
        `/api/agencies/${agencyId}/compliance/dashboard`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Unable to load compliance dashboard."
        );
      }

      setDashboard(data);
    } catch (err) {
      setDashboardError(err.message);
    } finally {
      setLoadingDashboard(false);
    }
  }

  async function openComplianceCommunications() {
    if (!agency?.id) {
      return;
    }

    setCommunicationsOpen(true);
    setCommunicationsLoading(true);
    setCommunicationsError("");
    setCommunicationsPreflight(null);
    setCommunicationsSelectedIds([]);
    setEmailSettingsOpen(false);

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });

    try {
      const evaluationDate =
        dashboard?.evaluation_date;

      const query = evaluationDate
        ? `?evaluation_date=${encodeURIComponent(
            evaluationDate
          )}`
        : "";

      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/compliance/communications/preflight` +
          query
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to load compliance communications."
        );
      }

      setCommunicationsPreflight(data);

      setCommunicationsSelectedIds(
        (data.recipients || [])
          .filter(
            (recipient) =>
              recipient.selected_by_default
          )
          .map(
            (recipient) =>
              recipient.officer_id
          )
      );
    } catch (err) {
      setCommunicationsError(err.message);
    } finally {
      setCommunicationsLoading(false);
    }
  }


  function closeComplianceCommunications() {
    setCommunicationsOpen(false);
    setCommunicationsPreflight(null);
    setCommunicationsError("");
    setCommunicationsSelectedIds([]);

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }


  async function openEmployeeWorkspace(employee) {
    if (!agency?.id || !employee?.id) {
      return;
    }

    setSelectedOfficerId(employee.id);
    setWorkspaceOpen(true);
    setLoadingWorkspace(true);
    setWorkspaceError("");
    setEmployeeWorkspace(null);

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
        `/officers/${employee.id}/workspace`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to load employee workspace."
        );
      }

      setEmployeeWorkspace(data);
    } catch (err) {
      setWorkspaceError(err.message);
    } finally {
      setLoadingWorkspace(false);
    }
  }

  async function loadArchivedEmployees() {
    if (!agency?.id) {
      return;
    }

    setArchivedEmployeesLoading(true);
    setArchivedEmployeesError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}/officers?include_archived=true`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to load archived employees."
        );
      }

      setArchivedEmployees(
        data.filter(
          (employee) =>
            employee.employment_status === "archived"
        )
      );
    } catch (err) {
      setArchivedEmployeesError(err.message);
    } finally {
      setArchivedEmployeesLoading(false);
    }
  }


  async function openArchivedEmployees() {
    setArchivedEmployeesOpen(true);
    setArchivedEmployeeSearch("");

    await loadArchivedEmployees();

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }


  function closeArchivedEmployees() {
    setArchivedEmployeesOpen(false);
    setArchivedEmployees([]);
    setArchivedEmployeesError("");
    setArchivedEmployeeSearch("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }


  async function handleArchiveEmployee() {
    if (!agency?.id || !selectedOfficerId) {
      return;
    }

    const confirmed = window.confirm(
      "Archive this employee? Their historical training, awards, certifications, and agency-managed information will be retained."
    );

    if (!confirmed) {
      return;
    }

    const reason = window.prompt(
      "Optional archive reason:",
      ""
    );

    if (reason === null) {
      return;
    }

    setLifecycleBusy(true);
    setWorkspaceError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}/archive`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            reason,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to archive employee."
        );
      }

      await Promise.all([
        loadDashboard(agency.id),
        openEmployeeWorkspace({
          id: selectedOfficerId,
        }),
        loadArchivedEmployees(),
      ]);
    } catch (err) {
      setWorkspaceError(err.message);
    } finally {
      setLifecycleBusy(false);
    }
  }


  async function handleRestoreEmployee() {
    if (!agency?.id || !selectedOfficerId) {
      return;
    }

    const confirmed = window.confirm(
      "Restore this employee to active status?"
    );

    if (!confirmed) {
      return;
    }

    setLifecycleBusy(true);
    setWorkspaceError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}/restore`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to restore employee."
        );
      }

      await Promise.all([
        loadDashboard(agency.id),
        openEmployeeWorkspace({
          id: selectedOfficerId,
        }),
        loadArchivedEmployees(),
      ]);
    } catch (err) {
      setWorkspaceError(err.message);
    } finally {
      setLifecycleBusy(false);
    }
  }


  function closeEmployeeWorkspace() {
    setWorkspaceOpen(false);
    setEmployeeWorkspace(null);
    setWorkspaceError("");
    setSelectedOfficerId("");
    setAssignmentSummary(null);
    setCredentialVerifications([]);
    setQualificationFacts(null);
    setQualificationError("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  useEffect(() => {
    async function loadAgency() {
      try {
        const response = await fetch("/api/agencies");

        if (!response.ok) {
          throw new Error("Unable to load the agency.");
        }

        const agencies = await response.json();

        if (!agencies.length) {
          throw new Error("No agency has been configured.");
        }

        const selectedAgency = agencies[0];
        setAgency(selectedAgency);
        setEmailDomain(
          selectedAgency.email_domain || ""
        );
        setEmailPattern(
          selectedAgency.email_pattern || ""
        );

        await Promise.all([
          loadDashboard(selectedAgency.id),
        ]);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoadingAgency(false);
      }
    }

    loadAgency();
  }, []);

  useEffect(() => {
    async function loadAssignments() {
      if (!agency || !selectedOfficerId) {
        setAssignmentSummary(null);
        setCredentialVerifications([]);
        return;
      }

      setAssignmentError("");

      try {
        const response = await fetch(
          `/api/agencies/${agency.id}` +
            `/officers/${selectedOfficerId}` +
            `/assignment-summary`
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error || "Unable to load assignments."
          );
        }

        setAssignmentSummary(data);

        const credentialResponse = await fetch(
          `/api/agencies/${agency.id}` +
            `/officers/${selectedOfficerId}` +
            `/credential-verifications`
        );

        const credentialData = await credentialResponse.json();

        if (!credentialResponse.ok) {
          throw new Error(
            credentialData.error ||
              "Unable to load credential verifications."
          );
        }

        setCredentialVerifications(credentialData);
      } catch (err) {
        setAssignmentError(err.message);
      }
    }

    loadAssignments();
  }, [agency, selectedOfficerId]);

  useEffect(() => {
    async function loadQualificationFacts() {
      if (!agency || !selectedOfficerId) {
        setQualificationFacts(null);
        setQualificationError("");
        return;
      }

      setQualificationError("");

      try {
        const response = await fetch(
          `/api/agencies/${agency.id}` +
            `/officers/${selectedOfficerId}` +
            `/qualification-facts`
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error ||
              "Unable to load qualification information."
          );
        }

        setQualificationFacts(data);
      } catch (err) {
        setQualificationError(err.message);
      }
    }

    loadQualificationFacts();
  }, [agency, selectedOfficerId]);

  const ready =
    Boolean(agency) &&
    Boolean(awardsFile) &&
    Boolean(coursesFile) &&
    Boolean(cycleFile) &&
    Boolean(licenseeSearchFile) &&
    !importing;

  async function handleSaveEmailSettings(event) {
    event.preventDefault();

    if (!agency?.id) {
      return;
    }

    setEmailSettingsBusy(true);
    setEmailSettingsError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}/email-configuration`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email_domain: emailDomain,
            email_pattern: emailPattern,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to save email configuration."
        );
      }

      setAgency((current) => ({
        ...current,
        email_domain: data.email_domain,
        email_pattern: data.email_pattern,
      }));

      setEmailDomain(data.email_domain || "");
      setEmailPattern(data.email_pattern || "");
      setEmailSettingsOpen(false);

      if (workspaceOpen) {
        await refreshEmployeeWorkspace();
      }
    } catch (err) {
      setEmailSettingsError(err.message);
    } finally {
      setEmailSettingsBusy(false);
    }
  }

  async function handleEditEmployeeEmail() {
    if (
      !agency?.id ||
      !selectedOfficerId ||
      !employeeWorkspace
    ) {
      return;
    }

    const currentOverride =
      employeeWorkspace.officer.email_override || "";

    const value = window.prompt(
      "Employee email override. Leave blank to use the agency email convention:",
      currentOverride
    );

    if (value === null) {
      return;
    }

    setWorkspaceError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}/email`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email_override: value,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to update employee email."
        );
      }

      await refreshEmployeeWorkspace();
    } catch (err) {
      setWorkspaceError(err.message);
    }
  }

  async function handleSaveQualificationFacts(
    payload
  ) {
    if (!agency?.id || !selectedOfficerId) {
      return;
    }

    setQualificationBusy(true);
    setQualificationError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}` +
          `/qualification-facts`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to save qualification information."
        );
      }

      setQualificationFacts(data);

      await refreshEmployeeWorkspace();
    } catch (err) {
      setQualificationError(err.message);
    } finally {
      setQualificationBusy(false);
    }
  }

  async function handleEmailEmployee(
    track = "peace_officer"
  ) {
    if (
      !agency?.id ||
      !selectedOfficerId ||
      !employeeWorkspace
    ) {
      return;
    }

    setWorkspaceError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}` +
          `/compliance-email` +
          `?track=${encodeURIComponent(track)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to prepare compliance email."
        );
      }

      if (!data.can_email || !data.recipient) {
        throw new Error(
          "No employee email address is configured."
        );
      }

      const mailto =
        `mailto:${encodeURIComponent(data.recipient)}` +
        `?subject=${encodeURIComponent(data.subject)}` +
        `&body=${encodeURIComponent(data.body)}`;

      window.location.href = mailto;
    } catch (err) {
      setWorkspaceError(err.message);
    }
  }

  async function handleImport(event) {
    event.preventDefault();

    if (!ready) {
      return;
    }

    setImporting(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("awards_file", awardsFile);
    formData.append("courses_file", coursesFile);
    formData.append("cycle_file", cycleFile);
    formData.append(
      "licensee_search_file",
      licenseeSearchFile
    );

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}/imports/tcole`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "The TCOLE import could not be completed."
        );
      }

      setResult(data);

      await Promise.all([
        loadDashboard(agency.id),
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  }

  async function refreshEmployeeWorkspace() {
    if (
      !agency ||
      !selectedOfficerId ||
      !workspaceOpen
    ) {
      return;
    }

    const response = await fetch(
      `/api/agencies/${agency.id}` +
        `/officers/${selectedOfficerId}/workspace`
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error ||
          "Unable to refresh employee workspace."
      );
    }

    setEmployeeWorkspace(data);
  }

  async function handleSetLicenseTracking(
    license
  ) {
    if (
      !agency?.id ||
      !selectedOfficerId ||
      !license
    ) {
      return;
    }

    const turningOff =
      license.tracking_enabled;

    let reason = null;

    if (turningOff) {
      const confirmed = window.confirm(
        `Stop tracking ${license.license_name} compliance?\n\n` +
        "The license and all historical records will remain visible. " +
        "Its requirements will no longer affect this employee's PTM " +
        "compliance status, dashboard, reports, or normal compliance " +
        "notifications. This does not change the employee's TCOLE " +
        "license status."
      );

      if (!confirmed) {
        return;
      }

      reason = window.prompt(
        "Reason for stopping compliance tracking (optional):",
        ""
      );

      if (reason === null) {
        return;
      }
    } else {
      const confirmed = window.confirm(
        `Resume tracking ${license.license_name} compliance?`
      );

      if (!confirmed) {
        return;
      }
    }

    setWorkspaceError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}` +
          `/license-tracking/${license.license_type}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            tracking_enabled: turningOff
              ? false
              : true,
            reason,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to update license compliance tracking."
        );
      }

      await Promise.all([
        refreshEmployeeWorkspace(),
        loadDashboard(agency.id),
      ]);
    } catch (err) {
      setWorkspaceError(err.message);
    }
  }


  async function refreshAssignments() {
    if (!agency || !selectedOfficerId) {
      return;
    }

    const response = await fetch(
      `/api/agencies/${agency.id}` +
        `/officers/${selectedOfficerId}` +
        `/assignment-summary`
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error || "Unable to refresh assignments."
      );
    }

    setAssignmentSummary(data);
  }

  async function refreshCredentialVerifications() {
    if (!agency || !selectedOfficerId) {
      return;
    }

    const response = await fetch(
      `/api/agencies/${agency.id}` +
        `/officers/${selectedOfficerId}` +
        `/credential-verifications`
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error ||
          "Unable to refresh credential verifications."
      );
    }

    setCredentialVerifications(data);
  }

  async function handleVerifyTdem() {
    const effectiveDate = window.prompt(
      "TDEM PIO certification effective date (YYYY-MM-DD):"
    );

    if (!effectiveDate) {
      return;
    }

    const verifiedBy = window.prompt(
      "Verified by:"
    );

    if (verifiedBy === null) {
      return;
    }

    const reference = window.prompt(
      "Certificate number or reference (optional):"
    );

    if (reference === null) {
      return;
    }

    setCredentialBusy(true);
    setCredentialError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}` +
          `/credential-verifications/` +
          `TDEM_PIO_CERTIFICATION`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            effective_date: effectiveDate,
            verified_by: verifiedBy,
            reference,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to verify TDEM certification."
        );
      }

      await refreshCredentialVerifications();
    } catch (err) {
      setCredentialError(err.message);
    } finally {
      setCredentialBusy(false);
    }
  }

  async function handleRevokeTdem() {
    const confirmed = window.confirm(
      "Revoke this TDEM PIO certification verification?"
    );

    if (!confirmed) {
      return;
    }

    setCredentialBusy(true);
    setCredentialError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}` +
          `/credential-verifications/` +
          `TDEM_PIO_CERTIFICATION/revoke`,
        {
          method: "PATCH",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to revoke TDEM certification verification."
        );
      }

      await refreshCredentialVerifications();
    } catch (err) {
      setCredentialError(err.message);
    } finally {
      setCredentialBusy(false);
    }
  }

  async function handleActivate(assignment) {
    const effectiveDate = window.prompt(
      `Effective date for ${assignment.assignment_name} (YYYY-MM-DD):`
    );

    if (!effectiveDate) {
      return;
    }

    setAssignmentBusy(true);
    setAssignmentError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}` +
          `/assignments/${assignment.assignment_type}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            effective_date: effectiveDate,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Unable to activate assignment."
        );
      }

      await Promise.all([
        refreshAssignments(),
        refreshEmployeeWorkspace(),
        loadDashboard(agency.id),
      ]);
    } catch (err) {
      setAssignmentError(err.message);
    } finally {
      setAssignmentBusy(false);
    }
  }

  async function handleEnd(assignment) {
    const inactiveDate = window.prompt(
      `Date ${assignment.assignment_name} stops applying (YYYY-MM-DD):`
    );

    if (!inactiveDate) {
      return;
    }

    setAssignmentBusy(true);
    setAssignmentError("");

    try {
      const response = await fetch(
        `/api/agencies/${agency.id}` +
          `/officers/${selectedOfficerId}` +
          `/assignments/${assignment.assignment_type}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            inactive_date: inactiveDate,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Unable to end assignment."
        );
      }

      await Promise.all([
        refreshAssignments(),
        refreshEmployeeWorkspace(),
        loadDashboard(agency.id),
      ]);
    } catch (err) {
      setAssignmentError(err.message);
    } finally {
      setAssignmentBusy(false);
    }
  }

  function getPeaceOfficerCertificateLevel(employee) {
    const certificate = employee.highest_certificate;

    if (certificate === "Basic Peace Officer") {
      return "BASIC";
    }

    if (certificate === "Intermediate Peace Officer") {
      return "INTERMEDIATE";
    }

    if (certificate === "Advanced Peace Officer") {
      return "ADVANCED";
    }

    if (certificate === "Master Peace Officer") {
      return "MASTER";
    }

    return "NONE";
  }

  const certificateCounts = {
    ALL: dashboard?.employees.length || 0,
    NONE: 0,
    BASIC: 0,
    INTERMEDIATE: 0,
    ADVANCED: 0,
    MASTER: 0,
  };

  dashboard?.employees.forEach((employee) => {
    const level = getPeaceOfficerCertificateLevel(employee);
    certificateCounts[level] += 1;
  });

  const filteredDashboardEmployees =
    dashboard?.employees.filter((employee) => {
      if (
        dashboardFilter !== "ALL" &&
        employee.overall_status !== dashboardFilter
      ) {
        return false;
      }

      if (
        certificateFilter !== "ALL" &&
        getPeaceOfficerCertificateLevel(employee) !==
          certificateFilter
      ) {
        return false;
      }

      const search = dashboardSearch
        .trim()
        .toLowerCase();

      if (!search) {
        return true;
      }

      const searchable = [
        employee.first_name,
        employee.middle_name,
        employee.last_name,
        employee.tcole_pid,
        employee.highest_certificate,
        ...(employee.assignments || []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchable.includes(search);
    }) || [];

  async function handleCompleteGettingStarted() {
    setGettingStartedError("");

    if (
      onboardingComplete ||
      !dismissGettingStarted
    ) {
      setGettingStartedOpen(false);
      setDismissGettingStarted(false);
      return;
    }

    setGettingStartedBusy(true);

    try {
      const response = await fetch(
        "/api/auth/complete-onboarding",
        {
          method: "POST",
          credentials: "same-origin",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to save onboarding preference."
        );
      }

      setOnboardingComplete(true);
      setGettingStartedOpen(false);
      setDismissGettingStarted(false);
    } catch (err) {
      setGettingStartedError(
        err.message ||
          "Unable to save onboarding preference."
      );
    } finally {
      setGettingStartedBusy(false);
    }
  }


  async function handleSelfPasswordChange(event) {
    event.preventDefault();

    setPasswordError("");
    setPasswordNotice("");

    if (!currentPassword) {
      setPasswordError(
        "Enter your current password."
      );
      return;
    }

    if (newPassword.length < 12) {
      setPasswordError(
        "New password must be at least 12 characters."
      );
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError(
        "New password and confirmation do not match."
      );
      return;
    }

    setPasswordBusy(true);

    try {
      const response = await fetch(
        "/api/auth/change-password",
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to change your password."
        );
      }

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");

      setPasswordNotice(
        data.message ||
          "Password changed successfully."
      );
    } catch (err) {
      setPasswordError(
        err.message ||
          "Unable to change your password."
      );
    } finally {
      setPasswordBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="authenticated-brand">
          <img
            src="/ptm-logo.png"
            alt=""
            className="authenticated-brand-logo"
            aria-hidden="true"
          />

          <div className="authenticated-brand-copy">
            <h1>
              Paradigm Training Manager
              <sup className="product-mark">™</sup>
            </h1>

            <div className="authenticated-brand-company">
              by Paradigm Strategic Partners, LLC
            </div>
          </div>
        </div>

        <div className="authenticated-user">
          <div>
            <strong>
              {currentUser?.first_name}{" "}
              {currentUser?.last_name}
            </strong>

            <span>
              {currentUser?.agency?.name ||
                "Paradigm Strategic Partners"}
            </span>
          </div>

          {currentUser?.role === "PLATFORM_ADMIN" && (
            <a
              href="/platform"
              className="platform-app-link"
            >
              Platform Administration
            </a>
          )}

          <button
            type="button"
            onClick={() => {
              setPasswordError("");
              setPasswordNotice("");
              setAccountOpen(true);
            }}
          >
            Account
          </button>

          <button
            type="button"
            onClick={onLogout}
          >
            Log Out
          </button>
        </div>
      </header>

      {gettingStartedOpen && (
        <div
          className="getting-started-backdrop"
          role="presentation"
        >
          <section
            className="getting-started-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="getting-started-title"
          >
            <div className="getting-started-heading">
              <div>
                <span>
                  GETTING STARTED
                </span>

                <h2 id="getting-started-title">
                  Set Up Your Agency in PTM
                </h2>

                <p>
                  Follow these five simple steps to
                  load your agency's TCOLE data and
                  get Paradigm Training Manager ready
                  to use.
                </p>
              </div>

              {onboardingComplete && (
                <button
                  type="button"
                  className="getting-started-close"
                  aria-label="Close Getting Started Guide"
                  onClick={() =>
                    setGettingStartedOpen(false)
                  }
                >
                  ×
                </button>
              )}
            </div>

            <div className="getting-started-content">
              {gettingStartedError && (
                <div className="getting-started-error">
                  {gettingStartedError}
                </div>
              )}

              <section className="getting-started-step">
                <div className="getting-started-number">
                  1
                </div>

                <div>
                  <h3>
                    Log in to TCLEDDS
                  </h3>

                  <p>
                    Log in to your agency's TCLEDDS
                    account and scroll down to{" "}
                    <strong>Reports</strong>.
                  </p>
                </div>
              </section>

              <section className="getting-started-step">
                <div className="getting-started-number">
                  2
                </div>

                <div>
                  <h3>
                    Download Four Reports
                  </h3>

                  <p>
                    Download the following reports as
                    CSV files:
                  </p>

                  <ol className="getting-started-report-list">
                    <li>
                      Licensees And Awards
                    </li>
                    <li>
                      Licensees Taken Or Missing A Course
                    </li>
                    <li>
                      Cycle Training - All Courses
                    </li>
                    <li>
                      Department Licensee Search Report
                    </li>
                  </ol>

                  <div className="getting-started-image-wrap">
                    <img
                      src="/tcledds-department-reports.png"
                      alt="TCLEDDS Department Reports showing the four reports required for Paradigm Training Manager"
                    />
                  </div>

                  <p>
                    For each report:
                  </p>

                  <ul>
                    <li>
                      Select <strong>All</strong>{" "}
                      employees/licensees.
                    </li>
                    <li>
                      Set the Start Date to{" "}
                      <strong>01/01/1900</strong>.
                    </li>
                    <li>
                      Set the End Date to{" "}
                      <strong>today's date</strong>.
                    </li>
                    <li>
                      Leave other filters set to{" "}
                      <strong>All</strong> unless
                      TCLEDDS requires otherwise.
                    </li>
                    <li>
                      Export/download the report as a
                      CSV file.
                    </li>
                  </ul>

                  <div className="getting-started-warning">
                    Do not rename or modify the CSV files.
                  </div>
                </div>
              </section>

              <section className="getting-started-step">
                <div className="getting-started-number">
                  3
                </div>

                <div>
                  <h3>
                    Upload the Reports to PTM
                  </h3>

                  <p>
                    Return to Paradigm Training Manager
                    and find the{" "}
                    <strong>TCOLE Data Import</strong>{" "}
                    section on the main page. Upload all
                    four CSV files.
                  </p>

                  <p>
                    PTM will import your agency's
                    employees, certifications, training
                    history, and cycle information and
                    automatically evaluate the applicable
                    compliance requirements.
                  </p>
                </div>
              </section>

              <section className="getting-started-step">
                <div className="getting-started-number">
                  4
                </div>

                <div>
                  <h3>
                    Review Email Settings
                  </h3>

                  <p>
                    Open <strong>Email Settings</strong>{" "}
                    and confirm the information PTM
                    should use when generating employee
                    compliance notifications.
                  </p>
                </div>
              </section>

              <section className="getting-started-step">
                <div className="getting-started-number">
                  5
                </div>

                <div>
                  <h3>
                    You're Done
                  </h3>

                  <p>
                    That's it. Your agency is now ready
                    to use PTM.
                  </p>

                  <p>
                    From here, PTM tells you who is
                    compliant, who isn't, what each
                    employee still needs, and when it is
                    due.
                  </p>
                </div>
              </section>
            </div>

            <div className="getting-started-actions">
              {!onboardingComplete && (
                <label className="getting-started-dismiss">
                  <input
                    type="checkbox"
                    checked={dismissGettingStarted}
                    onChange={(event) =>
                      setDismissGettingStarted(
                        event.target.checked
                      )
                    }
                    disabled={gettingStartedBusy}
                  />

                  <span>
                    Don't show this automatically again.
                  </span>
                </label>
              )}

              <button
                type="button"
                className="getting-started-primary"
                disabled={gettingStartedBusy}
                onClick={handleCompleteGettingStarted}
              >
                {gettingStartedBusy
                  ? "Saving..."
                  : onboardingComplete
                    ? "Close Guide"
                    : "Continue to PTM"}
              </button>
            </div>
          </section>
        </div>
      )}

      {accountOpen && (
        <div
          className="account-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setAccountOpen(false);
              setPasswordError("");
              setPasswordNotice("");
              setCurrentPassword("");
              setNewPassword("");
              setConfirmPassword("");
            }
          }}
        >
          <section
            className="account-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="account-password-title"
          >
            <div className="account-modal-heading">
              <div>
                <span>ACCOUNT SECURITY</span>
                <h2 id="account-password-title">
                  Change Password
                </h2>
                <p>
                  Update the password used to sign in to
                  Paradigm Training Manager.
                </p>
              </div>

              <button
                type="button"
                className="account-modal-close"
                aria-label="Close account settings"
                onClick={() => {
                  setAccountOpen(false);
                  setPasswordError("");
                  setPasswordNotice("");
                  setCurrentPassword("");
                  setNewPassword("");
                  setConfirmPassword("");
                }}
              >
                ×
              </button>
            </div>

            {passwordError && (
              <div className="account-message error">
                {passwordError}
              </div>
            )}

            {passwordNotice && (
              <div className="account-message success">
                {passwordNotice}
              </div>
            )}

            <div className="account-guide-section">
              <div>
                <strong>
                  Getting Started Guide
                </strong>

                <span>
                  Review the five-step TCLEDDS setup
                  and import instructions.
                </span>
              </div>

              <button
                type="button"
                className="account-secondary-button"
                onClick={() => {
                  setAccountOpen(false);
                  setGettingStartedError("");
                  setGettingStartedOpen(true);
                }}
              >
                Open Guide
              </button>
            </div>

            <form
              className="account-password-form"
              onSubmit={handleSelfPasswordChange}
            >
              <label>
                <span>Current Password</span>
                <input
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) =>
                    setCurrentPassword(
                      event.target.value
                    )
                  }
                  disabled={passwordBusy}
                  required
                />
              </label>

              <label>
                <span>New Password</span>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(event) =>
                    setNewPassword(
                      event.target.value
                    )
                  }
                  disabled={passwordBusy}
                  minLength={12}
                  required
                />

                <small>
                  Minimum 12 characters.
                </small>
              </label>

              <label>
                <span>Confirm New Password</span>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(
                      event.target.value
                    )
                  }
                  disabled={passwordBusy}
                  minLength={12}
                  required
                />
              </label>

              <div className="account-modal-actions">
                <button
                  type="button"
                  className="account-secondary-button"
                  disabled={passwordBusy}
                  onClick={() => {
                    setAccountOpen(false);
                    setPasswordError("");
                    setPasswordNotice("");
                    setCurrentPassword("");
                    setNewPassword("");
                    setConfirmPassword("");
                  }}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="account-primary-button"
                  disabled={passwordBusy}
                >
                  {passwordBusy
                    ? "Changing Password..."
                    : "Change Password"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      <main className="page">
        {archivedEmployeesOpen ? (
          <section className="archived-employees-workspace">
            <div className="archived-employees-heading">
              <div>
                <div className="dashboard-kicker">
                  Employee Lifecycle Management
                </div>

                <h2>Archived Employees</h2>

                <p>
                  Archived employees remain in PTM with
                  their historical records preserved.
                </p>
              </div>

              <button
                type="button"
                className="workspace-back"
                onClick={closeArchivedEmployees}
              >
                ← Back to Dashboard
              </button>
            </div>

            <div className="archived-employees-toolbar">
              <input
                type="search"
                placeholder="Search archived employees..."
                value={archivedEmployeeSearch}
                onChange={(event) =>
                  setArchivedEmployeeSearch(
                    event.target.value
                  )
                }
              />

              <strong>
                {
                  archivedEmployees.filter(
                    (employee) => {
                      const search =
                        archivedEmployeeSearch
                          .trim()
                          .toLowerCase();

                      if (!search) {
                        return true;
                      }

                      const value = [
                        employee.first_name,
                        employee.middle_name,
                        employee.last_name,
                        employee.tcole_pid,
                      ]
                        .filter(Boolean)
                        .join(" ")
                        .toLowerCase();

                      return value.includes(search);
                    }
                  ).length
                }{" "}
                archived
              </strong>
            </div>

            {archivedEmployeesError && (
              <div className="message error-message">
                {archivedEmployeesError}
              </div>
            )}

            {archivedEmployeesLoading ? (
              <div className="dashboard-loading">
                Loading archived employees...
              </div>
            ) : (
              <div className="archived-employees-list">
                {archivedEmployees
                  .filter((employee) => {
                    const search =
                      archivedEmployeeSearch
                        .trim()
                        .toLowerCase();

                    if (!search) {
                      return true;
                    }

                    const value = [
                      employee.first_name,
                      employee.middle_name,
                      employee.last_name,
                      employee.tcole_pid,
                    ]
                      .filter(Boolean)
                      .join(" ")
                      .toLowerCase();

                    return value.includes(search);
                  })
                  .map((employee) => (
                    <button
                      key={employee.id}
                      type="button"
                      className="archived-employee-row"
                      onClick={() =>
                        openEmployeeWorkspace(employee)
                      }
                    >
                      <div>
                        <strong>
                          {[
                            employee.first_name,
                            employee.middle_name,
                            employee.last_name,
                          ]
                            .filter(Boolean)
                            .join(" ")}
                        </strong>

                        <span>
                          PID {employee.tcole_pid}
                        </span>
                      </div>

                      <span className="employee-status archived">
                        ARCHIVED
                      </span>
                    </button>
                  ))}

                {!archivedEmployeesLoading &&
                  archivedEmployees.length === 0 && (
                    <div className="dashboard-empty">
                      No archived employees.
                    </div>
                  )}
              </div>
            )}
          </section>
        ) : communicationsOpen ? (
          <ComplianceCommunicationsWorkspace
            preflight={communicationsPreflight}
            loading={communicationsLoading}
            error={communicationsError}
            selectedIds={communicationsSelectedIds}
            setSelectedIds={
              setCommunicationsSelectedIds
            }
            onBack={closeComplianceCommunications}
          />
        ) : workspaceOpen ? (
          <EmployeeWorkspace
            workspace={employeeWorkspace}
            loading={loadingWorkspace}
            error={workspaceError}
            onBack={closeEmployeeWorkspace}
            assignmentSummary={assignmentSummary}
            assignmentBusy={assignmentBusy}
            assignmentError={assignmentError}
            credentialVerifications={
              credentialVerifications
            }
            credentialBusy={credentialBusy}
            credentialError={credentialError}
            qualificationFacts={qualificationFacts}
            qualificationBusy={qualificationBusy}
            qualificationError={qualificationError}
            onSaveQualificationFacts={
              employeeWorkspace?.officer
                ?.employment_status === "archived"
                ? undefined
                : handleSaveQualificationFacts
            }
            onActivateAssignment={
              employeeWorkspace?.officer
                ?.employment_status === "archived"
                ? undefined
                : handleActivate
            }
            onEndAssignment={
              employeeWorkspace?.officer
                ?.employment_status === "archived"
                ? undefined
                : handleEnd
            }
            onVerifyTdem={
              employeeWorkspace?.officer
                ?.employment_status === "archived"
                ? undefined
                : handleVerifyTdem
            }
            onRevokeTdem={
              employeeWorkspace?.officer
                ?.employment_status === "archived"
                ? undefined
                : handleRevokeTdem
            }
            onEditEmail={handleEditEmployeeEmail}
            onEmailEmployee={handleEmailEmployee}
            onArchiveEmployee={
              handleArchiveEmployee
            }
            onRestoreEmployee={
              handleRestoreEmployee
            }
            onSetLicenseTracking={
              employeeWorkspace?.officer
                ?.employment_status === "archived"
                ? undefined
                : handleSetLicenseTracking
            }
            lifecycleBusy={lifecycleBusy}
          />
        ) : (
          <>
        <section className="dashboard-section">
          <div className="dashboard-heading dashboard-heading-redesign">
            <div className="dashboard-heading-copy">
              <div className="dashboard-kicker">
                Executive Compliance Dashboard
              </div>

              <h2>
                {agency?.name ||
                  "Agency Compliance"}
              </h2>

              <p>
                Current TCOLE compliance posture and
                prioritized training requirements.
              </p>

              <div className="dashboard-data-notice">
                <strong>TCOLE Data Notice:</strong>{" "}
                PTM is a compliance management tool designed
                to organize and evaluate TCOLE-reported data.
                TCOLE reports may occasionally contain
                differing information. When a discrepancy
                exists, the applicable TCOLE record should be
                treated as the authoritative source.
              </div>


            </div>

            <div className="dashboard-heading-footer">
              <div className="dashboard-header-actions">
                <button
                  type="button"
                  className="archived-employees-button"
                  onClick={openArchivedEmployees}
                >
                  Archived Employees
                </button>

                <button
                  type="button"
                  className="communications-launch-button"
                  onClick={openComplianceCommunications}
                >
                  Email Compliance Updates
                </button>

                <button
                  type="button"
                  className="agency-email-settings-button"
                  onClick={() => {
                    setEmailSettingsError("");
                    setEmailDomain(
                      agency?.email_domain || ""
                    );
                    setEmailPattern(
                      agency?.email_pattern || ""
                    );
                    setEmailSettingsOpen(true);
                  }}
                >
                  Email Settings
                </button>
              </div>

              {dashboard && (
                <div className="dashboard-period">
                  <span>
                    Training Unit{" "}
                    {dashboard.training_unit.number}
                  </span>
                  <strong>
                    {formatDashboardDate(
                      dashboard.training_unit.start
                    )}{" "}
                    through{" "}
                    {formatDashboardDate(
                      dashboard.training_unit.end
                    )}
                  </strong>
                </div>
              )}
            </div>
          </div>

          {emailSettingsOpen && (
            <section className="agency-email-settings-panel">
              <div className="agency-email-settings-heading">
                <div>
                  <h3>Agency Email Settings</h3>
                  <p>
                    Define the standard employee email
                    convention for this agency.
                  </p>
                </div>

                <button
                  type="button"
                  className="settings-close-button"
                  aria-label="Close email settings"
                  onClick={() =>
                    setEmailSettingsOpen(false)
                  }
                >
                  ×
                </button>
              </div>

              {emailSettingsError && (
                <div className="message error-message">
                  {emailSettingsError}
                </div>
              )}

              <form
                className="agency-email-settings-form"
                onSubmit={handleSaveEmailSettings}
              >
                <label>
                  <span>Email Domain</span>
                  <input
                    type="text"
                    value={emailDomain}
                    placeholder="example.gov"
                    onChange={(event) =>
                      setEmailDomain(
                        event.target.value
                      )
                    }
                  />
                </label>

                <label>
                  <span>Email Format</span>
                  <select
                    value={emailPattern}
                    onChange={(event) =>
                      setEmailPattern(
                        event.target.value
                      )
                    }
                  >
                    <option value="">
                      Select email format
                    </option>
                    <option value="FIRST_INITIAL_LAST">
                      First initial + last name
                    </option>
                    <option value="FIRST_DOT_LAST">
                      First name . last name
                    </option>
                    <option value="FIRST_LAST">
                      First name + last name
                    </option>
                    <option value="LAST_FIRST_INITIAL">
                      Last name + first initial
                    </option>
                  </select>
                </label>

                <div className="agency-email-example">
                  <span>Example</span>
                  <strong>
                    {buildEmailConventionExample(
                      emailPattern,
                      emailDomain
                    )}
                  </strong>
                </div>

                <div className="agency-email-settings-actions">
                  <button
                    type="button"
                    className="settings-secondary-button"
                    disabled={emailSettingsBusy}
                    onClick={() =>
                      setEmailSettingsOpen(false)
                    }
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="settings-primary-button"
                    disabled={emailSettingsBusy}
                  >
                    {emailSettingsBusy
                      ? "Saving..."
                      : "Save Email Settings"}
                  </button>
                </div>
              </form>
            </section>
          )}

          {loadingDashboard && (
            <div className="dashboard-loading">
              Loading compliance dashboard...
            </div>
          )}

          {dashboardError && (
            <div className="message error-message">
              <strong>
                Compliance dashboard could not be loaded.
              </strong>
              <p>{dashboardError}</p>
            </div>
          )}

          {dashboard && (
            <>
              <div className="dashboard-summary-grid">
                <DashboardSummaryCard
                  label="Active Employees"
                  value={
                    dashboard.summary.active_employee_count
                  }
                  status="all"
                  active={dashboardFilter === "ALL"}
                  onClick={() =>
                    setDashboardFilter("ALL")
                  }
                />

                <DashboardSummaryCard
                  label="Compliant"
                  value={
                    dashboard.summary.compliant_count
                  }
                  status="compliant"
                  active={
                    dashboardFilter === "COMPLIANT"
                  }
                  onClick={() =>
                    setDashboardFilter("COMPLIANT")
                  }
                />

                <DashboardSummaryCard
                  label="Training Due"
                  value={dashboard.summary.due_count}
                  status="due"
                  active={dashboardFilter === "DUE"}
                  onClick={() =>
                    setDashboardFilter("DUE")
                  }
                />

                <DashboardSummaryCard
                  label="Noncompliant"
                  value={
                    dashboard.summary.noncompliant_count
                  }
                  status="noncompliant"
                  active={
                    dashboardFilter === "NONCOMPLIANT"
                  }
                  onClick={() =>
                    setDashboardFilter("NONCOMPLIANT")
                  }
                />

                <DashboardSummaryCard
                  label="Not Evaluated"
                  value={
                    dashboard.summary.not_evaluated_count
                  }
                  status="not-evaluated"
                  active={
                    dashboardFilter === "NOT_EVALUATED"
                  }
                  onClick={() =>
                    setDashboardFilter("NOT_EVALUATED")
                  }
                />
              </div>

              <div className="certificate-filter-section">
                <div className="certificate-filter-label">
                  Highest Peace Officer Certificate
                </div>

                <div
                  className="certificate-tabs"
                  role="group"
                  aria-label="Filter by highest Peace Officer certificate"
                >
                  {[
                    ["ALL", "All"],
                    ["NONE", "No Certificate"],
                    ["BASIC", "Basic"],
                    ["INTERMEDIATE", "Intermediate"],
                    ["ADVANCED", "Advanced"],
                    ["MASTER", "Master"],
                  ].map(([value, label]) => (
                    <button
                      type="button"
                      key={value}
                      className={
                        "certificate-tab" +
                        (
                          certificateFilter === value
                            ? " active"
                            : ""
                        )
                      }
                      onClick={() =>
                        setCertificateFilter(value)
                      }
                    >
                      <span>{label}</span>
                      <strong>
                        {certificateCounts[value]}
                      </strong>
                    </button>
                  ))}
                </div>
              </div>

              <div className="dashboard-toolbar">
                <div className="dashboard-search">
                  <label htmlFor="dashboard-search">
                    Search employees
                  </label>

                  <input
                    id="dashboard-search"
                    type="search"
                    placeholder="Name, PID, certificate, or assignment"
                    value={dashboardSearch}
                    onChange={(event) =>
                      setDashboardSearch(
                        event.target.value
                      )
                    }
                  />
                </div>

                <div className="dashboard-result-count">
                  Showing{" "}
                  <strong>
                    {filteredDashboardEmployees.length}
                  </strong>{" "}
                  of{" "}
                  <strong>
                    {
                      dashboard.summary
                        .active_employee_count
                    }
                  </strong>{" "}
                  employees
                </div>
              </div>

              <div className="employee-compliance-list">
                {filteredDashboardEmployees.map(
                  (employee) => (
                    <EmployeeComplianceCard
                      key={employee.id}
                      employee={employee}
                      onOpen={openEmployeeWorkspace}
                    />
                  )
                )}

                {filteredDashboardEmployees.length ===
                  0 && (
                  <div className="dashboard-empty">
                    No employees match the current
                    dashboard filter.
                  </div>
                )}
              </div>
            </>
          )}
        </section>

        <section className="intro admin-intro">
          <h2>TCOLE Compliance Data Import</h2>

          <p>
            Upload the four official TCOLE reports for your agency.
            PTM will reconcile personnel, licenses, awards, training
            history, and actual credited training hours.
          </p>

          <div className="agency-panel">
            <span>Agency</span>
            <strong>
              {loadingAgency
                ? "Loading..."
                : agency?.name || "Not configured"}
            </strong>
          </div>
        </section>

        <form className="import-panel" onSubmit={handleImport}>
          <FileField
            label="Awards Report"
            description="rptAwards.csv"
            file={awardsFile}
            onChange={setAwardsFile}
          />

          <FileField
            label="Course History"
            description="rptCourseTaken.csv"
            file={coursesFile}
            onChange={setCoursesFile}
          />

          <FileField
            label="Cycle Training Report"
            description="rptCycleT_All.csv"
            file={cycleFile}
            onChange={setCycleFile}
          />

          <FileField
            label="Department Licensee Search Report"
            description="rptDepartmentOfficerSearch.csv"
            file={licenseeSearchFile}
            onChange={setLicenseeSearchFile}
          />

          <div className="import-action">
            <button
              type="submit"
              className="import-button"
              disabled={!ready}
            >
              {importing
                ? "Importing TCOLE Records..."
                : "Import TCOLE Records"}
            </button>
          </div>
        </form>

        {error && (
          <section className="message error-message">
            <strong>Import could not be completed.</strong>
            <p>{error}</p>
          </section>
        )}

        {result && (
          <section className="results">
            <div className="success-heading">
              <div className="success-icon">✓</div>

              <div>
                <h2>Import Completed Successfully</h2>
                <p>
                  PTM reconciled all four TCOLE reports.
                </p>
              </div>
            </div>

            <div className="results-grid">
              <ResultCard
                label="Officers"
                value={result.officer_count}
              />
              <ResultCard
                label="Awards Processed"
                value={result.award_rows_processed}
              />
              <ResultCard
                label="Course Rows"
                value={result.course_rows_processed}
              />
              <ResultCard
                label="Training Records"
                value={result.training_records_created}
              />
              <ResultCard
                label="Cycle Rows"
                value={result.cycle_rows_processed}
              />
              <ResultCard
                label="License Search Rows"
                value={result.licensee_search_rows_processed}
              />
              <ResultCard
                label="Peace Officer Licenses"
                value={result.peace_officer_license_rows}
              />
              <ResultCard
                label="Service Dates Populated"
                value={result.service_dates_populated}
              />
              <ResultCard
                label="Records With Hours"
                value={result.training_records_with_hours}
              />
              <ResultCard
                label="Warnings"
                value={result.warning_count}
              />
              <ResultCard
                label="Errors"
                value={result.error_count}
              />
            </div>
          </section>
        )}

          </>
        )}
      </main>
    </div>
  );
}



function ProductFooter() {
  return (
    <footer className="product-footer">
      <div className="product-footer-inner">
        <div>
          <strong>
            Paradigm Training Manager
            <sup className="product-mark">™</sup>
          </strong>
          <span>
            {" "}
            | Version {__PTM_VERSION__}
          </span>
        </div>

        <div>
          Copyright © 2026 Paradigm Strategic Partners,
          LLC. All Rights Reserved.
        </div>
      </div>
    </footer>
  );
}



function RoiCalculator() {
  const [employees, setEmployees] = useState("50");
  const [hoursPerMonth, setHoursPerMonth] =
    useState("8");
  const [hourlyCost, setHourlyCost] = useState("45");

  const annualHours =
    Math.max(0, Number(hoursPerMonth) || 0) * 12;

  const annualCost =
    annualHours *
    Math.max(0, Number(hourlyCost) || 0);

  const recoveredHours = annualHours * 0.75;
  const recoveredValue =
    recoveredHours *
    Math.max(0, Number(hourlyCost) || 0);

  const employeeCount =
    Math.max(0, Number(employees) || 0);

  let estimatedSubscription = 399;

  if (employeeCount > 300) {
    estimatedSubscription = null;
  } else if (employeeCount > 150) {
    estimatedSubscription = 2999;
  } else if (employeeCount > 75) {
    estimatedSubscription = 1999;
  } else if (employeeCount > 35) {
    estimatedSubscription = 1199;
  } else if (employeeCount > 15) {
    estimatedSubscription = 749;
  }

  const netValue =
    estimatedSubscription == null
      ? null
      : recoveredValue - estimatedSubscription;

  const multiple =
    estimatedSubscription &&
    estimatedSubscription > 0
      ? recoveredValue / estimatedSubscription
      : null;

  return (
    <div className="public-roi-calculator">
      <div className="public-roi-inputs">
        <label>
          <span>Licensed employees</span>
          <input
            type="number"
            min="1"
            value={employees}
            onChange={(event) =>
              setEmployees(event.target.value)
            }
          />
        </label>

        <label>
          <span>
            Hours spent managing compliance each month
          </span>
          <input
            type="number"
            min="0"
            step="0.5"
            value={hoursPerMonth}
            onChange={(event) =>
              setHoursPerMonth(event.target.value)
            }
          />
        </label>

        <label>
          <span>Estimated hourly staff cost</span>
          <input
            type="number"
            min="0"
            step="1"
            value={hourlyCost}
            onChange={(event) =>
              setHourlyCost(event.target.value)
            }
          />
        </label>
      </div>

      <div className="public-roi-results">
        <div>
          <span>Your current process</span>
          <strong>
            {annualHours.toLocaleString()} hours/year
          </strong>
          <small>
            ${annualCost.toLocaleString()} estimated annual
            staff cost
          </small>
        </div>

        <div>
          <span>Illustrative PTM scenario</span>
          <strong>
            {Math.round(
              recoveredHours
            ).toLocaleString()}{" "}
            staff hours returned
          </strong>
          <small>
            ${Math.round(
              recoveredValue
            ).toLocaleString()}{" "}
            estimated staff-time value recovered
          </small>
        </div>

        <div className="public-roi-net">
          <span>Estimated net value</span>
          <strong>
            {netValue == null
              ? "Contact us"
              : `$${Math.round(
                  netValue
                ).toLocaleString()}/year`}
          </strong>
          <small>
            {estimatedSubscription == null
              ? "Enterprise Plus pricing is custom."
              : `PTM subscription estimate: $${estimatedSubscription.toLocaleString()}/year`}
          </small>

          {multiple != null && (
            <small>
              Illustrative staff-time value:
              {" "}
              {multiple.toFixed(1)}× subscription cost
            </small>
          )}
        </div>
      </div>

      <p className="public-roi-disclaimer">
        Illustrative estimate based on the values entered
        above and an assumed 75% reduction in administrative
        time. Actual time savings will vary by agency.
      </p>
    </div>
  );
}


function PricingCard({
  name,
  range,
  logins,
  price,
  featured = false,
}) {
  return (
    <article
      className={
        "public-pricing-card" +
        (featured ? " featured" : "")
      }
    >
      {featured && (
        <span className="public-pricing-featured">
          Popular
        </span>
      )}

      <h3>{name}</h3>
      <p>{range}</p>
      <strong>{price}</strong>
      <span>{logins}</span>
    </article>
  );
}


function FaqItem({ question, answer }) {
  const [open, setOpen] = useState(false);

  return (
    <article className="public-faq-item">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <span>{question}</span>
        <strong>{open ? "−" : "+"}</strong>
      </button>

      {open && <p>{answer}</p>}
    </article>
  );
}



function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    setBusy(true);
    setError("");

    try {
      const response = await fetch(
        "/api/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "same-origin",
          body: JSON.stringify({
            email,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Unable to sign in."
        );
      }

      window.location.href =
        data.user?.role === "PLATFORM_ADMIN"
          ? "/platform"
          : "/app";
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-shell">
        <a href="/" className="login-brand">
          <span>
            Paradigm Strategic Partners
          </span>

          <strong>
            Paradigm Training Manager
            <sup className="product-mark">™</sup>
          </strong>
        </a>

        <section className="login-card">
          <div className="login-heading">
            <span>AGENCY ACCESS</span>
            <h1>Sign in to PTM</h1>

            <p>
              Use the credentials assigned to you by
              Paradigm or your agency administrator.
            </p>
          </div>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <label>
              <span>Email address</span>

              <input
                type="email"
                autoComplete="username"
                required
                value={email}
                disabled={busy}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
              />
            </label>

            <label>
              <span>Password</span>

              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                disabled={busy}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
              />
            </label>

            <button
              type="submit"
              disabled={busy}
            >
              {busy
                ? "Signing In..."
                : "Sign In"}
            </button>
          </form>

          <div className="login-help">
            PTM accounts are created for authorized
            agency personnel. Public account registration
            is not available.
          </div>
        </section>

        <a href="/" className="login-return">
          ← Return to Paradigm Training Manager
        </a>
      </div>
    </div>
  );
}


function AuthenticatedApplication() {
  const [authState, setAuthState] = useState({
    loading: true,
    user: null,
  });

  useEffect(() => {
    let active = true;

    async function loadCurrentUser() {
      try {
        const response = await fetch(
          "/api/auth/me",
          {
            credentials: "same-origin",
          }
        );

        if (response.status === 401) {
          window.location.replace("/login");
          return;
        }

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error ||
              "Unable to verify your PTM session."
          );
        }

        if (
          data.user?.role === "PLATFORM_ADMIN"
        ) {
          window.location.replace("/platform");
          return;
        }

        if (active) {
          setAuthState({
            loading: false,
            user: data.user,
          });
        }
      } catch {
        if (active) {
          window.location.replace("/login");
        }
      }
    }

    loadCurrentUser();

    return () => {
      active = false;
    };
  }, []);

  async function handleLogout() {
    try {
      await fetch(
        "/api/auth/logout",
        {
          method: "POST",
          credentials: "same-origin",
        }
      );
    } finally {
      window.location.replace("/login");
    }
  }

  if (authState.loading) {
    return (
      <div className="auth-loading">
        <div>
          <strong>
            Paradigm Training Manager
            <sup className="product-mark">™</sup>
          </strong>

          <span>
            Verifying your secure session...
          </span>
        </div>
      </div>
    );
  }

  return (
    <OperationalApp
      currentUser={authState.user}
      onLogout={handleLogout}
    />
  );
}


function formatPlatformDate(value) {
  if (!value) {
    return "Never";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}


function PlatformAdministration({
  currentUser,
  onLogout,
}) {
  const [agencies, setAgencies] = useState([]);
  const [selectedAgency, setSelectedAgency] =
    useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [newAgencyOpen, setNewAgencyOpen] =
    useState(false);

  const [newAgency, setNewAgency] = useState({
    name: "",
    tcole_agency_number: "",
    ori: "",
    email_domain: "",
    email_pattern: "",
  });

  const [newAdminOpen, setNewAdminOpen] =
    useState(false);

  const [newAdmin, setNewAdmin] = useState({
    first_name: "",
    last_name: "",
    email: "",
  });

  const [
    generatedInvitation,
    setGeneratedInvitation,
  ] = useState(null);

  const [
    invitationCopyNotice,
    setInvitationCopyNotice,
  ] = useState("");

  const [resetUser, setResetUser] =
    useState(null);

  const [resetPassword, setResetPassword] =
    useState("");

  const [resetPasswordConfirm, setResetPasswordConfirm] =
    useState("");

  const [editAgencyOpen, setEditAgencyOpen] =
    useState(false);

  const [editAgency, setEditAgency] = useState({
    name: "",
    tcole_agency_number: "",
    ori: "",
    email_domain: "",
    email_pattern: "",
  });

  const [editAdminUser, setEditAdminUser] =
    useState(null);

  const [editAdmin, setEditAdmin] = useState({
    first_name: "",
    last_name: "",
    email: "",
  });

  async function fetchJson(
    url,
    options = {},
  ) {
    const response = await fetch(
      url,
      {
        credentials: "same-origin",
        ...options,
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error ||
          "Unable to complete the request."
      );
    }

    return data;
  }

  async function loadAgencies() {
    setLoading(true);
    setError("");

    try {
      const data = await fetchJson(
        "/api/platform/agencies"
      );

      setAgencies(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function openAgency(agencyId) {
    setBusy(true);
    setError("");
    setNotice("");

    try {
      const data = await fetchJson(
        `/api/platform/agencies/${agencyId}`
      );

      setSelectedAgency(data);
      setNewAdminOpen(false);
      setResetUser(null);
      setEditAgencyOpen(false);
      setEditAdminUser(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function refreshSelectedAgency() {
    if (!selectedAgency?.id) {
      return;
    }

    const data = await fetchJson(
      `/api/platform/agencies/${selectedAgency.id}`
    );

    setSelectedAgency(data);

    setAgencies((current) =>
      current.map((agency) =>
        agency.id === data.id
          ? {
              ...agency,
              ...data,
              administrators: undefined,
            }
          : agency
      )
    );
  }

  useEffect(() => {
    loadAgencies();
  }, []);

  async function handleCreateAdmin(event) {
    event.preventDefault();

    setError("");
    setNotice("");
    setInvitationCopyNotice("");

    setBusy(true);

    try {
      const result = await fetchJson(
        `/api/platform/agencies/${selectedAgency.id}/administrators`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            first_name:
              newAdmin.first_name,
            last_name:
              newAdmin.last_name,
            email:
              newAdmin.email,
          }),
        }
      );

      await refreshSelectedAgency();

      setNewAdmin({
        first_name: "",
        last_name: "",
        email: "",
      });

      setNewAdminOpen(false);

      setGeneratedInvitation({
        user: result,
        url:
          `${window.location.origin}${result.invitation_path}`,
      });

      setNotice(
        "Administrator invitation created."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRegenerateInvitation(user) {
    setBusy(true);
    setError("");
    setNotice("");
    setInvitationCopyNotice("");

    try {
      const result = await fetchJson(
        `/api/platform/agencies/${selectedAgency.id}/administrators/${user.id}/resend-invitation`,
        {
          method: "POST",
        }
      );

      await refreshSelectedAgency();

      setGeneratedInvitation({
        user: result,
        url:
          `${window.location.origin}${result.invitation_path}`,
      });

      setNotice(
        "A new invitation link was generated. "
        + "The previous link is no longer valid."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCopyInvitation() {
    if (!generatedInvitation?.url) {
      return;
    }

    try {
      await navigator.clipboard.writeText(
        generatedInvitation.url
      );

      setInvitationCopyNotice(
        "Invitation link copied."
      );
    } catch {
      setInvitationCopyNotice(
        "Copy failed. Select and copy the link manually."
      );
    }
  }

  async function handleAdminStatus(
    user,
    status,
  ) {
    setBusy(true);
    setError("");
    setNotice("");

    try {
      await fetchJson(
        `/api/platform/agencies/${selectedAgency.id}/administrators/${user.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            status,
          }),
        }
      );

      await refreshSelectedAgency();

      setNotice(
        status === "active"
          ? "Administrator activated."
          : "Administrator deactivated."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function beginAgencyEdit() {
    setEditAgency({
      name: selectedAgency.name || "",
      tcole_agency_number:
        selectedAgency.tcole_agency_number || "",
      ori: selectedAgency.ori || "",
      email_domain:
        selectedAgency.email_domain || "",
      email_pattern:
        selectedAgency.email_pattern || "",
    });

    setEditAgencyOpen(true);
    setError("");
    setNotice("");
  }

  async function handleAgencyUpdate(event) {
    event.preventDefault();

    setBusy(true);
    setError("");
    setNotice("");

    try {
      await fetchJson(
        `/api/platform/agencies/${selectedAgency.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: editAgency.name,
            tcole_agency_number:
              editAgency.tcole_agency_number,
            ori: editAgency.ori,
            email_domain:
              editAgency.email_domain,
            email_pattern:
              editAgency.email_pattern,
          }),
        }
      );

      await refreshSelectedAgency();
      setEditAgencyOpen(false);
      setNotice("Agency information updated.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function beginAdminEdit(user) {
    setEditAdminUser(user);

    setEditAdmin({
      first_name: user.first_name || "",
      last_name: user.last_name || "",
      email: user.email || "",
    });

    setResetUser(null);
    setError("");
    setNotice("");
  }

  async function handleAdminUpdate(event) {
    event.preventDefault();

    setBusy(true);
    setError("");
    setNotice("");

    try {
      await fetchJson(
        `/api/platform/agencies/${selectedAgency.id}/administrators/${editAdminUser.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            first_name: editAdmin.first_name,
            last_name: editAdmin.last_name,
            email: editAdmin.email,
          }),
        }
      );

      await refreshSelectedAgency();
      setEditAdminUser(null);
      setNotice(
        "Administrator information updated."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handlePasswordReset(event) {
    event.preventDefault();

    setError("");
    setNotice("");

    if (
      resetPassword !==
      resetPasswordConfirm
    ) {
      setError(
        "The new passwords do not match."
      );
      return;
    }

    setBusy(true);

    try {
      await fetchJson(
        `/api/platform/agencies/${selectedAgency.id}/administrators/${resetUser.id}/reset-password`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            password: resetPassword,
          }),
        }
      );

      setResetUser(null);
      setResetPassword("");
      setResetPasswordConfirm("");

      setNotice(
        "Administrator password reset."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (currentUser?.role !== "PLATFORM_ADMIN") {
    return (
      <div className="platform-denied">
        <h1>Resource not found.</h1>
        <a href="/app">
          Return to PTM
        </a>
      </div>
    );
  }

  async function handleCreateAgency(event) {
    event.preventDefault();

    const name = newAgency.name.trim();

    if (!name) {
      setError("Agency name is required.");
      return;
    }

    setBusy(true);
    setError("");
    setNotice("");

    try {
      const data = await fetchJson(
        "/api/platform/agencies",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name,
            tcole_agency_number:
              newAgency.tcole_agency_number.trim() ||
              null,
            ori:
              newAgency.ori.trim() ||
              null,
            email_domain:
              newAgency.email_domain.trim() ||
              null,
            email_pattern:
              newAgency.email_pattern ||
              null,
          }),
        }
      );

      setAgencies((current) =>
        [...current, data].sort((a, b) =>
          a.name.localeCompare(b.name)
        )
      );

      setNewAgency({
        name: "",
        tcole_agency_number: "",
        ori: "",
        email_domain: "",
        email_pattern: "",
      });

      setNewAgencyOpen(false);
      setSelectedAgency(data);

      setNotice(
        `${data.name} was created successfully. ` +
        "You can now add agency administrators."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }


  return (
    <div className="platform-shell">
      <header className="topbar platform-topbar">
        <div className="authenticated-brand">
          <img
            src="/ptm-logo.png"
            alt=""
            className="authenticated-brand-logo"
            aria-hidden="true"
          />

          <div className="authenticated-brand-copy">
            <h1>
              Paradigm Training Manager
              <sup className="product-mark">™</sup>
            </h1>

            <div className="authenticated-brand-company">
              by Paradigm Strategic Partners, LLC
            </div>
          </div>
        </div>

        <div className="authenticated-user">
          <div>
            <strong>
              {currentUser?.first_name}{" "}
              {currentUser?.last_name}
            </strong>

            <span>
              Platform Administrator
            </span>
          </div>

          <button
            type="button"
            onClick={onLogout}
          >
            Log Out
          </button>
        </div>
      </header>

      <main className="platform-page">
        <div className="platform-heading">
          <div>
            <span>
              PARADIGM ADMINISTRATION
            </span>

            <h2>
              {selectedAgency
                ? selectedAgency.name
                : "Agency Management"}
            </h2>

            <p>
              {selectedAgency
                ? "Manage this PTM agency and its administrator accounts."
                : "Manage PTM agencies and agency administrator access."}
            </p>
          </div>

          <div className="platform-heading-actions">
            {!selectedAgency && (
              <button
                type="button"
                className="platform-primary-button"
                onClick={() => {
                  setError("");
                  setNotice("");
                  setNewAgencyOpen(true);
                }}
              >
                + Add Agency
              </button>
            )}

            {selectedAgency && (
              <button
                type="button"
                className="platform-secondary-button"
                onClick={() => {
                  setSelectedAgency(null);
                  setError("");
                  setNotice("");
                }}
              >
                ← All Agencies
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="platform-message error">
            {error}
          </div>
        )}

        {notice && (
          <div className="platform-message success">
            {notice}
          </div>
        )}

        {newAgencyOpen && (
          <div
            className="platform-modal-backdrop"
            role="presentation"
            onMouseDown={(event) => {
              if (event.target === event.currentTarget) {
                setNewAgencyOpen(false);
              }
            }}
          >
            <section
              className="platform-create-agency-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="create-agency-title"
            >
              <div className="platform-modal-heading">
                <div>
                  <span>NEW PTM TENANT</span>
                  <h2 id="create-agency-title">
                    Add Agency
                  </h2>
                  <p>
                    Create a new agency tenant. After
                    creation, you can assign one or more
                    agency administrators.
                  </p>
                </div>

                <button
                  type="button"
                  className="platform-modal-close"
                  aria-label="Close"
                  onClick={() =>
                    setNewAgencyOpen(false)
                  }
                >
                  ×
                </button>
              </div>

              <form
                className="platform-agency-form"
                onSubmit={handleCreateAgency}
              >
                <label className="platform-form-wide">
                  <span>Agency Name *</span>
                  <input
                    type="text"
                    required
                    value={newAgency.name}
                    disabled={busy}
                    placeholder="Example Police Department"
                    onChange={(event) =>
                      setNewAgency((current) => ({
                        ...current,
                        name: event.target.value,
                      }))
                    }
                  />
                </label>

                <label>
                  <span>TCOLE Agency Number</span>
                  <input
                    type="text"
                    value={
                      newAgency.tcole_agency_number
                    }
                    disabled={busy}
                    onChange={(event) =>
                      setNewAgency((current) => ({
                        ...current,
                        tcole_agency_number:
                          event.target.value,
                      }))
                    }
                  />
                </label>

                <label>
                  <span>ORI</span>
                  <input
                    type="text"
                    value={newAgency.ori}
                    disabled={busy}
                    onChange={(event) =>
                      setNewAgency((current) => ({
                        ...current,
                        ori: event.target.value,
                      }))
                    }
                  />
                </label>

                <label>
                  <span>Email Domain</span>
                  <input
                    type="text"
                    value={newAgency.email_domain}
                    disabled={busy}
                    placeholder="example.gov"
                    onChange={(event) =>
                      setNewAgency((current) => ({
                        ...current,
                        email_domain:
                          event.target.value,
                      }))
                    }
                  />
                </label>

                <label>
                  <span>Email Pattern</span>
                  <select
                    value={newAgency.email_pattern}
                    disabled={busy}
                    onChange={(event) =>
                      setNewAgency((current) => ({
                        ...current,
                        email_pattern:
                          event.target.value,
                      }))
                    }
                  >
                    <option value="">
                      Not configured
                    </option>
                    <option value="FIRST_INITIAL_LAST">
                      First initial + last name
                    </option>
                    <option value="FIRST_DOT_LAST">
                      First name . last name
                    </option>
                    <option value="FIRST_LAST">
                      First name + last name
                    </option>
                    <option value="LAST_FIRST_INITIAL">
                      Last name + first initial
                    </option>
                  </select>
                </label>

                <div className="platform-modal-actions">
                  <button
                    type="button"
                    className="platform-secondary-button"
                    disabled={busy}
                    onClick={() =>
                      setNewAgencyOpen(false)
                    }
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="platform-primary-button"
                    disabled={busy}
                  >
                    {busy
                      ? "Creating Agency..."
                      : "Create Agency"}
                  </button>
                </div>
              </form>
            </section>
          </div>
        )}

        {!selectedAgency ? (
          <>
            {loading ? (
              <div className="platform-loading">
                Loading agencies...
              </div>
            ) : (
              <section className="platform-panel">
                <div className="platform-table-wrap">
                  <table className="platform-table">
                    <thead>
                      <tr>
                        <th>Agency</th>
                        <th>Status</th>
                        <th>
                          Licensed Employees
                        </th>
                        <th>
                          Administrators
                        </th>
                        <th></th>
                      </tr>
                    </thead>

                    <tbody>
                      {agencies.map((agency) => (
                        <tr key={agency.id}>
                          <td>
                            <strong>
                              {agency.name}
                            </strong>

                            {agency.tcole_agency_number && (
                              <span>
                                TCOLE{" "}
                                {
                                  agency.tcole_agency_number
                                }
                              </span>
                            )}
                          </td>

                          <td>
                            <span
                              className={
                                "platform-status " +
                                agency.status
                              }
                            >
                              {agency.status}
                            </span>
                          </td>

                          <td>
                            {
                              agency.active_employee_count
                            }
                          </td>

                          <td>
                            {
                              agency.active_administrator_count
                            }
                            {" active / "}
                            {
                              agency.administrator_count
                            }
                            {" total"}
                          </td>

                          <td>
                            <button
                              type="button"
                              className="platform-link-button"
                              disabled={busy}
                              onClick={() =>
                                openAgency(
                                  agency.id
                                )
                              }
                            >
                              Manage Agency
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </>
        ) : (
          <>
            <section className="platform-agency-summary">
              <div>
                <span>Status</span>
                <strong>
                  {selectedAgency.status}
                </strong>
              </div>

              <div>
                <span>
                  Active Employees
                </span>
                <strong>
                  {
                    selectedAgency.active_employee_count
                  }
                </strong>
              </div>

              <div>
                <span>
                  Archived Employees
                </span>
                <strong>
                  {
                    selectedAgency.archived_employee_count
                  }
                </strong>
              </div>

              <div>
                <span>
                  Administrators
                </span>
                <strong>
                  {
                    selectedAgency.administrator_count
                  }
                </strong>
              </div>
            </section>

            <section className="platform-panel">
              <div className="platform-panel-heading">
                <div>
                  <h3>
                    Agency Information
                  </h3>

                  <p>
                    Basic tenant configuration.
                  </p>
                </div>

                {!editAgencyOpen && (
                  <button
                    type="button"
                    className="platform-secondary-button"
                    disabled={busy}
                    onClick={beginAgencyEdit}
                  >
                    Edit Agency
                  </button>
                )}
              </div>

              {editAgencyOpen ? (
                <form
                  className="platform-edit-form"
                  onSubmit={handleAgencyUpdate}
                >
                  <label className="platform-form-wide">
                    <span>Agency Name</span>
                    <input
                      required
                      value={editAgency.name}
                      disabled={busy}
                      onChange={(event) =>
                        setEditAgency((current) => ({
                          ...current,
                          name: event.target.value,
                        }))
                      }
                    />
                  </label>

                  <label>
                    <span>TCOLE Agency Number</span>
                    <input
                      value={
                        editAgency.tcole_agency_number
                      }
                      disabled={busy}
                      onChange={(event) =>
                        setEditAgency((current) => ({
                          ...current,
                          tcole_agency_number:
                            event.target.value,
                        }))
                      }
                    />
                  </label>

                  <label>
                    <span>ORI</span>
                    <input
                      value={editAgency.ori}
                      disabled={busy}
                      onChange={(event) =>
                        setEditAgency((current) => ({
                          ...current,
                          ori: event.target.value,
                        }))
                      }
                    />
                  </label>

                  <label>
                    <span>Email Domain</span>
                    <input
                      value={editAgency.email_domain}
                      disabled={busy}
                      onChange={(event) =>
                        setEditAgency((current) => ({
                          ...current,
                          email_domain:
                            event.target.value,
                        }))
                      }
                    />
                  </label>

                  <label>
                    <span>Email Pattern</span>
                    <input
                      value={editAgency.email_pattern}
                      disabled={busy}
                      onChange={(event) =>
                        setEditAgency((current) => ({
                          ...current,
                          email_pattern:
                            event.target.value,
                        }))
                      }
                    />
                  </label>

                  <div className="platform-edit-actions">
                    <button
                      type="button"
                      className="platform-secondary-button"
                      disabled={busy}
                      onClick={() =>
                        setEditAgencyOpen(false)
                      }
                    >
                      Cancel
                    </button>

                    <button
                      type="submit"
                      className="platform-primary-button"
                      disabled={busy}
                    >
                      {busy
                        ? "Saving..."
                        : "Save Changes"}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="platform-agency-details">
                  <div>
                    <span>Agency Name</span>
                    <strong>
                      {selectedAgency.name}
                    </strong>
                  </div>

                  <div>
                    <span>
                      TCOLE Agency Number
                    </span>
                    <strong>
                      {
                        selectedAgency.tcole_agency_number ||
                        "Not configured"
                      }
                    </strong>
                  </div>

                  <div>
                    <span>ORI</span>
                    <strong>
                      {
                        selectedAgency.ori ||
                        "Not configured"
                      }
                    </strong>
                  </div>

                  <div>
                    <span>Email Domain</span>
                    <strong>
                      {
                        selectedAgency.email_domain ||
                        "Not configured"
                      }
                    </strong>
                  </div>

                  <div>
                    <span>Email Pattern</span>
                    <strong>
                      {
                        selectedAgency.email_pattern ||
                        "Not configured"
                      }
                    </strong>
                  </div>
                </div>
              )}
            </section>

            <section className="platform-panel">
              <div className="platform-panel-heading">
                <div>
                  <h3>
                    Agency Administrators
                  </h3>

                  <p>
                    Each administrator has an
                    independent PTM login and
                    access to this agency only.
                  </p>
                </div>

                <button
                  type="button"
                  className="platform-primary-button"
                  onClick={() =>
                    setNewAdminOpen(
                      (current) => !current
                    )
                  }
                >
                  {newAdminOpen
                    ? "Cancel"
                    : "+ Add Administrator"}
                </button>
              </div>

              {newAdminOpen && (
                <form
                  className="platform-admin-form"
                  onSubmit={handleCreateAdmin}
                >
                  <label>
                    <span>First Name</span>
                    <input
                      required
                      value={
                        newAdmin.first_name
                      }
                      disabled={busy}
                      onChange={(event) =>
                        setNewAdmin({
                          ...newAdmin,
                          first_name:
                            event.target.value,
                        })
                      }
                    />
                  </label>

                  <label>
                    <span>Last Name</span>
                    <input
                      required
                      value={
                        newAdmin.last_name
                      }
                      disabled={busy}
                      onChange={(event) =>
                        setNewAdmin({
                          ...newAdmin,
                          last_name:
                            event.target.value,
                        })
                      }
                    />
                  </label>

                  <label>
                    <span>
                      Login Email
                    </span>
                    <input
                      type="email"
                      required
                      value={newAdmin.email}
                      disabled={busy}
                      onChange={(event) =>
                        setNewAdmin({
                          ...newAdmin,
                          email:
                            event.target.value,
                        })
                      }
                    />
                  </label>

                  <div className="platform-invitation-note">
                    PTM will create a secure, one-time
                    invitation link. The administrator
                    will choose their own password when
                    activating the account.
                  </div>

                  <div className="platform-form-actions">
                    <button
                      type="submit"
                      className="platform-primary-button"
                      disabled={busy}
                    >
                      {busy
                        ? "Creating..."
                        : "Create Invitation"}
                    </button>
                  </div>
                </form>
              )}

              {generatedInvitation && (
                <div className="platform-invitation-result">
                  <div>
                    <span>
                      INVITATION LINK
                    </span>

                    <strong>
                      {generatedInvitation.user.first_name}{" "}
                      {generatedInvitation.user.last_name}
                    </strong>

                    <p>
                      Send this link to the administrator
                      using your normal email, text
                      message, or another trusted method.
                      It expires after 72 hours and can
                      only be used once.
                    </p>
                  </div>

                  <div className="platform-invitation-link-row">
                    <input
                      readOnly
                      value={
                        generatedInvitation.url
                      }
                      onFocus={(event) =>
                        event.target.select()
                      }
                    />

                    <button
                      type="button"
                      className="platform-primary-button"
                      onClick={
                        handleCopyInvitation
                      }
                    >
                      Copy Link
                    </button>
                  </div>

                  {invitationCopyNotice && (
                    <div className="platform-invitation-copy-notice">
                      {invitationCopyNotice}
                    </div>
                  )}

                  <button
                    type="button"
                    className="platform-link-button"
                    onClick={() => {
                      setGeneratedInvitation(null);
                      setInvitationCopyNotice("");
                    }}
                  >
                    Dismiss
                  </button>
                </div>
              )}

              <div className="platform-admin-list">
                {selectedAgency.administrators?.map(
                  (user) => (
                    <article
                      className="platform-admin-card"
                      key={user.id}
                    >
                      <div className="platform-admin-identity">
                        <strong>
                          {user.first_name}{" "}
                          {user.last_name}
                        </strong>

                        <span>
                          {user.email}
                        </span>
                      </div>

                      <div className="platform-admin-meta">
                        <span
                          className={
                            "platform-status " +
                            user.status
                          }
                        >
                          {user.status}
                        </span>

                        <span>
                          Last login:{" "}
                          {formatPlatformDate(
                            user.last_login_at
                          )}
                        </span>
                      </div>

                      <div className="platform-admin-actions">
                        <button
                          type="button"
                          className="platform-link-button"
                          disabled={busy}
                          onClick={() =>
                            beginAdminEdit(user)
                          }
                        >
                          Edit
                        </button>

                        {user.status === "pending_invitation" ? (
                          <button
                            type="button"
                            className="platform-link-button"
                            disabled={busy}
                            onClick={() =>
                              handleRegenerateInvitation(
                                user
                              )
                            }
                          >
                            Generate New Link
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="platform-link-button"
                            disabled={busy}
                            onClick={() => {
                              setResetUser(user);
                              setEditAdminUser(null);
                              setResetPassword("");
                              setResetPasswordConfirm("");
                              setError("");
                            }}
                          >
                            Reset Password
                          </button>
                        )}

                        <button
                          type="button"
                          className="platform-link-button"
                          disabled={busy}
                          onClick={() =>
                            handleAdminStatus(
                              user,
                              user.status === "active"
                                ? "inactive"
                                : "active"
                            )
                          }
                        >
                          {user.status === "active"
                            ? "Deactivate"
                            : "Activate"}
                        </button>
                      </div>
                    </article>
                  )
                )}
              </div>
            </section>

            {editAdminUser && (
              <section className="platform-panel">
                <div className="platform-panel-heading">
                  <div>
                    <h3>
                      Edit Administrator
                    </h3>

                    <p>
                      Update the administrator's
                      name or login email.
                    </p>
                  </div>

                  <button
                    type="button"
                    className="platform-secondary-button"
                    disabled={busy}
                    onClick={() =>
                      setEditAdminUser(null)
                    }
                  >
                    Cancel
                  </button>
                </div>

                <form
                  className="platform-admin-form"
                  onSubmit={handleAdminUpdate}
                >
                  <label>
                    <span>First Name</span>
                    <input
                      required
                      value={editAdmin.first_name}
                      disabled={busy}
                      onChange={(event) =>
                        setEditAdmin((current) => ({
                          ...current,
                          first_name:
                            event.target.value,
                        }))
                      }
                    />
                  </label>

                  <label>
                    <span>Last Name</span>
                    <input
                      required
                      value={editAdmin.last_name}
                      disabled={busy}
                      onChange={(event) =>
                        setEditAdmin((current) => ({
                          ...current,
                          last_name:
                            event.target.value,
                        }))
                      }
                    />
                  </label>

                  <label className="platform-form-wide">
                    <span>Login Email</span>
                    <input
                      type="email"
                      required
                      value={editAdmin.email}
                      disabled={busy}
                      onChange={(event) =>
                        setEditAdmin((current) => ({
                          ...current,
                          email:
                            event.target.value,
                        }))
                      }
                    />
                  </label>

                  <div className="platform-form-actions platform-form-wide">
                    <button
                      type="submit"
                      className="platform-primary-button"
                      disabled={busy}
                    >
                      {busy
                        ? "Saving..."
                        : "Save Administrator"}
                    </button>
                  </div>
                </form>
              </section>
            )}

            {resetUser && (
              <section className="platform-panel platform-reset-panel">
                <div className="platform-panel-heading">
                  <div>
                    <h3>
                      Reset Password
                    </h3>

                    <p>
                      Set a new password for{" "}
                      {resetUser.first_name}{" "}
                      {resetUser.last_name}.
                    </p>
                  </div>

                  <button
                    type="button"
                    className="platform-secondary-button"
                    onClick={() =>
                      setResetUser(null)
                    }
                  >
                    Cancel
                  </button>
                </div>

                <form
                  className="platform-reset-form"
                  onSubmit={
                    handlePasswordReset
                  }
                >
                  <label>
                    <span>
                      New Password
                    </span>

                    <input
                      type="password"
                      required
                      minLength="12"
                      value={resetPassword}
                      disabled={busy}
                      onChange={(event) =>
                        setResetPassword(
                          event.target.value
                        )
                      }
                    />
                  </label>

                  <label>
                    <span>
                      Confirm Password
                    </span>

                    <input
                      type="password"
                      required
                      minLength="12"
                      value={
                        resetPasswordConfirm
                      }
                      disabled={busy}
                      onChange={(event) =>
                        setResetPasswordConfirm(
                          event.target.value
                        )
                      }
                    />
                  </label>

                  <button
                    type="submit"
                    className="platform-primary-button"
                    disabled={busy}
                  >
                    {busy
                      ? "Resetting..."
                      : "Reset Password"}
                  </button>
                </form>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}


function PlatformAuthenticatedApplication() {
  const [authState, setAuthState] = useState({
    loading: true,
    user: null,
  });

  useEffect(() => {
    let active = true;

    async function loadCurrentUser() {
      try {
        const response = await fetch(
          "/api/auth/me",
          {
            credentials: "same-origin",
          }
        );

        if (response.status === 401) {
          window.location.replace("/login");
          return;
        }

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error ||
              "Unable to verify your PTM session."
          );
        }

        if (
          data.user?.role !==
          "PLATFORM_ADMIN"
        ) {
          window.location.replace("/app");
          return;
        }

        if (active) {
          setAuthState({
            loading: false,
            user: data.user,
          });
        }
      } catch {
        if (active) {
          window.location.replace("/login");
        }
      }
    }

    loadCurrentUser();

    return () => {
      active = false;
    };
  }, []);

  async function handleLogout() {
    try {
      await fetch(
        "/api/auth/logout",
        {
          method: "POST",
          credentials: "same-origin",
        }
      );
    } finally {
      window.location.replace("/login");
    }
  }

  if (authState.loading) {
    return (
      <div className="auth-loading">
        <div>
          <strong>
            Paradigm Training Manager
            <sup className="product-mark">™</sup>
          </strong>

          <span>
            Loading platform administration...
          </span>
        </div>
      </div>
    );
  }

  return (
    <PlatformAdministration
      currentUser={authState.user}
      onLogout={handleLogout}
    />
  );
}



function PublicLandingPage() {
  const openApplication = () => {
    window.location.href = "/login";
  };

  return (
    <div className="public-site">
      <header className="public-header">
        <div className="public-header-inner">
          <a
            href="/"
            className="public-brand"
            aria-label="Paradigm Training Manager home"
          >
            <img
              src="/ptm-logo.png"
              alt=""
              className="public-brand-logo"
              aria-hidden="true"
            />

            <span className="public-brand-copy">
              <span className="public-brand-product">
                Paradigm Training Manager
                <sup className="product-mark">™</sup>
              </span>

              <span className="public-brand-company">
                by Paradigm Strategic Partners, LLC
              </span>
            </span>
          </a>

          <nav
            className="public-nav"
            aria-label="Primary navigation"
          >
            <a href="#how-it-works">
              How It Works
            </a>

            <a href="#why-ptm">
              Why PTM
            </a>

            <a href="#pricing">
              Pricing
            </a>

            <a href="#faq">
              FAQ
            </a>

            <button
              type="button"
              className="public-login-button"
              onClick={openApplication}
            >
              Agency Login
            </button>

            <a
              href="https://paradigm-strategic-partners-llc.odoo.com/contact-request-ptm"
              className="public-demo-button"
            >
              Request a Demo
            </a>
          </nav>
        </div>
      </header>

      <main>
        <section className="public-hero">
          <div className="public-hero-inner">
            <div className="public-hero-copy">
              <div className="public-eyebrow">
                TCOLE Compliance Management
              </div>

              <h1>
                Know who's compliant.
                <br />
                Know who isn't.
                <br />
                <span>Know exactly why.</span>
              </h1>

              <p className="public-hero-lead">
                TCOLE compliance management built for
                Texas law enforcement.
              </p>

              <p className="public-hero-description">
                Import your agency's TCOLE records and PTM
                automatically evaluates applicable training
                requirements, identifies deficiencies,
                tracks deadlines, and shows you exactly
                where your agency stands.
              </p>

              <div className="public-hero-actions">
                <a
                  href="#how-it-works"
                  className="public-primary-cta"
                >
                  See How PTM Works
                </a>

                <a
                  href="https://paradigm-strategic-partners-llc.odoo.com/contact-request-ptm"
                  className="public-secondary-cta"
                >
                  Request a Demo
                </a>
              </div>

              <div className="public-outcome">
                Compliance is the outcome.
              </div>
            </div>

            <div
              className="public-dashboard-preview"
              aria-label="Paradigm Training Manager dashboard preview"
            >
              <div className="public-preview-topbar">
                <div>
                  <span>
                    Executive Compliance Dashboard
                  </span>
                  <strong>
                    Sample Agency
                  </strong>
                </div>

                <span className="public-preview-period">
                  Unit 1
                </span>
              </div>

              <div className="public-preview-grid">
                <div>
                  <span>Licensed Employees</span>
                  <strong>47</strong>
                </div>

                <div className="public-preview-good">
                  <span>Compliant</span>
                  <strong>43</strong>
                </div>

                <div className="public-preview-alert">
                  <span>Attention Required</span>
                  <strong>2</strong>
                </div>

                <div className="public-preview-due">
                  <span>Upcoming Requirements</span>
                  <strong>2</strong>
                </div>
              </div>

              <div className="public-preview-list">
                <div>
                  <span className="public-preview-status good">
                    Compliant
                  </span>
                  <div>
                    <strong>Jordan Smith</strong>
                    <span>
                      Peace Officer · Master
                    </span>
                  </div>
                  <span>None Due</span>
                </div>

                <div>
                  <span className="public-preview-status due">
                    Training Due
                  </span>
                  <div>
                    <strong>Alex Martinez</strong>
                    <span>
                      Peace Officer · Advanced
                    </span>
                  </div>
                  <span>8/31/2027</span>
                </div>

                <div>
                  <span className="public-preview-status good">
                    Compliant
                  </span>
                  <div>
                    <strong>Taylor Morgan</strong>
                    <span>
                      Telecommunicator · Master
                    </span>
                  </div>
                  <span>None Due</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section
          className="public-foundation-section"
          id="why-ptm"
        >
          <div className="public-section-inner">
            <div className="public-section-heading">
              <span>THE CURRENT PROCESS</span>
              <h2>
                How much time are you spending just
                figuring out who's compliant?
              </h2>

              <p>
                You're already paying for TCOLE compliance
                management. You're paying for it in staff
                time.
              </p>
            </div>

            <div className="public-pain-grid">
              <article>
                <span>01</span>
                <h3>Reviewing TCOLE reports</h3>
                <p>
                  Sorting through individual training
                  histories and course records.
                </p>
              </article>

              <article>
                <span>02</span>
                <h3>Checking requirements</h3>
                <p>
                  Units, cycles, legislative mandates,
                  certification levels and assignments.
                </p>
              </article>

              <article>
                <span>03</span>
                <h3>Tracking spreadsheets</h3>
                <p>
                  Manually maintaining who's completed what
                  and what's still required.
                </p>
              </article>

              <article>
                <span>04</span>
                <h3>Following up</h3>
                <p>
                  Finding deficiencies, notifying employees,
                  and checking everything again later.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section
          className="public-process-section"
          id="how-it-works"
        >
          <div className="public-section-inner">
            <div className="public-section-heading centered">
              <span>HOW PTM WORKS</span>
              <h2>
                From TCOLE reports to answers.
              </h2>
            </div>

            <div className="public-process-grid">
              <article>
                <div>1</div>
                <h3>Import</h3>
                <p>
                  Download the reports you already use from
                  TCOLE and import them into PTM.
                </p>
              </article>

              <span className="public-process-arrow">
                →
              </span>

              <article>
                <div>2</div>
                <h3>Analyze</h3>
                <p>
                  PTM evaluates each employee against the
                  requirements that apply to them.
                </p>
              </article>

              <span className="public-process-arrow">
                →
              </span>

              <article>
                <div>3</div>
                <h3>Know</h3>
                <p>
                  See who's compliant, what's missing,
                  what's due, and what needs your attention.
                </p>
              </article>
            </div>
          </div>
        </section>


        <section className="public-complexity-section">
          <div className="public-section-inner">
            <div className="public-section-heading">
              <span>WHY IT GETS COMPLICATED</span>
              <h2>
                TCOLE compliance isn't just counting
                training hours.
              </h2>
              <p>
                Different employees can have different
                requirements based on license type,
                training period, certification level,
                assignments, service time, and specific
                mandated courses.
              </p>
            </div>

            <div className="public-complexity-grid">
              <article>
                <span>License Type</span>
                <strong>
                  Peace Officer · County Jailer ·
                  Telecommunicator
                </strong>
              </article>

              <article>
                <span>Training Period</span>
                <strong>
                  2-Year Unit · 4-Year Cycle
                </strong>
              </article>

              <article>
                <span>Certification</span>
                <strong>
                  Basic · Intermediate · Advanced · Master
                </strong>
              </article>

              <article>
                <span>Individual Requirements</span>
                <strong>
                  Courses · Hours · Service Time ·
                  Equivalencies
                </strong>
              </article>

              <article>
                <span>Assignments</span>
                <strong>
                  Supervisor · PIO · Chief · Other Roles
                </strong>
              </article>

              <article>
                <span>Legislative Requirements</span>
                <strong>
                  ALERRT · Law Update · Protecting Your
                  License · Other Mandates
                </strong>
              </article>
            </div>

            <div className="public-complexity-callout">
              <strong>
                PTM brings all of it together automatically.
              </strong>
            </div>
          </div>
        </section>

        <section className="public-product-section">
          <div className="public-section-inner">
            <div className="public-section-heading centered">
              <span>WHAT CHANGES WITH PTM</span>
              <h2>
                Stop comparing records manually.
              </h2>
              <p>
                PTM turns training records into an
                actionable compliance picture for both the
                agency and the individual employee.
              </p>
            </div>

            <div className="public-product-grid">
              <article>
                <div className="public-product-card-heading">
                  <span>Executive Dashboard</span>
                  <strong>Agency-wide visibility</strong>
                </div>

                <div className="public-mini-dashboard">
                  <div>
                    <span>Active Employees</span>
                    <strong>47</strong>
                  </div>
                  <div>
                    <span>Compliant</span>
                    <strong>43</strong>
                  </div>
                  <div>
                    <span>Training Due</span>
                    <strong>4</strong>
                  </div>
                </div>

                <p>
                  See the current compliance posture of the
                  agency at a glance.
                </p>
              </article>

              <article>
                <div className="public-product-card-heading">
                  <span>Individual Compliance</span>
                  <strong>Know exactly what's missing</strong>
                </div>

                <div className="public-mini-requirements">
                  <div>
                    <span className="good">Complete</span>
                    <strong>Current Unit Hours</strong>
                  </div>
                  <div>
                    <span className="due">Due</span>
                    <strong>
                      State and Federal Law Update
                    </strong>
                  </div>
                  <div>
                    <span className="due">Due</span>
                    <strong>
                      8 additional ALERRT hours
                    </strong>
                  </div>
                </div>

                <p>
                  See exactly which requirements remain and
                  when they are due.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section className="public-roi-section">
          <div className="public-section-inner">
            <div className="public-roi-copy">
              <span>THE FINANCIAL CASE</span>
              <h2>
                What is your current process costing you?
              </h2>
              <p>
                PTM does not need to eliminate a position to
                create value. The real benefit is staff
                capacity returned to the agency.
              </p>
            </div>

            <RoiCalculator />
          </div>
        </section>

        <section className="public-capacity-section">
          <div className="public-section-inner">
            <div className="public-section-heading centered">
              <span>GIVE THE TIME BACK</span>
              <h2>
                What could your staff do with that time?
              </h2>
              <p>
                Training coordinators were not hired to
                spend their careers maintaining
                spreadsheets.
              </p>
            </div>

            <div className="public-capacity-grid">
              <article>Finding better training opportunities</article>
              <article>Scheduling and coordinating training</article>
              <article>Conducting instruction</article>
              <article>Accreditation and policy work</article>
              <article>Officer development</article>
              <article>Other agency priorities</article>
            </div>

            <div className="public-capacity-callout">
              PTM doesn't just save time. It gives your
              people time back.
            </div>
          </div>
        </section>

        <section className="public-feature-section">
          <div className="public-section-inner">
            <div className="public-section-heading">
              <span>MORE VISIBILITY, LESS WORK</span>
              <h2>
                Save time without sacrificing oversight.
              </h2>
            </div>

            <div className="public-feature-grid">
              <article>
                <h3>Executive Dashboard</h3>
                <p>
                  See agency-wide compliance status,
                  deficiencies, and priorities.
                </p>
              </article>

              <article>
                <h3>Individual Compliance</h3>
                <p>
                  Know exactly what each employee has
                  completed and what remains.
                </p>
              </article>

              <article>
                <h3>Upcoming Requirements</h3>
                <p>
                  Identify issues before the deadline
                  arrives.
                </p>
              </article>

              <article>
                <h3>Compliance Communications</h3>
                <p>
                  Prepare individualized updates for
                  employees and open them in the agency's
                  default email application.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section className="public-not-lms-section">
          <div className="public-section-inner">
            <div className="public-not-lms-card">
              <span>NOT ANOTHER LMS</span>
              <h2>
                You don't need another learning management
                system.
              </h2>
              <h3>Neither do we.</h3>

              <p>
                PTM is not designed to sell courses, host
                videos, administer tests, manage classrooms,
                or replace the training resources your
                agency already uses.
              </p>

              <div className="public-not-lms-question">
                <span>It answers a different question:</span>
                <strong>Is everyone compliant?</strong>
                <span>And if the answer is no:</span>
                <strong>Why not?</strong>
              </div>

              <p className="public-not-lms-close">
                Use the training resources you already use.
                Let PTM manage the compliance.
              </p>
            </div>
          </div>
        </section>

        <section className="public-trust-section">
          <div className="public-section-inner">
            <div className="public-section-heading centered">
              <span>BUILT FOR THE JOB</span>
              <h2>
                Built specifically for Texas law
                enforcement.
              </h2>
              <p>
                PTM is not generic HR software with a
                compliance label added to it.
              </p>
            </div>

            <div className="public-trust-grid">
              <article>TCOLE-specific rules</article>
              <article>Published course equivalencies</article>
              <article>
                Peace officers, jailers, and
                telecommunicators
              </article>
              <article>
                Assignment-specific requirements
              </article>
              <article>
                2-year units and 4-year cycles
              </article>
              <article>
                Proficiency certification eligibility
              </article>
              <article>
                Explainable compliance determinations
              </article>
              <article>
                Defined, data-driven compliance rules
              </article>
            </div>
          </div>
        </section>

        <section className="public-pricing-section" id="pricing">
          <div className="public-section-inner">
            <div className="public-section-heading centered">
              <span>STRAIGHTFORWARD PRICING</span>
              <h2>
                Compliance shouldn't require a budget
                meeting.
              </h2>
              <p>
                Annual pricing based on the number of
                licensed employees in the agency.
              </p>
            </div>

            <div className="public-pricing-grid">
              <PricingCard
                name="Starter"
                range="1–15 licensed employees"
                logins="1 agency login included"
                price="$399/year"
              />
              <PricingCard
                name="Small"
                range="16–35 licensed employees"
                logins="1 agency login included"
                price="$749/year"
              />
              <PricingCard
                name="Medium"
                range="36–75 licensed employees"
                logins="2 agency logins included"
                price="$1,199/year"
                featured
              />
              <PricingCard
                name="Large"
                range="76–150 licensed employees"
                logins="3 agency logins included"
                price="$1,999/year"
              />
              <PricingCard
                name="Enterprise"
                range="151–300 licensed employees"
                logins="4 agency logins included"
                price="$2,999/year"
              />
              <PricingCard
                name="Enterprise Plus"
                range="301+ licensed employees"
                logins="Custom agency access"
                price="Custom"
              />
            </div>

            <div className="public-pricing-note">
              Additional agency administrator logins may be
              added separately. Pilot terms may differ from
              commercial pricing.
            </div>
          </div>
        </section>

        <section className="public-faq-section" id="faq">
          <div className="public-section-inner">
            <div className="public-section-heading">
              <span>COMMON QUESTIONS</span>
              <h2>Frequently asked questions.</h2>
            </div>

            <div className="public-faq-list">
              <FaqItem
                question="Does PTM replace TCOLE?"
                answer="No. PTM uses agency-imported TCOLE records to help the agency evaluate and manage compliance."
              />
              <FaqItem
                question="Is PTM an LMS?"
                answer="No. PTM is a compliance management platform, not a learning management system."
              />
              <FaqItem
                question="Do we have to manually enter all of our employees' training?"
                answer="No. PTM is designed around importing the official TCOLE reports the agency already uses."
              />
              <FaqItem
                question="Can PTM tell me why an employee is not compliant?"
                answer="Yes. PTM identifies the applicable requirement and shows what remains outstanding."
              />
              <FaqItem
                question="Does PTM support peace officers, jailers, and telecommunicators?"
                answer="Yes. PTM evaluates supported TCOLE requirements for each applicable license track."
              />
              <FaqItem
                question="Can one agency see another agency's information?"
                answer="No. PTM is being built as a multi-tenant system with agency data isolated by design."
              />
            </div>
          </div>
        </section>

        <section
          className="public-pilot-cta"
          id="request-demo"
        >
          <div className="public-section-inner">
            <div>
              <span>PARADIGM TRAINING MANAGER™</span>
              <h2>
                Better compliance visibility.
                <br />
                Less administrative work.
              </h2>
              <p>
                The complete public site is being prepared
                for the trusted-user pilot.
              </p>
            </div>

            <button
              type="button"
              onClick={openApplication}
            >
              Agency Login
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}


function InvitationActivationPage() {
  const params = new URLSearchParams(
    window.location.search
  );

  const token = params.get("token") || "";

  const [state, setState] = useState({
    loading: true,
    invitation: null,
    error: "",
  });

  const [password, setPassword] =
    useState("");

  const [passwordConfirm, setPasswordConfirm] =
    useState("");

  const [busy, setBusy] =
    useState(false);

  const [activated, setActivated] =
    useState(false);

  useEffect(() => {
    let active = true;

    async function loadInvitation() {
      if (!token) {
        setState({
          loading: false,
          invitation: null,
          error:
            "This invitation link is invalid.",
        });
        return;
      }

      try {
        const response = await fetch(
          `/api/auth/invitation?token=${encodeURIComponent(token)}`
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error ||
              "Unable to validate this invitation."
          );
        }

        if (active) {
          setState({
            loading: false,
            invitation: data,
            error: "",
          });
        }
      } catch (err) {
        if (active) {
          setState({
            loading: false,
            invitation: null,
            error:
              err.message ||
              "Unable to validate this invitation.",
          });
        }
      }
    }

    loadInvitation();

    return () => {
      active = false;
    };
  }, [token]);

  async function handleActivation(event) {
    event.preventDefault();

    setState((current) => ({
      ...current,
      error: "",
    }));

    if (password.length < 12) {
      setState((current) => ({
        ...current,
        error:
          "Password must be at least 12 characters.",
      }));
      return;
    }

    if (password !== passwordConfirm) {
      setState((current) => ({
        ...current,
        error:
          "Password and confirmation do not match.",
      }));
      return;
    }

    setBusy(true);

    try {
      const response = await fetch(
        "/api/auth/activate-invitation",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            token,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to activate your account."
        );
      }

      setActivated(true);
      setPassword("");
      setPasswordConfirm("");
    } catch (err) {
      setState((current) => ({
        ...current,
        error:
          err.message ||
          "Unable to activate your account.",
      }));
    } finally {
      setBusy(false);
    }
  }

  if (state.loading) {
    return (
      <div className="activation-page">
        <div className="activation-card">
          <strong>
            Paradigm Training Manager
            <sup className="product-mark">™</sup>
          </strong>

          <p>
            Validating your invitation...
          </p>
        </div>
      </div>
    );
  }

  if (activated) {
    return (
      <div className="activation-page">
        <section className="activation-card">
          <div className="activation-kicker">
            ACCOUNT ACTIVATED
          </div>

          <h1>
            Your PTM account is ready.
          </h1>

          <p>
            Your password has been created
            successfully. You can now sign in.
          </p>

          <a
            href="/login"
            className="activation-primary-link"
          >
            Continue to Sign In
          </a>
        </section>
      </div>
    );
  }

  if (state.error && !state.invitation) {
    return (
      <div className="activation-page">
        <section className="activation-card">
          <div className="activation-kicker">
            INVITATION
          </div>

          <h1>
            Unable to activate account
          </h1>

          <div className="activation-message error">
            {state.error}
          </div>

          <p>
            Ask your PTM administrator to
            generate a new invitation link.
          </p>

          <a href="/login">
            Return to Sign In
          </a>
        </section>
      </div>
    );
  }

  return (
    <div className="activation-page">
      <section className="activation-card">
        <div className="activation-kicker">
          PTM ACCOUNT INVITATION
        </div>

        <h1>
          Create your password
        </h1>

        <p>
          You have been invited to access
          Paradigm Training Manager for{" "}
          <strong>
            {state.invitation?.agency}
          </strong>.
        </p>

        <div className="activation-identity">
          <strong>
            {state.invitation?.first_name}{" "}
            {state.invitation?.last_name}
          </strong>

          <span>
            {state.invitation?.email}
          </span>
        </div>

        {state.error && (
          <div className="activation-message error">
            {state.error}
          </div>
        )}

        <form
          onSubmit={handleActivation}
          className="activation-form"
        >
          <label>
            <span>Password</span>

            <input
              type="password"
              required
              minLength={12}
              autoComplete="new-password"
              value={password}
              disabled={busy}
              onChange={(event) =>
                setPassword(
                  event.target.value
                )
              }
            />

            <small>
              Minimum 12 characters.
            </small>
          </label>

          <label>
            <span>
              Confirm Password
            </span>

            <input
              type="password"
              required
              minLength={12}
              autoComplete="new-password"
              value={passwordConfirm}
              disabled={busy}
              onChange={(event) =>
                setPasswordConfirm(
                  event.target.value
                )
              }
            />
          </label>

          <button
            type="submit"
            disabled={busy}
          >
            {busy
              ? "Activating..."
              : "Activate Account"}
          </button>
        </form>
      </section>
    </div>
  );
}


function App() {
  const path = window.location.pathname;

  const loginPath =
    path === "/login" ||
    path.startsWith("/login/");

  const activationPath =
    path === "/activate";

  const platformPath =
    path === "/platform" ||
    path.startsWith("/platform/");

  const applicationPath =
    path === "/app" ||
    path.startsWith("/app/");

  return (
    <>
      {loginPath ? (
        <LoginPage />
      ) : activationPath ? (
        <InvitationActivationPage />
      ) : platformPath ? (
        <PlatformAuthenticatedApplication />
      ) : applicationPath ? (
        <AuthenticatedApplication />
      ) : (
        <PublicLandingPage />
      )}

      <ProductFooter />
    </>
  );
}


export default App;
