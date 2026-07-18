import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { NewWorkspaceDialog } from "./components/NewWorkspaceDialog";
import { ProjectWorkspace } from "./components/ProjectWorkspace";
import { WorkspaceList } from "./components/WorkspaceList";
import type { Project } from "./types";

function insertOrReplace(items: Project[], item: Project): Project[] {
  const index = items.findIndex((candidate) => candidate.id === item.id);
  if (index === -1) return [item, ...items];
  return items.map((candidate) => candidate.id === item.id ? item : candidate);
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const loaded = await api.listProjects();
      setProjects(loaded);
      setSelected((current) => loaded.find((project) => project.id === current?.id) || loaded[0] || null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load workspaces.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadProjects(); }, [loadProjects]);

  function updateProject(project: Project) {
    setProjects((current) => insertOrReplace(current, project));
    setSelected(project);
  }

  async function createWorkspace(repoUrl: string, ownerName: string, ownerContact: string) {
    const project = await api.createProject(repoUrl, ownerName, ownerContact);
    updateProject(project);
    setDialogOpen(false);
  }

  async function openDemo() {
    setError("");
    try { updateProject(await api.createDemo()); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to create the example workspace."); }
  }

  return <div className="app-shell">
    <aside className="sidebar"><button className="brand" onClick={() => setSelected(null)} aria-label="Return to workspaces"><span className="brand-mark">✦</span><span>Onboard Repo<br />Copilot</span></button><nav><button className={!selected ? "active" : ""} onClick={() => setSelected(null)}>Workspaces</button><button disabled={!selected} className={selected ? "active" : ""}>Project brief</button><button disabled={!selected}>Evidence</button><button disabled={!selected}>Ask</button></nav><div className="sidebar-footer"><span className="avatar">MP</span><div><strong>{selected?.owner_name || "Workspace owner"}</strong><small>{selected ? "Escalation path ready" : "Choose a workspace"}</small></div></div></aside>
    <div className="main-column"><header className="topbar"><span>{selected ? "Repository onboarding workspace" : "Your codebase onboarding workspaces"}</span><div><button className="text-button" onClick={openDemo}>Open example</button><button className="button primary compact" onClick={() => setDialogOpen(true)}>Analyze another repo</button></div></header>{error && <p className="page-error" role="alert">{error}</p>}{loading ? <main className="loading-screen">Loading workspaces…</main> : selected ? <ProjectWorkspace project={selected} onRefresh={updateProject} /> : <WorkspaceList projects={projects} selectedId={null} onSelect={setSelected} onNew={() => setDialogOpen(true)} />}</div>
    {dialogOpen && <NewWorkspaceDialog onClose={() => setDialogOpen(false)} onSubmit={createWorkspace} />}
  </div>;
}
