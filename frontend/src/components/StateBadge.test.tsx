/// <reference types="vitest/globals" />
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { stateBadgeClass, stateLabel } from "../lib/runState";
import { StateBadge } from "./StateBadge";
import type { RunState } from "../api/types";

describe("StateBadge", () => {
  const states: RunState[] = ["pending", "running", "completed", "failed", "cancelled"];

  it.each(states)("renders correct label for %s", (state) => {
    render(
      <MemoryRouter>
        <StateBadge state={state} />
      </MemoryRouter>
    );
    expect(screen.getByText(stateLabel[state])).toBeInTheDocument();
  });

  it("applies correct CSS class for running state", () => {
    render(
      <MemoryRouter>
        <StateBadge state="running" />
      </MemoryRouter>
    );
    const badge = screen.getByText("Running");
    expect(badge).toHaveClass("badge-running");
  });
});

describe("stateLabel", () => {
  it("has all five states defined", () => {
    expect(Object.keys(stateLabel).sort()).toEqual(
      ["cancelled", "completed", "failed", "pending", "running"]
    );
  });
});

describe("stateBadgeClass", () => {
  it("maps every state to a CSS class", () => {
    for (const state of Object.keys(stateLabel) as RunState[]) {
      expect(stateBadgeClass[state]).toBeTruthy();
    }
  });
});