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
              {employee.highest_certificate ||
                "No proficiency certificate"}
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
    displayPathway?.type === "SERVICE_TRAINING"
      ? displayPathway.service_years
      : null;

  const trainingRequirement =
    displayPathway?.type === "SERVICE_TRAINING"
      ? displayPathway.training_hours
      : null;

  const serviceShort =
    bestPathway?.type === "SERVICE_TRAINING"
      ? Number(bestPathway.service_years_short || 0)
      : 0;

  const trainingShort =
    bestPathway?.type === "SERVICE_TRAINING"
      ? Number(bestPathway.training_hours_short || 0)
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

        <div
          className={
            trainingShort > 0
              ? "proficiency-fact deficient"
              : trainingRequirement != null
                ? "proficiency-fact satisfied"
                : "proficiency-fact"
          }
        >
          <span>TCOLE Training Hours</span>

          <strong>
            {advancement.training_hours != null
              ? trainingRequirement != null
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

          {trainingRequirement != null && (
            <small>
              {trainingShort > 0
                ? `${trainingShort.toLocaleString()} hours short`
                : "✓ Training requirement met"}
            </small>
          )}
        </div>

        <div className="proficiency-fact">
          <span>Education</span>
          <strong>
            {advancement.education_level ||
              "Not reported"}
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
        </div>

        <div className="qualification-block">
          <div className="qualification-heading">
            <div>
              <strong>
                Qualifying Military Service
              </strong>
              <span>
                Defaults to no qualifying military
                service. Turn this on only when military
                service applies to the officer.
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
          {workspace.proficiency_advancement
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

          {workspace.proficiency_advancement
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

          {workspace.proficiency_advancement
            ?.peace_officer &&
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
        </div>
      </div>

      <div className="workspace-hero">
        <div>
          <div className="dashboard-kicker">
            Employee Compliance & Training Detail
          </div>

          <div className="workspace-name-row">
            <h2>{name}</h2>
            <WorkspaceStatus
              status={workspace.overall_status}
            />
          </div>

          <div className="workspace-identity">
            <span>PID {officer.tcole_pid}</span>
            <span>•</span>
            <span>
              {officer.highest_certificate ||
                "No proficiency certificate"}
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

            <button
              type="button"
              className="workspace-email-edit"
              onClick={onEditEmail}
            >
              Edit Email
            </button>
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

function App() {
  const [agency, setAgency] = useState(null);
  const [selectedOfficerId, setSelectedOfficerId] = useState("");
  const [emailSettingsOpen, setEmailSettingsOpen] = useState(false);
  const [emailDomain, setEmailDomain] = useState("");
  const [emailPattern, setEmailPattern] = useState("");
  const [emailSettingsBusy, setEmailSettingsBusy] = useState(false);
  const [emailSettingsError, setEmailSettingsError] = useState("");

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

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand-kicker">
            Paradigm Strategic Partners
          </div>
          <h1>Paradigm Training Manager</h1>
        </div>

        <div className="version">v0.2.11</div>
      </header>

      <main className="page">
        {workspaceOpen ? (
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
              handleSaveQualificationFacts
            }
            onActivateAssignment={handleActivate}
            onEndAssignment={handleEnd}
            onVerifyTdem={handleVerifyTdem}
            onRevokeTdem={handleRevokeTdem}
            onEditEmail={handleEditEmployeeEmail}
            onEmailEmployee={handleEmailEmployee}
          />
        ) : (
          <>
        <section className="dashboard-section">
          <div className="dashboard-heading">
            <div>
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
            </div>

            <div className="dashboard-header-actions">
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

export default App;
