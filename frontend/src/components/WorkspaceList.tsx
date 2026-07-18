import type { Project } from "../types";

type Props = { projects: Project[]; selectedId: number | null; onSelect: (project: Project) => void; onNew: () => void };

export function WorkspaceList({ projects, selectedId, onSelect, onNew }: Props) {
  return <main className="workspace-list"><section className="empty-hero"><div><h1>Make your next repository feel familiar.</h1><p>Turn public GitHub metadata into a grounded project brief, a reading path, and an accountable human handoff.</p></div><button className="button primary" onClick={onNew}>Analyze a repository</button></section>
    {projects.length ? <section className="workspace-rail" aria-label="Existing workspaces">{projects.map((project) => <button className={`workspace-row ${project.id === selectedId ? "selected" : ""}`} key={project.id} onClick={() => onSelect(project)}><span className="repo-dot" /><span><strong>{project.name}</strong><small>{project.owner_name} · {project.status === "ready" ? "Evidence ready" : "Limited metadata"}</small></span></button>)}</section> : <section className="empty-panel"><h2>No workspaces yet</h2><p>Start with one public GitHub repository. The included demo is available from the side navigation.</p></section>}
  </main>;
}
