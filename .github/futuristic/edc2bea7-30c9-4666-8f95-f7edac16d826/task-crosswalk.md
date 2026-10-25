# T002 — proposed implementation-task and verification crosswalk

This is a **planning artifact**, not `SolutionDesignOutput`, an application, a test result, or the final solution-design JSON/Markdown. The approved `requirements_analysis` contains REQ-001 through REQ-024. The proposed IDs below are **implementation** `TASK-NNN` IDs, not document-stage T001/T002 IDs. No application or pytest suite is claimed to exist. The candidate IDs and dependency order follow T001 `design-notes.md`; detailed criteria here make their future verification explicit.

## Evidence and citation boundary

The full pinned story and approved `requirements_analysis`, `ui_analysis`, and risk outputs were read to their `next_offset: null` boundaries. The approved stage-output reader returned **no source-reference locator** for those outputs: their requirement IDs are authorized predecessor links, but no `stage_output` source reference is invented. The attachment read returned a source reference, not image bytes; the image description below is the exact observation supplied by the user, not a claim to have measured a running UI.

Only the following directly returned evidence references are cited in task entries (each triple is exact):

| Key | Exact source reference | Use |
| --- | --- | --- |
| S | `{"source_type":"user_story","source_id":"user_story","locator":"characters 0-16000"}` | Local Python 3.12/Flask/server-rendered/pytest scope, synthetic accounts, in-memory sink, production-limitations documentation, and no deployment/workflows. |
| A | `{"source_type":"attachment","source_id":"941402b9-bfd8-414c-a6e4-2fc2dce190a1","locator":"sign-in-wireframe.png"}` | Supplied sign-in image reference; the user observes a white page, centered thin dark-outlined rectangular card, bold “Sign in”, “Email address” / `name@example.com`, “Password” / `********` placeholder, blue underlined “Forgot password?”, wide dark “Sign in” button, and “No account? Contact your administrator.” footer. Typed-character masking, link destination, form behavior and reset pages cannot be observed from a static image. |
| K | `{"source_type":"knowledge","source_id":"bcf198d8-a628-401c-8641-b726fcbd00b5","locator":"v1, chunk 0"}` | ACC-STD-01: recovery link, identical public known/unknown response, five requests/account/hour; ACC-STD-02: single-use link expiring 30 minutes from issue and all-session signout; ACC-STD-03: owner notification after every successful reset. Other identical search hits are not additional policies. |

## Proposed architecture and interfaces

Use a Python 3.12 Flask application factory with Jinja server-rendered pages, an injectable UTC clock and cryptographic token source, synthetic accounts with password hashes, one process-local locked memory store, and a **private** in-memory notification sink. `GET/POST /sign-in` creates a registry-backed authenticated session on valid credentials; `GET /account` checks registry membership and account epoch on *each* request; `POST /sign-out` removes the session. `GET/POST /forgot-password` offers the request form and one identical public `200` acknowledgement for otherwise equivalent valid known, unknown and throttled submissions. Only eligible known-account requests append private link events. `GET/POST /reset/<token>` offers a password form only while the token is unused and unexpired; the POST rechecks under the store lock, changes the hash, consumes the token, invalidates all sessions and appends one owner-addressed success event as a single successful in-memory transition. A replay or expired token does none of these.

Proposed choices, **not further standards**: normalize synthetic email identifiers consistently; use a rolling 3600-second known-account acceptance window, with the sixth request suppressed and the oldest accepted timestamp removed at the hour boundary; keep only token digests in the reset index and raw links in the private sink; interpret expiry as `now < issued_at + 30 minutes`; check CSRF on all POSTs; keep reset tokens/passwords out of public messages and logs; and give invalid/used/expired tokens one neutral state. Signed cookies carry an opaque session reference, not sole proof of authentication; the protected-route registry/epoch check invalidates *every* previously active client after a reset. Serialize sign-in session creation with reset completion to avoid a stale-password race. Sink records are locally inspectable by authorized tests or same-process demonstration code, never a public endpoint or external email. No durable migration is needed for this one-process demonstration; restarts lose state. T001 discusses alternatives and security/production limitations. Recovery/error page copy, additional password policy and authorized demonstration inspection remain open design questions, not wireframe observations.

## Dependency-ordered task drafts

