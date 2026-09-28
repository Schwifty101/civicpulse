import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  CATEGORIES,
  PRIORITIES,
  STATUSES,
  listComplaints,
  updateStatus,
  type Category,
  type ComplaintOut,
  type Priority,
  type Status,
} from "../api/client";

const PAGE_SIZE = 10;

export function DashboardPage() {
  const [category, setCategory] = useState<Category | "">("");
  const [priority, setPriority] = useState<Priority | "">("");
  const [status, setStatus] = useState<Status | "">("");
  const [page, setPage] = useState(1);

  const [items, setItems] = useState<ComplaintOut[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await listComplaints({
        category: category || undefined,
        priority: priority || undefined,
        status: status || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [category, priority, status, page]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleStatusChange(id: string, next: Status) {
    setRowErrors((prev) => ({ ...prev, [id]: "" }));
    try {
      await updateStatus(id, next);
      await load();
    } catch (err) {
      // The server's 409 message is shown verbatim — never a generic "error".
      const message = err instanceof ApiError ? err.message : "update failed";
      setRowErrors((prev) => ({ ...prev, [id]: message }));
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="page">
      <h1>Operations Dashboard</h1>

      <div className="filters">
        <label>
          Category
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value as Category | "");
              setPage(1);
            }}
          >
            <option value="">All</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <select
            value={priority}
            onChange={(e) => {
              setPriority(e.target.value as Priority | "");
              setPage(1);
            }}
          >
            <option value="">All</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as Status | "");
              setPage(1);
            }}
          >
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p>Loading…</p>}

      <table>
        <thead>
          <tr>
            <th>Location</th>
            <th>Category</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Summary</th>
            <th>Change status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id} data-testid="complaint-row">
              <td>{c.location}</td>
              <td>{c.category}</td>
              <td>{c.priority}</td>
              <td>{c.status}</td>
              <td>{c.ai_summary}</td>
              <td>
                <div className="status-changer">
                  {STATUSES.filter((s) => s !== c.status).map((s) => (
                    <button key={s} onClick={() => handleStatusChange(c.id, s)}>
                      → {s}
                    </button>
                  ))}
                </div>
                {rowErrors[c.id] && (
                  <p className="field-error" role="alert">
                    {rowErrors[c.id]}
                  </p>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pagination">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          Previous
        </button>
        <span>
          Page {page} of {totalPages} ({total} total)
        </span>
        <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}
