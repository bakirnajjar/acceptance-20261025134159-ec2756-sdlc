# Solution design — local password-reset demonstration

**Stage:** `solution_design` · **Contract schema:** `1.1` · **Status:** design and prospective implementation plan only. No application, automated test result, deployment or delivery is claimed.

## Evidence and traceability

| Key | Exact source reference | What it supports |
| --- | --- | --- |
| S | `{"source_type":"user_story","source_id":"user_story","locator":"characters 0-16000"}` | Python 3.12, Flask, server-rendered pages, pytest, synthetic accounts, an in-memory notification sink, production-limitations documentation, and no deployment or deployment workflows. |
| A | `{"source_type":"attachment","source_id":"941402b9-bfd8-414c-a6e4-2fc2dce190a1","locator":"sign-in-wireframe.png"}` | Supplied static sign-in image. The attachment reader returned a reference only; the following appearance is the user's exact observation, not a measurement of running software. |
| K | `{"source_type":"knowledge","source_id":"bcf198d8-a628-401c-8641-b726fcbd00b5","locator":"v1, chunk 0"}` | Curated account recovery standard: ACC-STD-01 (recovery link, identical public response regardless of account existence, five requests/account/hour), ACC-STD-02 (single-use links expiring 30 minutes after issue; sign out every active session), ACC-STD-03 (notify owner after every successful reset). Other search hits repeat the same text; no other architecture or technology policy is inferred. |

The approved `requirements_analysis` supplies REQ-001–REQ-024, and `ui_analysis` distinguishes observed sign-in appearance from proposed behavior. They were read by stage key without a returned source-reference locator; their IDs are predecessor links, **not** fabricated `stage_output` citations. The T001 architecture notes and T002 task crosswalk informed this plan. Only S, A and K are cited as source references, including within contract tasks.

From the user's observation of A: a white page, centered thin dark-outlined rectangular card, bold **Sign in** heading, **Email address** label/input with `name@example.com` placeholder, **Password** label/input with `********` placeholder, blue underlined **Forgot password?** link, wide dark **Sign in** button, and **No account? Contact your administrator.** footer. Actual typed-character masking, link destination and submission behavior cannot be observed in the static image. Reset screens are not pictured.

## Architecture summary

Prospective local-only Python 3.12 Flask application factory renders Jinja sign-in and recovery pages and injects a UTC clock, cryptographic token generator, locked process-local synthetic-account/session/reset store and private in-memory notification sink. A revocable server-side session registry plus account epoch guards each protected request. Recovery accepts at most five known-account requests in a rolling hour while returning the same public acknowledgement for equivalent known, unknown and suppressed submissions; eligible links use random bearer tokens, a digest-only reset index and private sink delivery. An unused token remains usable only before 30 minutes from issuance. Reset POST revalidates and atomically commits a password-hash change, one-time token consumption, revocation of all account sessions and one owner-addressed sink event. Server-rendered sign-in styling follows only the observed static image; unpictured screens are proposals. Pytest will verify routes, private effects, boundaries and multiple clients; local documentation will state process-loss, single-worker, no-email and no-deployment limitations. This is a design, not a claim that the application or tests exist.

### Components, boundaries and interaction

