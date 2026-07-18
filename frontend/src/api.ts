import type { ChatMessage, Project } from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "The request could not be completed.");
  }
  return response.json() as Promise<T>;
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),
  createProject: (repo_url: string, owner_name: string, owner_contact: string) => request<Project>("/projects", { method: "POST", body: JSON.stringify({ repo_url, owner_name, owner_contact: owner_contact || null }) }),
  createDemo: () => request<Project>("/projects/demo", { method: "POST", body: JSON.stringify({}) }),
  reanalyze: (projectId: number) => request<Project>(`/projects/${projectId}/analyze`, { method: "POST" }),
  createSession: (projectId: number) => request<{ id: number }>(`/projects/${projectId}/chat-sessions`, { method: "POST" }),
  ask: (sessionId: number, question: string) => request<ChatMessage>(`/chat-sessions/${sessionId}/messages`, { method: "POST", body: JSON.stringify({ question }) }),
  escalate: (projectId: number, question: string, answer: string) => request<{ id: number; assigned_to: string }>(`/projects/${projectId}/escalations`, { method: "POST", body: JSON.stringify({ question, answer }) }),
};
