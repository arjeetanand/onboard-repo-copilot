# Engineering learnings

This document records decisions, issues found during consolidation, and the
commands used to verify the project. It is deliberately kept in the repository
so future contributors can understand *why* the project has its current shape.

## Source provenance

The consolidated product, **Onboard Repo Copilot**, combines original work from
two repositories. Only the capabilities listed below are being carried forward;
the source repositories remain the historical record until this project is
tested and deployed.

| Source repository | Commit inspected | Capabilities retained |
| --- | --- | --- |
| `askRepo` | `5f2a1bfd53ef4e5f4913dea0f18e3c0d8e1c9236` | Repository-onboarding shape, structured codebase brief, evidence-backed Q&A concept, FastAPI/React foundation, and Docker Compose approach. |
| `OnboardAI_Buddy` | `622558f496fb4b77f5edc669642a24d968ece3e5` | Project metadata, ownership, onboarding workflow, generated project twin, human escalation, optional Slack and OCI concepts. |

## Architectural decisions

- The canonical name is `onboard-repo-copilot`. Its purpose is to turn an
  approved GitHub repository into an evidence-backed onboarding workspace with
  a project brief, module map, Q&A, ownership metadata, and an escalation path.
- AskRepo is the technical baseline because it supplied a containerized
  FastAPI + React foundation and initial frontend tests. OnboardAI Buddy's
  onboarding-domain features are incorporated into that single product rather
  than maintained as a competing public project.
- The application must work without OCI, GitHub, or Slack credentials. Optional
  integrations are disabled by default and deterministic local analysis is the
  baseline behavior used in automated tests.
- SQLite is suitable for the first local/demo release. The database URL must be
  configurable, data belongs under the ignored `data/` directory, and a future
  production deployment should use a managed database plus migrations/backups.
- Repository identifiers are stable normalized GitHub owner/repository names.
  Timestamp-based project identifiers and Python's process-randomized `hash()`
  are not stable enough for idempotent re-analysis.

## Security fixes and guardrails

### GitHub-only repository policy

Repository URLs are a server-side network boundary. The canonical API accepts
only normalized `https://github.com/<owner>/<repo>` URLs (and the explicitly
supported GitHub URL forms), rejects loopback/private-network targets and
redirect chains, and applies file-count, file-size, and request-time limits.
This prevents arbitrary clone/fetch requests, server-side request forgery, and
unbounded repository analysis. Blog ingestion is not part of the initial
public workflow; any future arbitrary-URL fetcher requires the same policy.

### Secret-file exclusion

Never index, return, or commit credentials. The scanner must exclude `.env`,
`.env.*`, private keys, credentials, build folders, virtual environments,
`node_modules`, `.git`, database files, and generated artifacts. The repository
contains a safe `.env.example` only; real `.env` files, local data, OCI
configuration overrides, and test artifacts are ignored by Git. Secret-bearing
files must not be sent to an LLM or stored in any future retrieval system.

### CORS and access boundary

Do not use wildcard CORS with credentials. The API reads a comma-separated
`CORS_ORIGINS` allowlist, which defaults to the local Vite application during
development. The app is a portfolio/demo project until authentication and
authorization are added; do not deploy it as a public multi-tenant service
that exposes project metadata, chats, or escalation records.

### Optional integrations

`ENABLE_OCI_GENAI=false` and `SLACK_NOTIFY_ESCALATIONS=false` are safe
defaults. OCI credentials and Slack webhook URLs are supplied only through a
local ignored environment file or a deployment secret manager. The default
Compose configuration must not mount a developer's `~/.oci` directory.

## Configuration contract

The safe root `.env.example` should document these variables without including
real values:

