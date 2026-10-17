// Detail page for a single agent run

import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { RunDetailView } from "../components/RunDetail";
import { RunStatusControls } from "../components/RunStatusControls";
import { useRun } from "../hooks/useRuns";

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const { run, audit, loading, error } = useRun(runId ?? "");
  const [actionError, setActionError] = useState<string | null>(null);

  const handleStart = async () => {
    try {
      await api.startRun(runId!);
      window.location.reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Unknown error");
    }
  };

  const handleComplete = async () => {
    try {
      await api.completeRun(runId!);
      window.location.reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Unknown error");
    }
  };

  const handleFail = async () => {
    try {
      await api.failRun(runId!, "Agent failed unexpectedly");
      window.location.reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Unknown error");
    }
  };

  const handleCancel = async () => {
    try {
      await api.cancelRun(runId!);
      window.location.reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Unknown error");
    }
  };

  return (
    <div className="detail-page">
      {run && (
        <RunStatusControls
          run={run}
          onStart={handleStart}
          onComplete={handleComplete}
          onFail={handleFail}
          onCancel={handleCancel}
          error={actionError}
        />
      )}
      <RunDetailView
        detail={run ? { run, audit } : null}
        loading={loading}
        error={error ?? actionError}
      />
      <button className="btn btn-secondary" onClick={() => navigate("/")}>
        ← Back to Runs
      </button>
    </div>
  );
}