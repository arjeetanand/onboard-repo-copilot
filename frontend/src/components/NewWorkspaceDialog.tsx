import { FormEvent, useState } from "react";

type Props = { onClose: () => void; onSubmit: (repoUrl: string, ownerName: string, ownerContact: string) => Promise<void> };

export function NewWorkspaceDialog({ onClose, onSubmit }: Props) {
  const [repoUrl, setRepoUrl] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [ownerContact, setOwnerContact] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try { await onSubmit(repoUrl, ownerName, ownerContact); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to create the workspace."); }
    finally { setSubmitting(false); }
  }

  return <div className="modal-backdrop" role="presentation"><form className="dialog" onSubmit={submit} aria-labelledby="new-workspace-title">
    <div className="dialog-header"><div><h2 id="new-workspace-title">Analyze a public repository</h2><p>We inspect public GitHub metadata and never clone or modify the source repository.</p></div><button type="button" className="icon-button" onClick={onClose} aria-label="Close dialog">×</button></div>
    <label>GitHub repository URL<input required type="url" placeholder="https://github.com/owner/repository" value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} /></label>
    <label>Project owner<input required minLength={2} placeholder="Maya Patel" value={ownerName} onChange={(event) => setOwnerName(event.target.value)} /></label>
    <label>Owner contact <span>optional</span><input type="email" placeholder="maya@example.com" value={ownerContact} onChange={(event) => setOwnerContact(event.target.value)} /></label>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="dialog-actions"><button type="button" className="button secondary" onClick={onClose}>Cancel</button><button className="button primary" disabled={submitting}>{submitting ? "Analyzing…" : "Create workspace"}</button></div>
  </form></div>;
}
