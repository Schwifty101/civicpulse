import { useState } from "react";
import { SubmitPage } from "./pages/SubmitPage";
import { DashboardPage } from "./pages/DashboardPage";
import { StatsPage } from "./pages/StatsPage";

type View = "submit" | "dashboard" | "stats";

const VIEWS: { id: View; label: string }[] = [
  { id: "submit", label: "Submit" },
  { id: "dashboard", label: "Dashboard" },
  { id: "stats", label: "Stats" },
];

function App() {
  const [view, setView] = useState<View>("submit");

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="brand">CivicPulse</h1>
        <nav>
          {VIEWS.map((v) => (
            <button
              key={v.id}
              className={v.id === view ? "nav-active" : ""}
              onClick={() => setView(v.id)}
            >
              {v.label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {view === "submit" && <SubmitPage />}
        {view === "dashboard" && <DashboardPage />}
        {view === "stats" && <StatsPage />}
      </main>
    </div>
  );
}

export default App;