```dotenv
APP_ENV=development
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:5173

DATABASE_URL=sqlite:///./data/onboard_repo_copilot.db
PROJECT_DATA_DIR=./data

ALLOWED_REPO_HOSTS=github.com,www.github.com
MAX_REPO_FILES=250
MAX_REPO_FILE_BYTES=250000
GITHUB_TOKEN=

ENABLE_OCI_GENAI=false
OCI_REGION=
OCI_COMPARTMENT_ID=
OCI_PROFILE=DEFAULT
OCI_CONFIG_FILE=
OCI_MODEL_ID=
OCI_ENDPOINT=

SLACK_NOTIFY_ESCALATIONS=false
SLACK_WEBHOOK_URL=

VITE_API_URL=http://localhost:8000
```

## Initial verification plan

Run all checks from a clean checkout after copying `.env.example` to `.env`
and keeping optional cloud integrations disabled.

```bash
# Backend unit, service, and API tests
cd backend
python -m pytest -q --cov=app --cov-report=term-missing

# Frontend component tests and production build
cd ../frontend
npm ci
npm run test -- --run
npm run build

# Containerized end-to-end smoke test
cd ..
docker compose --env-file .env.test up --build -d
curl --fail http://localhost:8000/health
curl --fail http://localhost:5173
docker compose down -v
```

The test suite must cover the following behavior before a public deployment:

1. API health/readiness and the configured CORS origin behavior.
2. Valid public GitHub URL registration and stable, repeatable project IDs.
3. Rejection of malformed, non-GitHub, loopback, private-network, redirecting,
   and oversized repository inputs.
4. Project create/update/delete lifecycle, including validation on updates and
   related-record cleanup.
5. Project-twin generation and chat in deterministic fallback mode with OCI
   disabled.
6. Citation integrity: every returned citation maps to allowed indexed source
   content and never to a secret or ignored file.
7. Idempotent re-analysis across application restarts.
8. Slack escalation behavior with the integration disabled, plus mocked success
   and failure paths when explicitly enabled.
9. Registration, overview, chat, failure-state, and escalation frontend flows.
10. Docker startup, service readiness, and local persistence behavior.

## Dated work log

### 2026-07-18 — Consolidation audit and baseline

- Inspected AskRepo at `5f2a1bf` and OnboardAI Buddy at `622558f` before
  consolidation.
- Selected AskRepo as the implementation base and defined one public product
  rather than two overlapping portfolio repositories.
- Identified the missing backend coverage in both sources, no automated tests
  in OnboardAI Buddy, and only mocked frontend tests in AskRepo.
- Documented source issues to prevent their return: AskRepo's Docker profile
  made the README startup command incomplete, it lacked a `.gitignore`, and it
  used unstable project identifiers. OnboardAI Buddy hard-coded its API URL,
  enabled optional cloud integrations by default, and allowed unvalidated local
  repository paths through parts of its project API.
- Added this learning record to make the security boundary, configuration
  contract, and verification expectations explicit for future work.

### 2026-07-18 — Offline metadata fallback did not catch every network failure

- **Symptom:** The deterministic repository-analysis test raised `OSError`
  instead of returning the documented limited-metadata workspace when a network
  transport was unavailable.
- **Cause:** The fallback handled `URLError` but did not include the broader
  operating-system transport error surfaced by a mocked/offline client.
- **Fix:** Treat `OSError` as a recoverable metadata-fetch failure and return a
  clearly labelled `degraded` project brief with evidence stating that live
  metadata was unavailable.
- **Prevention:** Keep the offline public-repository test in the backend suite;
  all default workflows must remain usable without an API token or network.

### 2026-07-18 — FastAPI startup hook emitted a deprecation warning

- **Symptom:** The API suite passed but reported FastAPI's `on_event` startup
  deprecation warning.
- **Cause:** The initial service lifecycle used the older startup-event API.
- **Fix:** Replaced it with an explicit FastAPI lifespan handler that
  initializes SQLite before serving requests.
- **Prevention:** Treat warning-free test output as part of the definition of
  done for this project.

### 2026-07-18 — QA server origin was blocked by the default CORS allowlist

- **Symptom:** A browser QA instance at `127.0.0.1:5181` displayed a failed
  workspace request even though the API was healthy.
