"""SQLite persistence with no cloud dependency for the portfolio demo."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .settings import settings


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path() -> Path:
    path = settings.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              repo_url TEXT NOT NULL UNIQUE, name TEXT NOT NULL, owner_name TEXT NOT NULL,
              owner_contact TEXT, status TEXT NOT NULL DEFAULT 'ready', summary TEXT NOT NULL,
              tech_stack TEXT NOT NULL DEFAULT '[]', modules TEXT NOT NULL DEFAULT '[]',
              documents TEXT NOT NULL DEFAULT '[]', analyzed_at TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
              role TEXT NOT NULL, content TEXT NOT NULL, confidence REAL,
              citations TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS escalations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
              question TEXT NOT NULL, answer TEXT NOT NULL, assigned_to TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL
            );
            """
        )


def _project(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in ("tech_stack", "modules", "documents"):
        item[key] = json.loads(item[key])
    return item


def list_projects() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [_project(row) for row in rows]


def get_project(project_id: int) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _project(row) if row else None


def get_project_by_url(repo_url: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE repo_url = ?", (repo_url,)).fetchone()
    return _project(row) if row else None


def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    with connection() as conn:
        cursor = conn.execute(
            """INSERT INTO projects
            (repo_url, name, owner_name, owner_contact, status, summary, tech_stack, modules, documents, analyzed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (payload["repo_url"], payload["name"], payload["owner_name"], payload.get("owner_contact"), payload["status"],
             payload["summary"], json.dumps(payload["tech_stack"]), json.dumps(payload["modules"]),
             json.dumps(payload["documents"]), payload.get("analyzed_at"), now()),
        )
        project_id = int(cursor.lastrowid)
    project = get_project(project_id)
    assert project is not None
    return project


def replace_analysis(project_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    with connection() as conn:
        conn.execute(
            """UPDATE projects SET name=?, owner_name=?, owner_contact=?, status=?, summary=?, tech_stack=?,
            modules=?, documents=?, analyzed_at=? WHERE id=?""",
            (payload["name"], payload["owner_name"], payload.get("owner_contact"), payload["status"], payload["summary"],
             json.dumps(payload["tech_stack"]), json.dumps(payload["modules"]), json.dumps(payload["documents"]),
             payload.get("analyzed_at"), project_id),
        )
    return get_project(project_id)


def create_session(project_id: int) -> int:
    with connection() as conn:
        cursor = conn.execute("INSERT INTO chat_sessions (project_id, created_at) VALUES (?, ?)", (project_id, now()))
        return int(cursor.lastrowid)


def get_session_project_id(session_id: int) -> int | None:
    with connection() as conn:
        row = conn.execute("SELECT project_id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    return int(row["project_id"]) if row else None


def create_message(session_id: int, role: str, content: str, confidence: float | None, citations: list[dict[str, str]]) -> dict[str, Any]:
    with connection() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (session_id, role, content, confidence, citations, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, role, content, confidence, json.dumps(citations), now()),
        )
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    result = dict(row)
    result["citations"] = json.loads(result["citations"])
    return result


def create_escalation(project_id: int, question: str, answer: str, assigned_to: str) -> dict[str, Any]:
    with connection() as conn:
        cursor = conn.execute(
            "INSERT INTO escalations (project_id, question, answer, assigned_to, status, created_at) VALUES (?, ?, ?, ?, 'open', ?)",
            (project_id, question, answer, assigned_to, now()),
        )
        row = conn.execute("SELECT * FROM escalations WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)
