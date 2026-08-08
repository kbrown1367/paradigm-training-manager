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

function App() {
  const [agency, setAgency] = useState(null);
  const [awardsFile, setAwardsFile] = useState(null);
  const [coursesFile, setCoursesFile] = useState(null);
  const [cycleFile, setCycleFile] = useState(null);

  const [loadingAgency, setLoadingAgency] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

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

        setAgency(agencies[0]);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoadingAgency(false);
      }
    }

    loadAgency();
  }, []);

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
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand-kicker">
            Paradigm Strategic Partners
          </div>
          <h1>Paradigm Training Manager</h1>
        </div>

        <div className="version">v0.2.1</div>
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

            <div className="import-id">
              Import ID: {result.import_job_id}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
