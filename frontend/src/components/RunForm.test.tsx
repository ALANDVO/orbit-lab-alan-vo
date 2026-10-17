/// <reference types="vitest/globals" />
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RunForm } from "./RunForm";

describe("RunForm", () => {
  it("renders all input fields and a submit button", () => {
    render(<RunForm onSubmit={vi.fn()} loading={false} error={null} />);
    expect(screen.getByPlaceholderText("e.g. codex, claude-code, opencode")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("https://github.com/user/repo")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Enter the prompt for this agent run…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create run/i })).toBeInTheDocument();
  });

  it("calls onSubmit with form data when submitted", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<RunForm onSubmit={onSubmit} loading={false} error={null} />);

    const agentInput = screen.getByPlaceholderText("e.g. codex, claude-code, opencode");
    await userEvent.clear(agentInput);
    await userEvent.type(agentInput, "claude-code");
    await userEvent.type(screen.getByPlaceholderText("https://github.com/user/repo"), "https://github.com/user/repo");
    await userEvent.type(screen.getByPlaceholderText("Enter the prompt for this agent run…"), "Fix the login bug");

    fireEvent.submit(screen.getByRole("button", { name: /create run/i }).closest("form")!);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        agent: "claude-code",
        repo_url: "https://github.com/user/repo",
        prompt: "Fix the login bug",
        branch: null,
      });
    });
  });

  it("does not call onSubmit when required fields are empty", async () => {
    const onSubmit = vi.fn();
    render(<RunForm onSubmit={onSubmit} loading={false} error={null} />);
    fireEvent.submit(screen.getByRole("button", { name: /create run/i }).closest("form")!);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});