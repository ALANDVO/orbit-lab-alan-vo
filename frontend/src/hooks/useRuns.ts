// Hook for managing agent runs data

import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { AuditEntry, Run, RunCreate, RunListResponse, RunState } from "../api/types";

export interface RunsFilter {
  state?: RunState;
  agent?: string;
  limit?: number;
  offset?: number;
}

export function useRuns(initialFilter: RunsFilter = {}) {
  const [filter, setFilter] = useState<RunsFilter>(initialFilter);
  const [runs, setRuns] = useState<Run[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.listRuns({
        state: filter.state,
        agent: filter.agent,
        limit: filter.limit ?? 50,
        offset: filter.offset ?? 0,
      });
      setRuns(resp.runs);
      setTotal(resp.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setRuns([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  const create = async (payload: RunCreate): Promise<Run | null> => {
    try {
      const run = await api.createRun(payload);
      setRuns((prev) => [run, ...prev]);
      setTotal((prev) => prev + 1);
      return run;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      return null;
    }
  };

  useEffect(() => {
    load();
  }, [load]);

  const refetch = useCallback(() => {
    setFilter((f) => ({ ...f }));
  }, []);

  return {
    runs,
    total,
    loading,
    error,
    create,
    filter,
    setFilter,
    refetch,
  };
}

export function useRun(runId: string) {
  const [run, setRun] = useState<Run | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    try {
      const detail = await api.getRun(runId);
      setRun(detail.run);
      setAudit(detail.audit);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    load();
  }, [load]);

  return { run, audit, loading, error };
}