Each `source_references` entry below uses the exact type, ID and locator returned by the evidence tools. Acceptance criteria are **future checks**.

### TASK-001 — Local Flask foundation

- `requirement_ids`: `["REQ-018","REQ-019","REQ-020"]`
- `depends_on`: `[]`
- `source_references`: `[{"source_type":"user_story","source_id":"user_story","locator":"characters 0-16000"}]`
- **Description:** Create the Python 3.12 Flask application factory, Jinja template/static-asset foundation, injectable UTC clock, isolated process-local memory store and synthetic hashed-account seed/fixtures. Do not connect a real identity store or production service.
- **Acceptance criteria:** (1) A documented local Python 3.12 invocation starts Flask and serves a server-rendered HTML page. (2) Two independently constructed app instances do not share synthetic accounts or mutable runtime state. (3) Inspection finds no real-account integration. This task establishes injectable state/time, not a deployed application.

### TASK-002 — Sign-in screen and revocable sessions

- `requirement_ids`: `["REQ-001","REQ-002","REQ-003","REQ-004","REQ-006","REQ-007","REQ-008","REQ-019"]`
- `depends_on`: `["TASK-001"]`
- `source_references`: `[{"source_type":"user_story","source_id":"user_story","locator":"characters 0-16000"},{"source_type":"attachment","source_id":"941402b9-bfd8-414c-a6e4-2fc2dce190a1","locator":"sign-in-wireframe.png"}]`
- **Description:** Render the pictured sign-in card and exact visible labels/placeholders/footer using semantic HTML and a local stylesheet. Implement password `type=password` (actual masking is an implementation requirement, not image-observed behavior), visible focus and associated labels; verify synthetic password hashes; protect POSTs with CSRF; create opaque registry-backed sessions with an account epoch and guarded `/account`; provide CSRF-protected sign-out. No unpictured signed-in-page appearance is asserted.
- **Acceptance criteria:** (1) `GET /sign-in` returns the outlined card on white, bold heading, labeled email with `name@example.com`, labeled password with `********` and `type=password`, blue underlined recovery link, wide dark button and exact footer. (2) Valid synthetic credentials reach an authenticated `/account` across requests; invalid credentials and CSRF failures do not. (3) A removed session or mismatched epoch fails the next protected request; a signed cookie alone does not grant access.

### TASK-003 — Private recovery request and quota

- `requirement_ids`: `["REQ-005","REQ-009","REQ-010","REQ-011","REQ-012","REQ-019","REQ-021"]`
- `depends_on`: `["TASK-001","TASK-002"]`
- `source_references`: `[{"source_type":"user_story","source_id":"user_story","locator":"characters 0-16000"},{"source_type":"attachment","source_id":"941402b9-bfd8-414c-a6e4-2fc2dce190a1","locator":"sign-in-wireframe.png"},{"source_type":"knowledge","source_id":"bcf198d8-a628-401c-8641-b726fcbd00b5","locator":"v1, chunk 0"}]`
- **Description:** Make the pictured recovery link navigate to a proposed server-rendered labeled email request form. For a syntactically valid known synthetic account, enforce a locked rolling five-accepted-requests/3600-second window, generate a cryptographically random URL-safe reset token, index only its digest and issued-at time, and record the link in a private in-memory sink. Unknown identifiers and suppressed known-account requests issue no links, but use the same public acknowledgement as accepted requests. Never display a private link or expose the sink over HTTP.
- **Acceptance criteria:** (1) The link opens `GET /forgot-password` and valid request submissions return a rendered acknowledgement. (2) Otherwise equivalent known, unknown and suppressed POSTs have identical public status, headers and body without identifier, quota or link; comparison uses equivalent CSRF/session context. (3) Five known-account requests inside the rolling hour produce five private links, the sixth produces none, and a request at the oldest acceptance's +3600-second boundary can produce a new one. (4) Unknown identifiers create no link; no external delivery occurs.

### TASK-004 — Single-use reset and atomic completion

