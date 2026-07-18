import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import App from "./App";

const demo = {
  id: 7, repo_url: "https://github.com/acme/payments-service", name: "acme/payments-service", owner_name: "Maya Patel", owner_contact: "maya@example.com", status: "ready", summary: "Payments Service handles authorization and settlement.", tech_stack: ["Java", "Kafka"], modules: [{ name: "api", role: "REST controllers" }], documents: [{ source: "README.md", ref: "Setup" }], analyzed_at: "2026-07-18T00:00:00Z", created_at: "2026-07-18T00:00:00Z",
};

function response(data: unknown, ok = true) { return { ok, json: async () => data }; }

describe("Onboard Repo Copilot", () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn().mockResolvedValue(response([])) as unknown as typeof fetch; });

  test("loads an empty workspace state", async () => {
    render(<App />);
    expect(await screen.findByText("No workspaces yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze a repository" })).toBeInTheDocument();
  });

  test("creates and opens the example workspace", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(response([])).mockResolvedValueOnce(response(demo)).mockResolvedValueOnce(response({ id: 9, project_id: 7 }));
    render(<App />);
    await screen.findByText("No workspaces yet");
    fireEvent.click(screen.getByText("Open example"));
    expect(await screen.findByText("acme/payments-service")).toBeInTheDocument();
    expect(screen.getByText(/Payments Service handles authorization/i)).toBeInTheDocument();
  });

  test("validates an API error in the new workspace form", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(response([])).mockResolvedValueOnce(response({ detail: "Use a public GitHub URL." }, false));
    render(<App />);
    await screen.findByText("No workspaces yet");
    fireEvent.click(screen.getByRole("button", { name: "Analyze a repository" }));
    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repository"), { target: { value: "https://github.com/acme/demo" } });
    fireEvent.change(screen.getByPlaceholderText("Maya Patel"), { target: { value: "Maya Patel" } });
    fireEvent.click(screen.getByRole("button", { name: "Create workspace" }));
    expect(await screen.findByText("Use a public GitHub URL.")).toBeInTheDocument();
  });

  test("asks a question and exposes a human handoff for a low-confidence answer", async () => {
    const answer = { id: 11, role: "assistant", content: "Evidence suggests the application module is a good start.", confidence: 0.63, citations: [{ source: "README.md", ref: "Setup" }], escalation_recommended: true };
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(response([demo])).mockResolvedValueOnce(response({ id: 9, project_id: 7 })).mockResolvedValueOnce(response(answer));
    render(<App />);
    await screen.findByText("acme/payments-service");
    fireEvent.change(screen.getByPlaceholderText("Where should I start reading this codebase?"), { target: { value: "How does it work?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask question" }));
    expect(await screen.findByText(/Evidence suggests/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Get human help/i })).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
  });
});
