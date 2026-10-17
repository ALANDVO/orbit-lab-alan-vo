// Orbit Lab — AI orchestrator for a fleet of coding agents.
// Manages agent runs across isolated git worktrees with auditable lifecycles.

import { Link, Route, Routes } from "react-router-dom";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="app-title">
          Orbit Lab
        </Link>
        <nav className="app-nav">
          <Link to="/" className="nav-link">Runs</Link>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<RunsPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
          <Route path="*" element={<div className="page-placeholder">Not found</div>} />
        </Routes>
      </main>
    </div>
  );
}

export default App;