- `requirement_ids`: `["REQ-013","REQ-014","REQ-015","REQ-016","REQ-017","REQ-019","REQ-021"]`
- `depends_on`: `["TASK-002","TASK-003"]`
- `source_references`: `[{"source_type":"user_story","source_id":"user_story","locator":"characters 0-16000"},{"source_type":"knowledge","source_id":"bcf198d8-a628-401c-8641-b726fcbd00b5","locator":"v1, chunk 0"}]`
- **Description:** Render a proposed labeled new-password form for a valid link and a neutral unavailable-link state otherwise. On POST, validate CSRF/input and recheck digest, consumption and issue-based expiry under the same lock used by session creation; complete the new password hash, consumed token, account epoch/session revocation and one private owner-addressed success event together, before returning success. Keep link/password out of public responses and logs; no external notification service.
- **Acceptance criteria:** (1) An unused link at 29:59 since issuance accepts a new password; the same link at 30:00 or later cannot update it. (2) A link permits one successful completion only, including against simultaneous/replayed submissions; failed submissions add no success event. (3) The old password ceases to sign in and the new one works after success. (4) Two or more previously authenticated, independent clients all fail the next protected request. (5) Each completed reset records exactly one owner-addressed in-memory notification, never a notification claiming external delivery.

### TASK-005 — Pytest regression suite

- `requirement_ids`: `["REQ-001","REQ-002","REQ-003","REQ-004","REQ-005","REQ-006","REQ-007","REQ-008","REQ-009","REQ-010","REQ-011","REQ-012","REQ-013","REQ-014","REQ-015","REQ-016","REQ-017","REQ-018","REQ-019","REQ-020","REQ-021","REQ-022"]`
- `depends_on`: `["TASK-002","TASK-003","TASK-004"]`
- `source_references`: `[{"source_type":"user_story","source_id":"user_story","locator":"characters 0-16000"},{"source_type":"attachment","source_id":"941402b9-bfd8-414c-a6e4-2fc2dce190a1","locator":"sign-in-wireframe.png"},{"source_type":"knowledge","source_id":"bcf198d8-a628-401c-8641-b726fcbd00b5","locator":"v1, chunk 0"}]`
- **Description:** Add independent pytest fixtures for app factory, fixed/advancing UTC clock, synthetic accounts, private sink and multiple client cookie jars. Implement TC-001 through TC-022 below as automated checks; use no sleeps, live account or network notification. Run the suite locally with `python3.12 -m pytest` after implementing the application. This is a separate **test** task: the behavior is implemented by TASK-001 through TASK-004, while REQ-022 specifically requires the runnable pytest coverage here.
- **Acceptance criteria:** (1) `python3.12 -m pytest` is documented and runs the tests for the sign-in/reset behavior under Python 3.12. (2) Tests assert both public outcomes and private effects, including five/six/boundary, before/at-expiry, replay, independent-client session invalidation and owner event per success. (3) TC-001–TC-022 collectively exercise every REQ-001–REQ-022 without pretending to test visual browser behavior from an image alone. No test is reported as passed in this draft.

### TASK-006 — Local documentation and delivery audit

- `requirement_ids`: `["REQ-018","REQ-020","REQ-021","REQ-022","REQ-023","REQ-024"]`
- `depends_on`: `["TASK-005"]`
- `source_references`: `[{"source_type":"user_story","source_id":"user_story","locator":"characters 0-16000"}]`
- **Description:** Document local Python 3.12 setup, Flask startup, `python3.12 -m pytest`, synthetic credentials and authorized same-process/private-test sink inspection. Document process-restart state loss, single-worker limits, non-durable quota/revocation, no real account or notification delivery, and missing production-grade reliability/security operations. Review the delivered repository for the explicit no-deployment constraint; do not add deployment code, workflows, instructions or perform deployment.
- **Acceptance criteria:** (1) A reviewer can follow local-only setup/testing and identify why the demo is not production-ready. (2) Inspection confirms accounts are synthetic, sink remains memory-only, and tests have a runnable command. (3) Delivery/repository inspection finds no newly added deployment workflows or deploy instructions and no deployment action is performed. REQ-023 and REQ-024 are verified by documentation/repository inspection, not claimed to require pytest.

## Per-requirement implementation and test-case plan

The `TC-NNN` labels below are proposed future verification cases, **not** existing tests. For REQ-023/024, `DOC-023` and `AUDIT-024` name review procedures rather than pytest cases. TASK-005 is the separate pytest implementation task for REQ-001–REQ-022; the “implementation task” column identifies the feature/source-of-truth task rather than counting a test as feature implementation.

