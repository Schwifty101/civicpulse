import { useEffect, useState } from "react";
import { getStats, type StatsOut } from "../api/client";

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const max = Math.max(1, ...Object.values(data));
  return (
    <div className="breakdown">
      <h3>{title}</h3>
      <ul>
        {Object.entries(data).map(([key, count]) => (
          <li key={key}>
            <span className="breakdown-label">{key}</span>
            <span className="breakdown-bar-track">
              <span
                className="breakdown-bar"
                style={{ width: `${(count / max) * 100}%` }}
              />
            </span>
            <span className="breakdown-count">{count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function StatsPage() {
  const [stats, setStats] = useState<StatsOut | null>(null);
  const [cacheStatus, setCacheStatus] = useState<"HIT" | "MISS" | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStats()
      .then(({ data, cacheStatus }) => {
        setStats(data);
        setCacheStatus(cacheStatus);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <h1>Statistics</h1>

      {cacheStatus && (
        <span
          className={`cache-badge cache-${cacheStatus.toLowerCase()}`}
          data-testid="cache-badge"
          title="X-Cache response header from /api/stats"
        >
          X-Cache: {cacheStatus}
        </span>
      )}

      {loading && <p>Loading…</p>}

      {stats && (
        <>
          <p className="total-count">Total complaints: {stats.total}</p>
          <div className="breakdowns">
            <Breakdown title="By Category" data={stats.by_category} />
            <Breakdown title="By Priority" data={stats.by_priority} />
            <Breakdown title="By Status" data={stats.by_status} />
          </div>
        </>
      )}
    </div>
  );
}
