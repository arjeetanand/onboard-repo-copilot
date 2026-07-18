import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { ChatMessage, Project } from "../types";

type Props = { project: Project; onRefresh: (project: Project) => void };

function Evidence({ citations }: { citations: { source: string; ref: string }[] }) {
  return <div className="citations">{citations.map((citation) => <a key={`${citation.source}-${citation.ref}`} href={citation.ref.startsWith("http") ? citation.ref : undefined} target="_blank" rel="noreferrer"><strong>{citation.source}</strong><span>{citation.ref}</span></a>)}</div>;
}

export function ProjectWorkspace({ project, onRefresh }: Props) {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState("");
  const [asking, setAsking] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [handoff, setHandoff] = useState("");

  useEffect(() => { let alive = true; setMessages([]); setQuestion(""); setError(""); setHandoff(""); api.createSession(project.id).then((session) => { if (alive) setSessionId(session.id); }).catch((caught) => { if (alive) setError(caught.message); }); return () => { alive = false; }; }, [project.id]);

  async function ask(event: FormEvent) { event.preventDefault(); if (!sessionId || !question.trim()) return; setAsking(true); setError(""); setHandoff(""); try { const response = await api.ask(sessionId, question.trim()); setMessages((current) => [...current, response]); setQuestion(""); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to ask the codebase."); } finally { setAsking(false); } }
  async function refresh() { setRefreshing(true); setError(""); try { onRefresh(await api.reanalyze(project.id)); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to refresh analysis."); } finally { setRefreshing(false); } }
  async function escalate(message: ChatMessage) { try { const result = await api.escalate(project.id, question || "Follow-up question", message.content); setHandoff(`Handoff created for ${result.assigned_to}.`); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to create the handoff."); } }

  return <main className="project-workspace"><header className="project-header"><div><p className="path-label">Workspace / codebase briefing</p><h1>{project.name}</h1><a href={project.repo_url} target="_blank" rel="noreferrer">{project.repo_url.replace("https://github.com/", "github.com/")}</a></div><button className="button secondary" onClick={refresh} disabled={refreshing}>{refreshing ? "Refreshing…" : "Refresh analysis"}</button></header>
    <section className="brief-grid"><article className="project-brief"><h2>Project brief</h2><p className="summary">{project.summary}</p><h3>Technology signals</h3><div className="stack">{project.tech_stack.length ? project.tech_stack.map((item) => <span key={item}>{item}</span>) : <span>Not detected</span>}</div><h3>Module map</h3><div className="module-map">{project.modules.map((module) => <div key={module.name}><code>{module.name}</code><p>{module.role}</p></div>)}</div><div className="owner-card"><span>Owner / escalation</span><strong>{project.owner_name}</strong><small>{project.owner_contact || "Contact not provided"}</small></div></article>
      <aside className="ask-panel"><div><h2>Ask the codebase</h2><p>Answers are tied to the available repository evidence.</p></div><form onSubmit={ask}><label className="sr-only" htmlFor="question">Ask a question</label><textarea id="question" placeholder="Where should I start reading this codebase?" value={question} onChange={(event) => setQuestion(event.target.value)} /><button className="button primary" disabled={!sessionId || asking}>{asking ? "Finding evidence…" : "Ask question"}</button></form>{error && <p className="form-error" role="alert">{error}</p>}{handoff && <p className="success-message">{handoff}</p>}<div className="answer-list">{messages.length === 0 ? <div className="chat-empty">Ask about the architecture, onboarding path, or owner. Low-confidence answers can be handed off to a human.</div> : messages.map((message) => <article className="answer" key={message.id}><div className="answer-title"><span>Evidence-backed answer</span>{message.confidence !== null && <small>{Math.round(message.confidence * 100)}% confidence</small>}</div><p>{message.content}</p><Evidence citations={message.citations} />{message.escalation_recommended && <button className="text-button" onClick={() => escalate(message)}>Get human help →</button>}</article>)}</div></aside></section>
  </main>;
}