| Approved requirement | Implementation task(s) | Verification case (future) |
| --- | --- | --- |
| REQ-001 | TASK-002 | TC-001: rendered sign-in HTML/CSS contains white background, centered thin outlined rectangular card and bold “Sign in” heading. |
| REQ-002 | TASK-002 | TC-002: associated “Email address” label and `name@example.com` input placeholder. |
| REQ-003 | TASK-002 | TC-003: associated “Password” label, `********` placeholder and HTML `type=password`; this verifies the standard masking control, not image evidence of typing. |
| REQ-004 | TASK-002 | TC-004: “Forgot password?” anchor is visibly specified blue and underlined in local stylesheet. |
| REQ-005 | TASK-003 | TC-005: pictured recovery anchor resolves to rendered `GET /forgot-password` request form. |
| REQ-006 | TASK-002 | TC-006: “Sign in” submit button and dark/wide stylesheet treatment. |
| REQ-007 | TASK-002 | TC-007: exact “No account? Contact your administrator.” footer beneath form/card. |
| REQ-008 | TASK-002 | TC-008: synthetic valid credentials authenticate across requests; invalid/CSRF-rejected credentials do not. |
| REQ-009 | TASK-003 | TC-009: labeled email request form accepts a syntactically valid submission and returns rendered acknowledgement. |
| REQ-010 | TASK-003 | TC-010: accepted known-account request emits private usable link; public acknowledgement contains none, link opens reset form. |
| REQ-011 | TASK-003 | TC-011: otherwise equivalent known, unknown and throttled valid submissions return identical public status, headers and body without link/existence disclosure. |
| REQ-012 | TASK-003 | TC-012: fixed clock yields five accepted known-account links, no sixth within rolling hour and one new acceptance at oldest +3600 seconds; compare public parity. |
| REQ-013 | TASK-004 | TC-013: successful link reuse and concurrent replay cannot mutate password or append a second success event. |
| REQ-014 | TASK-004 | TC-014: unused issued link works at 29:59; a separate unused link fails at exactly 30:00 and thereafter, measured from issuance not first visit. |
| REQ-015 | TASK-004 | TC-015: after valid completion, old password fails and new password signs in. |
| REQ-016 | TASK-004 | TC-016: two independent clients signed in before reset both fail the next authenticated request; a newly signed-in client can authenticate. |
| REQ-017 | TASK-004 | TC-017: exactly one owner-addressed sink success event for each committed reset; none for rejected/expired/replayed attempts. |
| REQ-018 | TASK-001, TASK-006 | TC-018: start Flask with Python 3.12 in local setup and assert test interpreter version; documentation matches the runnable invocation. |
| REQ-019 | TASK-001, TASK-002, TASK-003, TASK-004 | TC-019: GET sign-in, request and valid reset pages return complete server-rendered forms without depending on a client app. |
| REQ-020 | TASK-001, TASK-006 | TC-020: isolated synthetic-account fixtures run without external identity integrations; inspect seed/config. |
| REQ-021 | TASK-003, TASK-004, TASK-006 | TC-021: test fixture inspects in-memory link and success events; inspect routes/config for no public sink endpoint or external delivery. |
| REQ-022 | TASK-005, TASK-006 | TC-022: execute `python3.12 -m pytest`; review test collection for TC-001–TC-021 and the privacy, quota, expiry, session and notification assertions. |
| REQ-023 | TASK-006 | DOC-023: read local documentation to verify explicit non-production state, synthetic identities, process-local sink, restart/multi-worker and security/reliability limitations. |
| REQ-024 | TASK-006 | AUDIT-024: inspect delivered tracked/untracked project files and work record for no new deployment workflow/instructions and no actual deployment. This is a negative constraint, **not** a deployment task. |

**Coverage disposition proposed for the final contract:** none (`coverage_dispositions: []`), conditional on the eventual final task list and test plan preserving this complete mapping. Every approved REQ-001 through REQ-024 has an implementation/documentation task and a planned pytest or explicit documentation/repository-inspection verification. All dependencies refer only to earlier `TASK-NNN` identifiers and form a DAG. There are no `stage_output` citations, invented IDs/locators, new requirements, production integration tasks or deployment tasks.
