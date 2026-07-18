export type Module = { name: string; role: string };
export type Citation = { source: string; ref: string };

export type Project = {
  id: number;
  repo_url: string;
  name: string;
  owner_name: string;
  owner_contact: string | null;
  status: "ready" | "analyzing" | "degraded";
  summary: string;
  tech_stack: string[];
  modules: Module[];
  documents: Citation[];
  analyzed_at: string | null;
  created_at: string;
};

export type ChatMessage = {
  id: number;
  role: string;
  content: string;
  confidence: number | null;
  citations: Citation[];
  escalation_recommended: boolean;
};