1. **Flask factory / composition root:** construct fresh store, sink and app per test instance; inject UTC-aware `Clock.now()` and a cryptographically strong URL-safe token source. Configure only local synthetic identities with password hashes and a documented local-only signing secret mechanism; use Jinja templates and a local stylesheet. No real directory, mail service, database, client SPA or deployment integration. [S]
2. **Identity and session service:** normalize synthetic emails consistently (trim and case-fold), verify a stored password hash, generate a new opaque session identifier and put only its digest, account ID and current `session_epoch` in the process-local registry. A signed, `HttpOnly`, `SameSite=Lax` cookie holds the opaque identifier and a per-client CSRF secret; it is not sufficient proof of authorization. Every protected request checks registry membership **and** current account epoch. Sign-out removes the registered session and clears the current cookie. Reset increments the epoch and removes all sessions for the account so other clients' old cookies fail on their next protected request. Serialize sign-in's password check and session installation with reset completion to prevent a stale-password session race. Session and CSRF mechanisms are proposed safeguards, not additional evidence from A. [S, K]
3. **Recovery service:** accept a syntactically valid email; for a known account count accepted requests with timestamps strictly newer than `now - 3600 seconds`. Under a single lock, allow up to five such requests; on an accepted request create a random bearer token and private link, index `SHA-256(token)` with account ID and UTC issuance instant, and append the link only to the private sink. At the oldest request's +3600-second boundary it ages out. Unknown or suppressed requests produce no token and no private link. All otherwise equivalent valid known, unknown and suppressed submissions return the **same `200` status, headers and rendered acknowledgement**, without identifier, quota or link; compare with equivalent CSRF/session contexts. This is public response parity, **not** a claim of constant-time behavior. [S, K]
4. **Reset service:** `GET` checks digest, single-use state and issue-based expiry without consuming the token. For `POST`, first validate CSRF and nonempty new password and prepare a password hash; then recheck validity within the same lock used for session creation and publish one in-memory state transition: replace the hash, mark token consumed, increment epoch/remove account sessions, append **one** owner-addressed notification event, and return success only after the private event is recorded. An unused token is valid only while `now < issued_at + 30 minutes`; at exactly 30:00 it is invalid. Concurrent replay/invalid input/expired link cannot change the password or emit a success event. Retain consumed token digests until their expiry; expired-record cleanup never makes them reusable. The single-process transition is not a durable outbox. [S, K]
5. **UI and private sink:** render semantic forms with `for`/`id` labels, keyboard controls, visible focus and field-associated accessible errors. Follow the observed sign-in composition precisely; `type=password` is required behavior, not proof from the image. The proposed, unpictured request page has a labeled email field and sign-in return link; valid requests show the generic acknowledgement. The proposed reset page has a labeled password field; malformed/used/expired links share a neutral unavailable-link page and fresh-request link. A neutral success page links to sign-in; `/account` is a minimal guarded result only. `MemoryNotificationSink.record_link(account_id, url, issued_at)` and `record_success(account_id, occurred_at)` are internal; only authorized local test fixtures or same-process demonstration code may inspect snapshot data. No HTTP, debug, public-log or external-email exposure of raw bearer links; success notifications do not include passwords or reset links. [S, A, K]

### Proposed HTTP and in-process contracts

| Interface | Request / validation | Public outcome and private effect |
| --- | --- | --- |
| `GET /sign-in` | Initialize anonymous CSRF secret if absent. | `200` rendered sign-in card, matching only the observed A composition. |
| `POST /sign-in` | `email`, `password`, CSRF form token; normalized synthetic lookup and hash check. | On valid credentials rotate session ID and redirect to `/account`; otherwise generic form error without password echo. CSRF rejection does not sign in. |
| `GET /account` | Cookie session ID; registry digest and account epoch checked each request. | Active account sees minimal rendered page; absent/revoked/mismatched session is refused and cleared/redirected to sign-in. |
| `POST /sign-out` | Active session and CSRF token. | Remove registry session and clear current cookie; no authentication from signed cookie alone. |
| `GET /forgot-password` | Recovery link target. | `200` server-rendered, labeled email request form. |
| `POST /forgot-password` | `email`, CSRF; syntactically valid submissions go through recovery service. | Identical `200` rendered acknowledgement, body and headers for equivalent known, unknown and throttled identifiers; eligible known requests alone produce a private link event. Invalid syntax/CSRF gets validation feedback independent of account existence. |
| `GET /reset/<token>` | URL-safe bearer token digested, looked up, checked for unconsumed/unexpired status. | Valid: `200` rendered new-password form. Otherwise neutral unavailable-link response with fresh-request path; GET does not consume a token. |
| `POST /reset/<token>` | CSRF, nonempty new password, token revalidation in locked store operation. | Exactly one completed reset changes hash, consumes token, revokes all account sessions and records one owner event **before** neutral confirmation. Expired/used/malformed token gets one neutral unavailable-link state without private mutation. |
| `MemoryNotificationSink` | Internal `record_link` and `record_success`; authorized read-only snapshot for local tests/demo. | Process-private records, no public sink route or real delivery. |