- **Cause:** The secure default CORS policy permits the standard Vite origin
  `http://localhost:5173`, not an arbitrary alternate test port/origin.
- **Fix:** Kept the secure default and validated the regular development flow
  at the documented `localhost:5173` origin. The temporary alternate QA
  instance was not used as evidence of a product defect.
- **Prevention:** Browser smoke tests target the documented local origin, and
  deployments must set `CORS_ORIGINS` explicitly for their own frontend URL.

### 2026-07-18 — In-app-browser screenshot capture timed out

- **Symptom:** The in-app browser completed interaction checks but its CDP
  screenshot request timed out twice after fresh state checks.
- **Cause:** The browser environment's screenshot endpoint was unreliable for
  this local development tab.
- **Fix:** Added a Playwright end-to-end smoke test that performs the same
  local example → cited answer → human handoff path and writes a visual QA
  screenshot. The in-app browser still verifies the real interaction flow.
- **Prevention:** Retain both the component suite and the browser smoke test;
  a screenshot tool failure should not prevent functional evidence collection.

### 2026-07-18 — Browser smoke test assumed an empty persisted workspace

- **Symptom:** The first Playwright smoke run could not find the empty-state
  heading because the in-app QA had already created the persisted example
  workspace.
- **Cause:** SQLite correctly retains local project data between application
  sessions, but the browser test assumed a fresh database.
- **Fix:** Made the test idempotent: it verifies the always-visible **Open
  example** action, then creates or refreshes the same deterministic demo
  workspace before exercising Q&A and handoff.
- **Prevention:** Browser tests must be valid with either a fresh or persisted
  local database unless they explicitly reset their isolated test database.

### 2026-07-18 — Legacy page assets exposed the source-product name

- **Symptom:** The React workspace displayed the consolidated product name, but
  the browser tab and page description still said `AskRepo` and loaded unused
  third-party font and Mermaid assets.
- **Cause:** The source application's `index.html` had not been included in
  the first UI refactor.
- **Fix:** Replaced the metadata with Onboard Repo Copilot branding and removed
  unused remote assets so the production interface has no unnecessary runtime
  CDN dependency.
- **Prevention:** Include document title, metadata, and runtime asset review in
  final release QA, not only component-level UI review.

### 2026-07-18 — Unit and browser test discovery overlapped

- **Symptom:** A full frontend unit-test command attempted to execute the
  Playwright browser specification as a Vitest file.
- **Cause:** Vitest's default test discovery includes `*.spec.ts` below the
  project root, including the dedicated `e2e/` directory.
- **Fix:** Explicitly excluded `e2e/**` from Vitest; the `test:e2e` script
  remains the only runner for browser specifications.
- **Prevention:** Keep unit and end-to-end tests in separate directories and
  make both runner boundaries explicit in configuration.

### 2026-07-18 — Mobile header hid the demo entry point

- **Symptom:** The mobile smoke test could not find **Open example**, leaving
  a new mobile visitor without the fastest way to see the product's workflow.
- **Cause:** A responsive rule hid all text buttons in the top bar to conserve
  space, including the primary demo action.
- **Fix:** The header now hides only descriptive text at phone widths, keeps
  both actions visible, and uses compact spacing to avoid horizontal overflow.
- **Prevention:** Keep the 390px end-to-end smoke test; responsive rules should
  preserve every required user action, not only the layout.

### 2026-07-18 — Browser assertion exceeded the installed API surface

- **Symptom:** The mobile test reached the responsive workspace but failed on
  `expect(locator).toEvaluate(...)`.
- **Cause:** That matcher is not provided by the installed Playwright version.
- **Fix:** Evaluate the scroll-width predicate on the page, then assert the
  returned boolean with the portable `expect(value).toBeTruthy()` matcher.
- **Prevention:** Prefer the documented matcher set pinned in `package-lock.json`
  and validate new browser assertions with the project's actual runner.
