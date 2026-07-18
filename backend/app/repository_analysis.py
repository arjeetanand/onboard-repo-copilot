"""Read-only GitHub metadata analysis with a deterministic no-network fallback."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import HTTPException

from .settings import settings


GITHUB_RE = re.compile(r"^/([^/]+)/([^/#?]+?)/?$")


def validate_and_normalize_repo_url(value: str) -> tuple[str, str, str]:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in (settings.allowed_repo_hosts or []):
        raise HTTPException(status_code=422, detail="Use a public https://github.com/owner/repository URL.")
    if parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
        raise HTTPException(status_code=422, detail="Repository URLs cannot include credentials, ports, queries, or fragments.")
    match = GITHUB_RE.fullmatch(parsed.path)
    if not match:
        raise HTTPException(status_code=422, detail="Repository URLs must include exactly an owner and repository name.")
    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    if not owner or not repo:
        raise HTTPException(status_code=422, detail="Repository owner and name are required.")
    return f"https://github.com/{owner}/{repo}", owner, repo


def _github_json(path: str) -> Any:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "onboard-repo-copilot-demo"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    request = Request(f"https://api.github.com{path}", headers=headers)
    with urlopen(request, timeout=6) as response:  # nosec B310: fixed GitHub API origin
        size = int(response.headers.get("Content-Length", "0"))
        if size and size > settings.max_repo_file_bytes:
            raise ValueError("GitHub response exceeded the configured safe size limit.")
        return json.loads(response.read(settings.max_repo_file_bytes + 1).decode("utf-8"))


def _fallback(owner: str, repo: str, message: str) -> dict[str, Any]:
    readable = repo.replace("-", " ").replace("_", " ").title()
    return {
        "name": f"{owner}/{repo}",
        "summary": f"{readable} is ready for a local onboarding review. Live GitHub metadata was unavailable, so this brief is based on the repository identity only.",
        "tech_stack": [],
        "modules": [
            {"name": "README.md", "role": "Start here: project purpose, setup, and decisions."},
            {"name": "src/", "role": "Likely application source; confirm the runtime entry point."},
            {"name": "tests/", "role": "Review intended behaviour and regression coverage."},
        ],
        "documents": [
            {"source": "Repository URL", "ref": f"https://github.com/{owner}/{repo}"},
            {"source": "Analysis note", "ref": message},
        ],
        "status": "degraded",
    }


def analyze_public_github_repo(repo_url: str) -> dict[str, Any]:
    normalized, owner, repo = validate_and_normalize_repo_url(repo_url)
    try:
        metadata = _github_json(f"/repos/{owner}/{repo}")
        if metadata.get("private"):
            raise HTTPException(status_code=422, detail="Only public GitHub repositories can be analyzed by this demo.")
        contents = _github_json(f"/repos/{owner}/{repo}/contents")
        languages = _github_json(f"/repos/{owner}/{repo}/languages")
        modules: list[dict[str, str]] = []
        for item in contents[: settings.max_repo_files]:
            name = item.get("name", "unknown")
            item_type = item.get("type", "file")
            if name.lower() in {".env", ".env.local", "id_rsa", "id_ed25519"}:
                continue
            role = "Top-level directory to inspect" if item_type == "dir" else "Repository entry point or supporting file"
            if name.lower().startswith("readme"):
                role = "Project purpose and local setup"
            elif name.lower() in {"package.json", "pyproject.toml", "requirements.txt", "go.mod"}:
                role = "Runtime dependencies and scripts"
            elif name.lower() in {"dockerfile", "docker-compose.yml"}:
                role = "Container and deployment configuration"
            modules.append({"name": name, "role": role})
        description = metadata.get("description") or "No repository description is available yet."
        return {
            "name": metadata.get("full_name", f"{owner}/{repo}"),
            "summary": description,
            "tech_stack": list(languages.keys())[:8],
            "modules": modules or _fallback(owner, repo, "The repository root did not contain visible files.")["modules"],
            "documents": [
                {"source": "GitHub repository", "ref": normalized},
                {"source": "Repository root", "ref": f"{normalized}/tree/{metadata.get('default_branch', 'main')}"},
                {"source": "GitHub metadata", "ref": metadata.get("html_url", normalized)},
            ],
            "status": "ready",
        }
    except HTTPException:
        raise
    except (OSError, URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return _fallback(owner, repo, f"Live metadata unavailable: {exc.__class__.__name__}.")


def demo_analysis() -> dict[str, Any]:
    return {
        "repo_url": "https://github.com/acme/payments-service",
        "name": "acme/payments-service",
        "summary": "Payments Service handles authorization, capture, refunds, and settlement through a REST API and publishes domain events for downstream workflows.",
        "tech_stack": ["Java", "Spring Boot", "PostgreSQL", "Kafka", "Redis", "Stripe"],
        "modules": [
            {"name": "api", "role": "REST controllers and request validation"},
            {"name": "application", "role": "Use cases, orchestration, and transaction management"},
            {"name": "domain", "role": "Payment entities and business rules"},
            {"name": "infrastructure", "role": "Persistence, messaging, and external adapters"},
        ],
        "documents": [
            {"source": "README.md", "ref": "Getting started and local setup"},
            {"source": "application/PaymentService.java", "ref": "Capture and refund orchestration"},
            {"source": "infrastructure/stripe/StripeClient.java", "ref": "Stripe adapter boundary"},
        ],
        "status": "ready",
    }