CSRF uses a random per-client secret in Flask's signed cookie plus matching hidden form field on **all POSTs**; signing is not encryption. Set `HttpOnly`/`SameSite=Lax`, and `Secure` where HTTPS is used (local HTTP cannot claim HTTPS). Apply Jinja autoescaping; avoid externally hosted assets, open redirects, tokens or passwords in responses, logs or exceptions. Token-bearing pages use `Cache-Control: no-store` and `Referrer-Policy: no-referrer`. Do not rely on Referer for CSRF. Do not infer a production-ready side-channel mitigation from identical public bodies. [S, K; safeguards are design choices]

### State and operational impact

One locked `MemoryStore` owns `accounts[normalized_email] = {id, password_hash, session_epoch}`, `sessions[SHA-256(session_id)] = {account_id, epoch}`, `reset_requests[account_id] = [accepted_issued_at...]`, `tokens[SHA-256(token)] = {account_id, issued_at, consumed}`, and private sink link/success events. Only synthetic data is seeded. Locking synchronizes quota issuance, sign-in session creation and reset commits. Tests advance injected UTC time without sleeps and use independent clients/cookie jars for full-account revocation. No database schema or migration exists for this single-process demonstration. [S, K]

Restart discards state; parallel processes would have inconsistent limits, links and revocation. A private in-memory append is not real email delivery, crash-safe persistence or a transaction with an external notification provider. Privacy-conscious local instrumentation may count accepted/suppressed/consumed/revoked transitions without logging emails, tokens or passwords; pytest inspects private sink events. Production would separately need transactional durable identity/token/session/quota storage, multi-instance synchronization, credential lifecycle management, delivery/outbox reliability, privacy/timing analysis and monitoring. **No hosting, deployment, deployment workflow or deployment instructions are part of this design.** [S]

## Significant decisions and alternatives

| Choice | Alternative considered | Reason and qualification |
| --- | --- | --- |
| Python 3.12, Flask factory, Jinja and pytest | SPA/API or persistent service | Required local server-rendered scope; factory isolation enables deterministic tests. [S] |
| Hashed synthetic accounts and process-local sink/store | Real directory, DB or SMTP | Demonstrates requested behavior without real identities or delivery; not durable or production-ready. [S] |
| Registry-backed opaque sessions and account epoch | Signed client cookie as sole authority; clear only resetter's cookie | Every old active client must fail after reset. [K] |
| Digest-indexed random reset bearer tokens; private raw links | Plaintext token index; public acknowledgement containing link | Reduces link exposure and preserves public non-disclosure. Private sink remains sensitive. [S, K] |
| Rolling 3600-second quota for known accounts | Fixed clock-hour bucket or invented unknown-account limit | Makes five/account/hour testable without boundary burst; unknown-account numeric limit is not supplied. [K; interpretation A4] |
| Lock-guarded recheck and one snapshot-like in-memory commit | Trust GET check or perform separate unlocked mutations | Prevents replay/expiry races and partial local success; no cross-process guarantee. [K] |
| One neutral invalid/used/expired-link page | Different reason-specific public errors | Avoids link-state disclosure; copy is unpictured and subject to review. [K; proposed] |
| Nonempty new-password baseline with hashing | Mandate unspecified complexity rule | Avoids inventing a normative policy; additional policy remains an open question. [S; proposed] |
| Same `200` acknowledgement for valid known/unknown/suppressed submissions | Different status, redirect or flash for suppressed/unknown | Verifiable public status/body/header parity; not a timing guarantee. [K] |

## Assumptions and open questions

These are design assumptions, not quotations from the standard:

- **A1.** Synthetic credentials may sign in to demonstrate revocable sessions; no particular account list, password policy beyond a usable new password, or signed-in content is specified.
- **A2.** Consistently normalized email identifies a synthetic account. Only the static sign-in composition is observed; reset, error, success and authenticated screens and their copy are proposed, not pictured.
- **A3.** Authorized local tests or same-process demonstration code inspect reset links and successful-reset events in a private in-memory sink; no real email or public link inspection endpoint exists.
- **A4.** Interpret five reset requests per account per hour as a rolling 3600-second window of accepted requests for each known synthetic account; do not infer a numeric quota for unknown identifiers.
- **A5.** Interpret expiry as usable while now is strictly earlier than issued_at plus 30 minutes and invalid at or after that instant; this boundary convention is a design interpretation.
- **A6.** One process and one isolated in-memory store are the local demonstration boundary. A restart loses accounts' mutable state, sessions, quotas, tokens and notifications; neither persistence nor multi-worker coordination is promised.

