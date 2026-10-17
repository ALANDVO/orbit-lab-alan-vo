// Dashboard page for listing and creating agent runs

import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { RunForm } from "../components/RunForm";
import { RunList } from "../components/RunList";
import { useRuns } from "../hooks/useRuns";
import type { Run, RunState } from "../api/types";

export default function RunsPage() {
  const navigate = useNavigate();
  const { runs, total, loading, error, create, filter, setFilter } = useRuns();

  const handleCreate = async (payload: { agent: string; repo_url: string; prompt: string; branch?: string | null }) => {
    const run = await create(payload);
    if (run) {
      navigate(`/runs/${run.id}`);
    }
  };

  const handleCancel = async (run: Run) => {
    try {
      await api.cancelRun(run.id);
      setFilter({ ...filter });
    } catch {
      // Error handled by UI
    }
  };

  const handleFilterChange = (state: RunState | "", agent: string) => {
    setFilter({ state: state || undefined, agent: agent || undefined, limit: 50, offset: 0 });
  };

  return (
    <div className="dashboard">
      <section className="dashboard-section">
        <h1>Agent Runs</h1>
        <p className="dashboard-intro">
          Create a new run or browse existing ones. Each run executes a coding agent
          in an isolated git worktree.
        </p>
      </section>

      <section className="dashboard-section">
        <h2>Create Run</h2>
        <RunForm
          onSubmit={handleCreate}
          loading={false}
          error={error}
        />
      </section>

      <section className="dashboard-section">
        <h2>Run History</h2>
        <RunList
          runs={runs}
          total={total}
          loading={loading}
          error={error}
          filterState={filter.state as RunState | ""}
          filterAgent={filter.agent ?? ""}
          onFilterChange={handleFilterChange}
          onSelectRun={(run) => navigate(`/runs/${run.id}`)}
          onCancelRun={handleCancel}
        />
      </section>
    </div>
  );
}