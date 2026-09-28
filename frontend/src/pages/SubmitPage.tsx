import { useState, type FormEvent } from "react";
import { ApiError, RateLimitError, createComplaint, type ComplaintOut } from "../api/client";

const TEXT_MIN = 10;
const TEXT_MAX = 2000;
const LOCATION_MIN = 3;
const LOCATION_MAX = 200;

function clientErrors(text: string, location: string): Record<string, string> {
  const errors: Record<string, string> = {};
  if (text.trim().length < TEXT_MIN || text.length > TEXT_MAX) {
    errors.text = `Complaint text must be between ${TEXT_MIN} and ${TEXT_MAX} characters.`;
  }
  if (location.trim().length < LOCATION_MIN || location.length > LOCATION_MAX) {
    errors.location = `Location must be between ${LOCATION_MIN} and ${LOCATION_MAX} characters.`;
  }
  return errors;
}

export function SubmitPage() {
  const [text, setText] = useState("");
  const [location, setLocation] = useState("");
  const [reporterContact, setReporterContact] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ComplaintOut | null>(null);
  const [retryAfter, setRetryAfter] = useState<number | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setResult(null);
    setGeneralError(null);
    setRetryAfter(null);

    // Mirrors server rules for fast feedback — the server still validates independently.
    const localErrors = clientErrors(text, location);
    setFieldErrors(localErrors);
    if (Object.keys(localErrors).length > 0) return;

    setSubmitting(true);
    try {
      const { data } = await createComplaint({
        text,
        location,
        reporter_contact: reporterContact || undefined,
      });
      setResult(data);
      setText("");
      setLocation("");
      setReporterContact("");
      setFieldErrors({});
    } catch (err) {
      if (err instanceof RateLimitError) {
        setRetryAfter(err.retryAfterSeconds);
      } else if (err instanceof ApiError && err.status === 400) {
        const body = err.body as { errors?: { field: string; message: string }[] };
        const next: Record<string, string> = {};
        for (const fe of body.errors ?? []) {
          const key = fe.field.replace(/^body\./, "");
          next[key] = fe.message;
        }
        setFieldErrors(next);
      } else {
        setGeneralError(err instanceof Error ? err.message : "submission failed");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <h1>Report a Complaint</h1>
      <form onSubmit={handleSubmit} noValidate>
        <label htmlFor="text">Complaint</label>
        <textarea
          id="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder="Describe the issue in detail — what, where, since when..."
          disabled={submitting}
        />
        {fieldErrors.text && (
          <p className="field-error" role="alert">
            {fieldErrors.text}
          </p>
        )}

        <label htmlFor="location">Location</label>
        <input
          id="location"
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Street, sector/block, city"
          disabled={submitting}
        />
        {fieldErrors.location && (
          <p className="field-error" role="alert">
            {fieldErrors.location}
          </p>
        )}

        <label htmlFor="contact">Contact (optional)</label>
        <input
          id="contact"
          type="text"
          value={reporterContact}
          onChange={(e) => setReporterContact(e.target.value)}
          placeholder="Phone or email"
          disabled={submitting}
        />

        <button type="submit" disabled={submitting}>
          {submitting ? "Triaging…" : "Submit Complaint"}
        </button>
        {submitting && (
          <p className="hint">AI triage takes a few seconds — hang tight.</p>
        )}
      </form>

      {retryAfter !== null && (
        <p className="warning" role="alert">
          Too many submissions — try again in {retryAfter} second{retryAfter === 1 ? "" : "s"}.
        </p>
      )}
      {generalError && (
        <p className="warning" role="alert">
          {generalError}
        </p>
      )}

      {result && (
        <div className="result-card" data-testid="result-card">
          <h2>Complaint Received</h2>
          <dl>
            <dt>Category</dt>
            <dd>{result.category}</dd>
            <dt>Priority</dt>
            <dd className={`priority-${result.priority}`}>{result.priority}</dd>
            <dt>AI Summary</dt>
            <dd>{result.ai_summary}</dd>
            <dt>Triaged by</dt>
            <dd>{result.triaged_by}</dd>
          </dl>
        </div>
      )}
    </div>
  );
}
