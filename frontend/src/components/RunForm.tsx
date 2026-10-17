// Form for creating a new agent run

import { useState } from "react";
import type { RunCreate } from "../api/types";

interface Props {
  onSubmit: (payload: RunCreate) => Promise<unknown>;
  loading: boolean;
  error: string | null;
}

export function RunForm({ onSubmit, loading, error }: Props) {
  const [agent, setAgent] = useState("codex");
  const [repoUrl, setRepoUrl] = useState("");
  const [prompt, setPrompt] = useState("");
  const [branch, setBranch] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim() || !prompt.trim()) return;

    await onSubmit({
      agent: agent.trim(),
      repo_url: repoUrl.trim(),
      prompt: prompt.trim(),
      branch: branch.trim() || null,
    });

    setRepoUrl("");
    setPrompt("");
    setBranch("");
  };

  return (
    <form className="run-form" onSubmit={handleSubmit}>
      {error && <div className="error-banner">{error}</div>}

      <div className="form-group">
        <label>Agent</label>
        <input
          type="text"
          value={agent}
          onChange={(e) => setAgent(e.target.value)}
          placeholder="e.g. codex, claude-code, opencode"
          required
          maxLength={64}
        />
      </div>

      <div className="form-group">
        <label>Repository URL</label>
        <input
          type="url"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/user/repo"
          required
          maxLength={512}
        />
      </div>

      <div className="form-group">
        <label>Branch (optional)</label>
        <input
          type="text"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="main"
          maxLength={128}
        />
      </div>

      <div className="form-group">
        <label>Prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter the prompt for this agent run…"
          required
          maxLength={16384}
          rows={4}
        />
      </div>

      <button type="submit" className="btn btn-primary" disabled={loading}>
        {loading ? "Creating…" : "Create Run"}
      </button>
    </form>
  );
}