All questions are **non-blocking** for this proposed local prototype:

1. What exact layout and copy should the unpictured recovery, invalid-link, success and minimal authenticated screens use? Only the supplied static sign-in card is observed; proposed pages remain subject to review.
2. Is a password policy beyond a nonempty new password required, and what minimal signed-in result should be approved? No additional password policy or post-sign-in UX was supplied.
3. Should invalid, used and expired links share the proposed neutral error copy? The standard sets link lifetime and single use, but not public error wording.
4. What authorized same-process sink inspection procedure, accessible validation copy and progress treatment should local demonstrators use? Inspection cannot expose bearer links through an HTTP page or public logs.
5. If production use is separately scoped, who owns durability, multi-instance limits and revocation, timing/privacy review, secret rotation, reliable delivery and monitoring? The requested application is a local demonstration; no deployment is authorized.

## Implementation tasks (prospective, dependency ordered)

`TASK-NNN` identifies future implementation work, not this document's T003 or work already completed. Acceptance criteria are **future checks**. The source keys expand to the exact triples above.

### TASK-001 — Local Flask foundation

- **Requirement IDs:** `REQ-018`, `REQ-019`, `REQ-020`
- **Depends on:** none
- **Source references:** S
- **Description:** Create the Python 3.12 Flask application factory, Jinja template/static-asset foundation, injectable UTC clock, isolated process-local memory store and synthetic hashed-account seed/fixtures. Do not connect a real identity store or production service.
- **Acceptance criteria:**
  1. A documented local Python 3.12 invocation starts Flask and serves a server-rendered HTML page.
  2. Two independently constructed app instances do not share synthetic accounts or mutable runtime state.
  3. Inspection finds no real-account integration; this task establishes injectable state/time, not a deployed application.

### TASK-002 — Sign-in screen and revocable sessions

- **Requirement IDs:** `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`, `REQ-006`, `REQ-007`, `REQ-008`, `REQ-019`
- **Depends on:** `TASK-001`
- **Source references:** S, A
- **Description:** Render the pictured sign-in card and exact visible labels/placeholders/footer using semantic HTML and a local stylesheet. Implement password type=password (actual masking is an implementation requirement, not image-observed behavior), visible focus and associated labels; verify synthetic password hashes; protect POSTs with CSRF; create opaque registry-backed sessions with an account epoch and guarded /account; provide CSRF-protected sign-out. No unpictured signed-in-page appearance is asserted.
- **Acceptance criteria:**
  1. GET /sign-in returns the outlined card on white, bold heading, labeled email with name@example.com, labeled password with ******** and type=password, blue underlined recovery link, wide dark button and exact footer.
  2. Valid synthetic credentials reach an authenticated /account across requests; invalid credentials and CSRF failures do not.
  3. A removed session or mismatched epoch fails the next protected request; a signed cookie alone does not grant access.

### TASK-003 — Private recovery request and quota

- **Requirement IDs:** `REQ-005`, `REQ-009`, `REQ-010`, `REQ-011`, `REQ-012`, `REQ-019`, `REQ-021`
- **Depends on:** `TASK-001`, `TASK-002`
- **Source references:** S, A, K
- **Description:** Make the pictured recovery link navigate to a proposed server-rendered labeled email request form. For a syntactically valid known synthetic account, enforce a locked rolling five-accepted-requests/3600-second window, generate a cryptographically random URL-safe reset token, index only its digest and issued-at time, and record the link in a private in-memory sink. Unknown identifiers and suppressed known-account requests issue no links, but use the same public acknowledgement as accepted requests. Never display a private link or expose the sink over HTTP.
- **Acceptance criteria:**
  1. The link opens GET /forgot-password and valid request submissions return a rendered acknowledgement.
  2. Otherwise equivalent known, unknown and suppressed POSTs have identical public status, headers and body without identifier, quota or link; comparison uses equivalent CSRF/session context.
  3. Five known-account requests inside the rolling hour produce five private links, the sixth produces none, and a request at the oldest acceptance's +3600-second boundary can produce a new one.
  4. Unknown identifiers create no link; no external delivery occurs.

