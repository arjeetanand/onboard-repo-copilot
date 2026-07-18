from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ProjectCreate(BaseModel):
    repo_url: HttpUrl
    owner_name: str = Field(min_length=2, max_length=120)
    owner_contact: str | None = Field(default=None, max_length=255)


class ProjectOut(BaseModel):
    id: int
    repo_url: str
    name: str
    owner_name: str
    owner_contact: str | None
    status: Literal["ready", "analyzing", "degraded"]
    summary: str
    tech_stack: list[str]
    modules: list[dict[str, str]]
    documents: list[dict[str, str]]
    analyzed_at: str | None
    created_at: str


class ChatSessionOut(BaseModel):
    id: int
    project_id: int


class ChatMessageCreate(BaseModel):
    question: str = Field(min_length=2, max_length=1200)


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    confidence: float | None
    citations: list[dict[str, str]]
    escalation_recommended: bool


class EscalationCreate(BaseModel):
    question: str = Field(min_length=2, max_length=1200)
    answer: str = Field(min_length=1, max_length=4000)
    assigned_to: str | None = Field(default=None, max_length=120)


class DemoProjectCreate(BaseModel):
    owner_name: str = "Maya Patel"
    owner_contact: str | None = "maya@example.com"
