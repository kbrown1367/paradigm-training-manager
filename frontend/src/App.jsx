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

function App() {
  const [agency, setAgency] = useState(null);
  const [officers, setOfficers] = useState([]);
  const [selectedOfficerId, setSelectedOfficerId] = useState("");
  const [assignmentSummary, setAssignmentSummary] = useState(null);

  const [awardsFile, setAwardsFile] = useState(null);
  const [coursesFile, setCoursesFile] = useState(null);
  const [cycleFile, setCycleFile] = useState(null);

  const [loadingAgency, setLoadingAgency] = useState(true);
  const [loadingAssignments, setLoadingAssignments] = useState(false);
  const [assignmentBusy, setAssignmentBusy] = useState(false);
  const [importing, setImporting] = useState(false);

  const [error, setError] = useState("");
  const [assignmentError, setAssignmentError] = useState("");
  const [result, setResult] = useState(null);

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

        await loadOfficers(selectedAgency.id);
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

      await loadOfficers(agency.id);
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

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand-kicker">
            Paradigm Strategic Partners
          </div>
          <h1>Paradigm Training Manager</h1>
        </div>

        <div className="version">v0.2.4</div>
      </header>

      <main className="page">
        <section className="intro">
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
        </section>
      </main>
    </div>
  );
}

export default App;