### TASK-004 — Single-use reset and atomic completion

- **Requirement IDs:** `REQ-013`, `REQ-014`, `REQ-015`, `REQ-016`, `REQ-017`, `REQ-019`, `REQ-021`
- **Depends on:** `TASK-002`, `TASK-003`
- **Source references:** S, K
- **Description:** Render a proposed labeled new-password form for a valid link and a neutral unavailable-link state otherwise. On POST, validate CSRF/input and recheck digest, consumption and issue-based expiry under the same lock used by session creation; complete the new password hash, consumed token, account epoch/session revocation and one private owner-addressed success event together, before returning success. Keep link/password out of public responses and logs; no external notification service.
- **Acceptance criteria:**
  1. An unused link at 29:59 since issuance accepts a new password; a separate unused link at 30:00 or later cannot update it.
  2. A link permits one successful completion only, including against simultaneous/replayed submissions; failed submissions add no success event.
  3. The old password ceases to sign in and the new one works after success.
  4. Two or more previously authenticated, independent clients all fail the next protected request.
  5. Each completed reset records exactly one owner-addressed in-memory notification, never a notification claiming external delivery.

### TASK-005 — Pytest regression suite

- **Requirement IDs:** `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`, `REQ-005`, `REQ-006`, `REQ-007`, `REQ-008`, `REQ-009`, `REQ-010`, `REQ-011`, `REQ-012`, `REQ-013`, `REQ-014`, `REQ-015`, `REQ-016`, `REQ-017`, `REQ-018`, `REQ-019`, `REQ-020`, `REQ-021`, `REQ-022`
- **Depends on:** `TASK-002`, `TASK-003`, `TASK-004`
- **Source references:** S, A, K
- **Description:** Add independent pytest fixtures for app factory, fixed/advancing UTC clock, synthetic accounts, private sink and multiple client cookie jars. Implement TC-001 through TC-022 in the Markdown verification matrix as automated checks; use no sleeps, live account or network notification. Run the suite locally with python3.12 -m pytest after implementing the application. This is a separate test task: TASK-001 through TASK-004 implement behavior and REQ-022 requires runnable pytest coverage here.
- **Acceptance criteria:**
  1. python3.12 -m pytest is documented and runs the tests for the sign-in/reset behavior under Python 3.12.
  2. Tests assert both public outcomes and private effects, including five/six/boundary, before/at-expiry, replay, independent-client session invalidation and owner event per success.
  3. TC-001–TC-022 collectively exercise every REQ-001–REQ-022 without pretending to test visual browser behavior from an image alone; no test is reported as passed in this design.

### TASK-006 — Local documentation and delivery audit

- **Requirement IDs:** `REQ-018`, `REQ-020`, `REQ-021`, `REQ-022`, `REQ-023`, `REQ-024`
- **Depends on:** `TASK-005`
- **Source references:** S
- **Description:** Document local Python 3.12 setup, Flask startup, python3.12 -m pytest, synthetic credentials and authorized same-process/private-test sink inspection. Document process-restart state loss, single-worker limits, non-durable quota/revocation, no real account or notification delivery, and missing production-grade reliability/security operations. Review the delivered repository for the explicit no-deployment constraint; do not add deployment code, workflows, instructions or perform deployment.
- **Acceptance criteria:**
  1. A reviewer can follow local-only setup/testing and identify why the demo is not production-ready.
  2. Inspection confirms accounts are synthetic, sink remains memory-only, and tests have a runnable command.
  3. Delivery/repository inspection finds no newly added deployment workflows or deploy instructions and no deployment action is performed; REQ-023 and REQ-024 are verified by documentation/repository inspection, not claimed to require pytest.

### Requirement → implementation task → planned verification

The cases below are a **plan**: no pytest suite or test run is asserted. TASK-005 implements the checks for REQ-001–REQ-022; the middle column identifies the feature/documentation task rather than treating the test task as feature implementation. REQ-023 and REQ-024 are explicit document/audit checks, not pytest cases.

