from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import database
from .contracts import ChatMessageCreate, ChatMessageOut, ChatSessionOut, DemoProjectCreate, EscalationCreate, ProjectCreate, ProjectOut
from .repository_analysis import analyze_public_github_repo, demo_analysis, validate_and_normalize_repo_url
from .settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.init_db()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or [],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

def project_out(project: dict) -> ProjectOut:
    return ProjectOut(**project)


def _store_analysis(repo_url: str, owner_name: str, owner_contact: str | None, existing_id: int | None = None) -> ProjectOut:
    normalized, _, _ = validate_and_normalize_repo_url(repo_url)
    analysis = analyze_public_github_repo(normalized)
    payload = {
        "repo_url": normalized, "name": analysis["name"], "owner_name": owner_name, "owner_contact": owner_contact,
        "status": analysis["status"], "summary": analysis["summary"], "tech_stack": analysis["tech_stack"],
        "modules": analysis["modules"], "documents": analysis["documents"],
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
    project = database.replace_analysis(existing_id, payload) if existing_id else database.create_project(payload)
    assert project is not None
    return project_out(project)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "onboard-repo-copilot"}


@app.get("/projects", response_model=list[ProjectOut])
def list_projects() -> list[ProjectOut]:
    return [project_out(item) for item in database.list_projects()]


@app.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(request: ProjectCreate) -> ProjectOut:
    normalized, _, _ = validate_and_normalize_repo_url(str(request.repo_url))
    existing = database.get_project_by_url(normalized)
    if existing:
        return _store_analysis(normalized, request.owner_name, request.owner_contact, existing["id"])
    return _store_analysis(normalized, request.owner_name, request.owner_contact)


@app.get("/projects/{project_id}", response_model=ProjectOut)
def read_project(project_id: int) -> ProjectOut:
    project = database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return project_out(project)


@app.post("/projects/{project_id}/analyze", response_model=ProjectOut)
def reanalyze_project(project_id: int) -> ProjectOut:
    project = database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return _store_analysis(project["repo_url"], project["owner_name"], project["owner_contact"], project_id)


@app.post("/projects/demo", response_model=ProjectOut, status_code=201)
def create_demo_project(request: DemoProjectCreate) -> ProjectOut:
    existing = database.get_project_by_url("https://github.com/acme/payments-service")
    payload = {**demo_analysis(), "owner_name": request.owner_name, "owner_contact": request.owner_contact,
               "analyzed_at": datetime.now(timezone.utc).isoformat()}
    project = database.replace_analysis(existing["id"], payload) if existing else database.create_project(payload)
    assert project is not None
    return project_out(project)


@app.post("/projects/{project_id}/chat-sessions", response_model=ChatSessionOut, status_code=201)
def create_chat_session(project_id: int) -> ChatSessionOut:
    if not database.get_project(project_id):
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return ChatSessionOut(id=database.create_session(project_id), project_id=project_id)


def _answer(project: dict, question: str) -> tuple[str, float, list[dict[str, str]]]:
    query = question.lower()
    citations = project["documents"][:3]
    module_text = "; ".join(f"{module['name']}: {module['role']}" for module in project["modules"][:4])
    if any(token in query for token in ("owner", "help", "contact", "escalat")):
        return (f"The designated project owner is {project['owner_name']}. Use the human handoff when the repository evidence is insufficient.", 0.95, citations[:1])
    if any(token in query for token in ("start", "read", "onboard", "setup")):
        return (f"Start with {project['documents'][0]['source']}, then review these areas: {module_text}.", 0.88, citations)
    if any(token in query for token in ("architecture", "module", "flow", "where")):
        return (f"The available repository evidence points to this module map: {module_text}. Verify implementation details in the cited sources before making a change.", 0.77, citations)
    return (f"Based on the current repository brief: {project['summary']} The most relevant areas are {module_text}.", 0.63, citations)


@app.post("/chat-sessions/{session_id}/messages", response_model=ChatMessageOut, status_code=201)
def ask_question(session_id: int, request: ChatMessageCreate) -> ChatMessageOut:
    project_id = database.get_session_project_id(session_id)
    if not project_id:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    project = database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    database.create_message(session_id, "user", request.question, None, [])
    answer, confidence, citations = _answer(project, request.question)
    message = database.create_message(session_id, "assistant", answer, confidence, citations)
    return ChatMessageOut(**message, escalation_recommended=confidence < 0.75)


@app.post("/projects/{project_id}/escalations", status_code=201)
def create_escalation(project_id: int, request: EscalationCreate) -> dict:
    project = database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return database.create_escalation(project_id, request.question, request.answer, request.assigned_to or project["owner_name"])
