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

function AssignmentRow({
  assignment,
  onActivate,
  onEnd,
  busy,
}) {
  return (
    <div className="assignment-row">
      <div>
        <div className="assignment-name">
          {assignment.assignment_name}
        </div>

        <div className="assignment-meta">
          {assignment.active
            ? `Active since ${assignment.effective_date}`
            : "Not active"}
        </div>
      </div>

      <button
        type="button"
        className={
          assignment.active
            ? "assignment-button end"
            : "assignment-button activate"
        }
        disabled={busy}
        onClick={() =>
          assignment.active
            ? onEnd(assignment)
            : onActivate(assignment)
        }
      >
        {assignment.active ? "Turn Off" : "Turn On"}
      </button>
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

function EmployeeComplianceCard({ employee }) {
  const name = [
    employee.first_name,
    employee.middle_name,
    employee.last_name,
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

function App() {
  const [agency, setAgency] = useState(null);
  const [officers, setOfficers] = useState([]);
  const [selectedOfficerId, setSelectedOfficerId] = useState("");

  const [dashboard, setDashboard] = useState(null);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardFilter, setDashboardFilter] = useState("ALL");
  const [certificateFilter, setCertificateFilter] = useState("ALL");
  const [dashboardSearch, setDashboardSearch] = useState("");
  const [assignmentSummary, setAssignmentSummary] = useState(null);
  const [credentialVerifications, setCredentialVerifications] = useState([]);

  const [awardsFile, setAwardsFile] = useState(null);
  const [coursesFile, setCoursesFile] = useState(null);
  const [cycleFile, setCycleFile] = useState(null);

  const [loadingAgency, setLoadingAgency] = useState(true);
  const [loadingAssignments, setLoadingAssignments] = useState(false);
  const [assignmentBusy, setAssignmentBusy] = useState(false);
  const [credentialBusy, setCredentialBusy] = useState(false);
  const [importing, setImporting] = useState(false);

  const [error, setError] = useState("");
  const [assignmentError, setAssignmentError] = useState("");
  const [credentialError, setCredentialError] = useState("");
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

  async function loadOfficers(agencyId) {
    const response = await fetch(
      `/api/agencies/${agencyId}/officers`
    );

    if (!response.ok) {
      throw new Error("Unable to load officers.");
    }

    const data = await response.json();
    setOfficers(data);
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

        await Promise.all([
          loadOfficers(selectedAgency.id),
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

      setLoadingAssignments(true);
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
      } finally {
        setLoadingAssignments(false);
      }
    }

    loadAssignments();
  }, [agency, selectedOfficerId]);

  const ready =
    Boolean(agency) &&
    Boolean(awardsFile) &&
    Boolean(coursesFile) &&
    Boolean(cycleFile) &&
    !importing;

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
        loadOfficers(agency.id),
        loadDashboard(agency.id),
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
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

      await refreshAssignments();
    } catch (err) {
      setAssignmentError(err.message);
    } finally {
      setAssignmentBusy(false);
    }
  }

  async function handleEnd(assignment) {
    const endDate = window.prompt(
      `End date for ${assignment.assignment_name} (YYYY-MM-DD):`
    );

    if (!endDate) {
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
            end_date: endDate,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Unable to end assignment."
        );
      }

      await refreshAssignments();
    } catch (err) {
      setAssignmentError(err.message);
    } finally {
      setAssignmentBusy(false);
    }
  }

  const primaryAssignmentTypes =
    assignmentSummary?.assignment_types.filter((item) =>
      [
        "POLICE_CHIEF",
        "SUPERVISOR",
        "PUBLIC_INFORMATION_OFFICER",
      ].includes(item.assignment_type)
    ) || [];

  const pioAssignment =
    assignmentSummary?.assignment_types.find(
      (item) =>
        item.assignment_type ===
        "PUBLIC_INFORMATION_OFFICER"
    );

  const activeTdemVerification =
    credentialVerifications.find(
      (item) =>
        item.credential_type ===
          "TDEM_PIO_CERTIFICATION" &&
        item.active
    );

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

        <div className="version">v0.2.10</div>
      </header>

      <main className="page">
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
            Upload the three official TCOLE reports for your agency.
            PTM will reconcile personnel, awards, training history,
            and actual credited training hours.
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
                  PTM reconciled all three TCOLE reports.
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

        <section className="assignments-panel">
          <div className="section-heading">
            <div>
              <h2>Officer Assignments</h2>
              <p>
                Agency-managed assignments control additional
                TCOLE compliance rules.
              </p>
            </div>
          </div>

          <div className="officer-selector">
            <label htmlFor="officer-select">
              Officer
            </label>

            <select
              id="officer-select"
              value={selectedOfficerId}
              onChange={(event) =>
                setSelectedOfficerId(event.target.value)
              }
            >
              <option value="">
                Select an officer
              </option>

              {officers.map((officer) => (
                <option
                  key={officer.id}
                  value={officer.id}
                >
                  {officer.name} | PID {officer.tcole_pid}
                </option>
              ))}
            </select>
          </div>

          {assignmentError && (
            <div className="message error-message">
              {assignmentError}
            </div>
          )}

          {selectedOfficerId && loadingAssignments && (
            <div className="assignment-loading">
              Loading assignments...
            </div>
          )}

          {selectedOfficerId &&
            !loadingAssignments &&
            assignmentSummary && (
              <div className="assignment-list">
                {primaryAssignmentTypes.map((assignment) => (
                  <AssignmentRow
                    key={assignment.assignment_type}
                    assignment={assignment}
                    onActivate={handleActivate}
                    onEnd={handleEnd}
                    busy={assignmentBusy}
                  />
                ))}
              </div>
            )}

          {selectedOfficerId &&
            pioAssignment?.active && (
              <div className="credential-panel">
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
                      activeTdemVerification
                        ? "credential-status verified"
                        : "credential-status unverified"
                    }
                  >
                    {activeTdemVerification
                      ? "Verified"
                      : "Not Verified"}
                  </span>
                </div>

                {credentialError && (
                  <div className="message error-message">
                    {credentialError}
                  </div>
                )}

                {activeTdemVerification ? (
                  <div className="credential-details">
                    <div>
                      <span>Effective Date</span>
                      <strong>
                        {activeTdemVerification.effective_date ||
                          "Not recorded"}
                      </strong>
                    </div>

                    <div>
                      <span>Verified By</span>
                      <strong>
                        {activeTdemVerification.verified_by ||
                          "Not recorded"}
                      </strong>
                    </div>

                    <div>
                      <span>Reference</span>
                      <strong>
                        {activeTdemVerification.reference ||
                          "Not recorded"}
                      </strong>
                    </div>

                    <button
                      type="button"
                      className="credential-button revoke"
                      disabled={credentialBusy}
                      onClick={handleRevokeTdem}
                    >
                      {credentialBusy
                        ? "Working..."
                        : "Revoke Verification"}
                    </button>
                  </div>
                ) : (
                  <div className="credential-unverified">
                    <p>
                      PTM has no active agency verification of this
                      officer's TDEM PIO certification.
                    </p>

                    <button
                      type="button"
                      className="credential-button verify"
                      disabled={credentialBusy}
                      onClick={handleVerifyTdem}
                    >
                      {credentialBusy
                        ? "Working..."
                        : "Verify Certification"}
                    </button>
                  </div>
                )}
              </div>
            )}
        </section>
      </main>
    </div>
  );
}

export default App;