| Requirement | Implementing task(s) | Future verification |
| --- | --- | --- |
| REQ-001 | TASK-002 | TC-001: rendered sign-in HTML/CSS contains white background, centered thin outlined rectangular card and bold “Sign in” heading. |
| REQ-002 | TASK-002 | TC-002: associated “Email address” label and `name@example.com` input placeholder. |
| REQ-003 | TASK-002 | TC-003: associated “Password” label, `********` placeholder and HTML `type=password`; this verifies the masking control, not image evidence of typing. |
| REQ-004 | TASK-002 | TC-004: “Forgot password?” anchor is specified blue and underlined in the local stylesheet. |
| REQ-005 | TASK-003 | TC-005: pictured recovery anchor resolves to rendered `GET /forgot-password` request form. |
| REQ-006 | TASK-002 | TC-006: “Sign in” submit button and dark/wide stylesheet treatment. |
| REQ-007 | TASK-002 | TC-007: exact “No account? Contact your administrator.” footer beneath form/card. |
| REQ-008 | TASK-002 | TC-008: synthetic valid credentials authenticate across requests; invalid/CSRF-rejected credentials do not. |
| REQ-009 | TASK-003 | TC-009: labeled email request form accepts syntactically valid submission and returns rendered acknowledgement. |
| REQ-010 | TASK-003 | TC-010: accepted known-account request emits private usable link; public acknowledgement contains none, link opens reset form. |
| REQ-011 | TASK-003 | TC-011: equivalent known, unknown and throttled valid submissions return identical public status, headers and body without link/existence disclosure. |
| REQ-012 | TASK-003 | TC-012: fixed clock yields five accepted known-account links, no sixth inside rolling hour and new acceptance at oldest +3600 seconds; public parity remains. |
| REQ-013 | TASK-004 | TC-013: successful-link reuse and concurrent replay cannot mutate password or append a second success event. |
| REQ-014 | TASK-004 | TC-014: unused issued link works at 29:59; a separate unused link fails at exactly 30:00 and later, measured from issuance. |
| REQ-015 | TASK-004 | TC-015: after valid completion, old password fails and new password signs in. |
| REQ-016 | TASK-004 | TC-016: two independent clients signed in before reset both fail next authenticated request; a newly signed-in client succeeds. |
| REQ-017 | TASK-004 | TC-017: exactly one owner-addressed sink success event for each committed reset; none for rejected/expired/replayed attempts. |
| REQ-018 | TASK-001, TASK-006 | TC-018: start Flask with Python 3.12 locally, assert interpreter version and verify documented invocation. |
| REQ-019 | TASK-001, TASK-002, TASK-003, TASK-004 | TC-019: GET sign-in, request and valid reset pages return complete server-rendered forms without a client app. |
| REQ-020 | TASK-001, TASK-006 | TC-020: isolated synthetic-account fixtures run without external identity integration; inspect seed/config. |
| REQ-021 | TASK-003, TASK-004, TASK-006 | TC-021: test fixture inspects in-memory link/success events; inspect routes/config for no public sink endpoint or external delivery. |
| REQ-022 | TASK-005, TASK-006 | TC-022: execute `python3.12 -m pytest`; review collection for TC-001–TC-021 plus privacy, quota, expiry, session and notification assertions. |
| REQ-023 | TASK-006 | DOC-023: review local documentation for non-production status, synthetic accounts, process-local sink, restart/multi-worker and security/reliability limitations. |
| REQ-024 | TASK-006 | AUDIT-024: inspect delivered tracked/untracked files and work record for no new deployment workflow/instructions and no deployment action; this is a negative constraint, not a deployment task. |

Every REQ-001–REQ-024 has implementation/documentation ownership and a future test or inspection. Accordingly `coverage_dispositions` is `[]`. The listed `depends_on` edges refer only to earlier tasks and form an acyclic graph.

## Prospective quality gates and hosting

- **Hosting:** `none` — local execution only; do not provision hosting, deploy, or add deployment workflows or instructions.
- **Technology:** `languages: ["Python 3.12"]`; `frameworks: ["Flask", "Jinja", "pytest"]`; `runtime: "Single local Python 3.12 process"`.
- **Build:** `[]`; no project build command exists yet.
- **Test:** `["python3.12 -m pytest"]`, to be run after the implementation and suite are created. **Not run for this design-only task.**
- **Lint:** `[]`; no project lint command exists yet.
