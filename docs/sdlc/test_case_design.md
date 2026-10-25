# Password-reset test case design

**Status:** Proposed verification only. No scenario has been executed or reported passing. TC-001–TC-022 are future pytest candidates, with supplemental browser/repository inspection where stated; TC-023 and TC-024 are inspection-only, not pytest.

## Evidence and traceability

- **S — user story:** `{"source_type":"user_story","source_id":"user_story","locator":"characters 0-8000"}` — local Python 3.12 Flask, server-rendered pages, synthetic accounts, in-memory sink, pytest, documentation and no deployment.
- **A — sign-in wireframe:** `{"source_type":"attachment","source_id":"941402b9-bfd8-414c-a6e4-2fc2dce190a1","locator":"sign-in-wireframe.png"}` — white page, thin dark outlined card, bold Sign in, Email address/name@example.com, Password/********, blue underlined Forgot password?, wide dark Sign in button and No account? Contact your administrator. Static appearance only.
- **K — account recovery standard:** `{"source_type":"knowledge","source_id":"bcf198d8-a628-401c-8641-b726fcbd00b5","locator":"v1, chunk 0"}` — ACC-STD-01 identical known/unknown public response and five per-account requests/hour; ACC-STD-02 single use, 30-minute issue-based expiry and all-session sign-out; ACC-STD-03 owner notification after every successful reset.

REQ IDs come from approved requirements analysis; TASK IDs from approved solution design (informed by UI analysis). Prior stage readers supplied no source-reference locator, so these are traceability links rather than fabricated stage-output citations. S/A/K are the exact authorized source references carried into the JSON contract. All named routes are design targets, not evidence of an existing application. Use isolated app fixtures, fixed/advancing UTC time, synthetic accounts, independent cookie jars and a private same-process sink; never expose reset links/events over public HTTP or send real email.

## Test cases

### TC-001 — Sign-in card and heading

**Trace:** REQ-001; TASK-002, TASK-005. **Mode:** pytest candidate for HTML/CSS, plus browser visual/accessibility inspection. **Evidence:** S, A.

**Preconditions:** An isolated local app is available to an anonymous client.

**Test data:** GET `/sign-in`; pictured wireframe A.

**Steps**
1. Preconditions: An isolated local app is available to an anonymous client. Test data: GET `/sign-in`; pictured wireframe A. Action: Request `/sign-in` without authenticating and parse the returned HTML and local stylesheet.
2. Locate the semantic “Sign in” heading and its surrounding rectangular card; inspect page background, outline and centering declarations.
3. Compare the rendered page at a normal desktop viewport with A; check that the heading and outline are perceivable and readable.

**Expected results**
1. Response succeeds with server-supplied HTML containing the card and one prominent “Sign in” heading.
2. Local styling specifies a white page and centered, thin dark outlined rectangular card; the heading is inside it.
3. Human/browser inspection confirms the pictured composition and readable contrast. HTML/CSS assertions alone are **partial**, not proof of pixel fidelity or accessibility.

### TC-002 — Labeled sign-in email field

**Trace:** REQ-002; TASK-002, TASK-005. **Mode:** pytest candidate for markup, plus browser accessibility inspection. **Evidence:** A.

**Preconditions:** Anonymous sign-in page is reachable.

**Test data:** exact label `Email address`; exact placeholder `name@example.com`.

**Steps**
1. Preconditions: Anonymous sign-in page is reachable. Test data: exact label `Email address`; exact placeholder `name@example.com`. Action: GET `/sign-in` and locate the email input and its associated label.
2. Parse the control's `type`, placeholder and label relationship; tab to it in a browser.

**Expected results**
1. The server response contains an editable email control with visible `Email address` text and `name@example.com` placeholder.
2. The label is programmatically associated with the control, its accessible name is “Email address,” and keyboard focus is visible; a placeholder alone does not count as a label.

### TC-003 — Pictured password field versus runtime masking

**Trace:** REQ-003; TASK-002, TASK-005. **Mode:** pytest candidate for markup and response privacy; browser interaction inspection for masking. **Evidence:** A.

**Preconditions:** Anonymous sign-in form is reachable.

**Test data:** exact `Password` label and `********` placeholder; distinct sample password `DemoSecret!`.

**Steps**
1. Preconditions: Anonymous sign-in form is reachable. Test data: exact `Password` label and `********` placeholder; distinct sample password `DemoSecret!`. Action: GET `/sign-in`; inspect the password label association, exact placeholder and `type="password"` markup.
2. In a browser, tab to the field, type `DemoSecret!` and inspect the displayed input.
3. Submit an invalid sign-in and inspect the response body and visible validation.

**Expected results**
1. The field has an associated “Password” label, the literal `********` placeholder and password-type markup.
2. Typed `DemoSecret!` is not displayed as literal characters; the field is keyboard operable and focus perceivable. This runtime behavior is a proposed requirement, **not** a conclusion from A.
3. The response does not echo `DemoSecret!` in HTML or error text, and a user can perceive that sign-in failed without exposing the password.

### TC-004 — Recovery link appearance and semantics

**Trace:** REQ-004; TASK-002, TASK-005. **Mode:** pytest candidate for markup/CSS, plus browser visual/accessibility inspection. **Evidence:** A, K.

**Preconditions:** Anonymous sign-in page is reachable.

**Test data:** exact text `Forgot password?`.

**Steps**
1. Preconditions: Anonymous sign-in page is reachable. Test data: exact text `Forgot password?`. Action: GET `/sign-in` and locate the anchor bearing the exact text.
2. Inspect anchor semantics and local style for blue underlined presentation; tab to the anchor and inspect rendered contrast/focus.

**Expected results**
1. One visible, keyboard-focusable anchor reads “Forgot password?” rather than noninteractive decorative text.
2. The rendered link is blue and underlined, has a visible focus state and readable contrast; stylesheet assertions are only partial visual evidence. Its destination is verified separately in TC-005.

### TC-005 — Recovery navigation is available anonymously

**Trace:** REQ-005; TASK-003, TASK-005. **Mode:** pytest candidate, plus keyboard navigation inspection. **Evidence:** A, K.

**Preconditions:** Anonymous client at `/sign-in`.

**Test data:** link `href` extracted from the rendered “Forgot password?” anchor.

**Steps**
1. Preconditions: Anonymous client at `/sign-in`. Test data: link `href` extracted from the rendered “Forgot password?” anchor. Action: Extract and follow that anchor as an unauthenticated client.
2. Inspect the returned page for a server-rendered reset-request form and labeled email control; activate the link with keyboard in a browser.

**Expected results**
1. The link stays within the local application and opens the reset-request page without a prior session; it does not navigate to an external service or disclose a private sink.
2. The response contains a usable email request form, and keyboard activation reaches it. Navigation is proposed flow behavior, not observed in the static wireframe.

### TC-006 — Sign-in submit control

**Trace:** REQ-006; TASK-002, TASK-005. **Mode:** pytest candidate for markup/CSS, plus browser visual/accessibility inspection. **Evidence:** A.

**Preconditions:** Anonymous sign-in form is reachable.

**Test data:** exact button text `Sign in`.

**Steps**
1. Preconditions: Anonymous sign-in form is reachable. Test data: exact button text `Sign in`. Action: GET `/sign-in` and locate the sign-in form's submit button and local styles.
2. Inspect rendered width, dark fill, readable text contrast and keyboard focus; submit the form with the keyboard.

**Expected results**
1. A genuine submit button reads “Sign in”; stylesheet specifies wide dark presentation.
2. Browser rendering is visibly wide/dark with readable contrast, visible focus and keyboard submission. Markup/CSS assertions do not alone prove rendered appearance or operation.

### TC-007 — Footer text and placement

**Trace:** REQ-007; TASK-002, TASK-005. **Mode:** pytest candidate for markup placement, plus visual inspection. **Evidence:** A.

**Preconditions:** Anonymous sign-in page is reachable.

**Test data:** exact sentence `No account? Contact your administrator.`

**Steps**
1. Preconditions: Anonymous sign-in page is reachable. Test data: exact sentence `No account? Contact your administrator.` Action: GET `/sign-in` and find the exact sentence in parsed DOM.
2. Inspect DOM order and browser rendering relative to the sign-in form/card.

**Expected results**
1. The complete text, including punctuation, occurs visibly beneath the form/card, not as a placeholder or hidden element.
2. Browser inspection confirms readable placement below the controls; no unpictured contact route is required.

### TC-008 — Synthetic sign-in creates a revocable authenticated session

**Trace:** REQ-008; TASK-002, TASK-005. **Mode:** pytest candidate; browser validation inspection. **Evidence:** S.

**Preconditions:** Fresh app with one configured synthetic hashed-password account and CSRF-protected sign-in; `/account` is guarded.

**Test data:** that account's valid email/password; wrong password, unknown email and invalid/missing CSRF.

**Steps**
1. Preconditions: Fresh app with one configured synthetic hashed-password account and CSRF-protected sign-in; `/account` is guarded. Test data: that account's valid email/password; wrong password, unknown email and invalid/missing CSRF. Action: GET the form and POST valid credentials with valid CSRF; use the same cookie jar to GET `/account`.
2. In separate clean clients try wrong password, unknown email and missing/invalid CSRF; request `/account` after each.
3. Remove the first client's session registry entry or change its account epoch using an isolated fixture; retry `/account` with the original cookie.

**Expected results**
1. The authenticated client can access `/account` across requests; a mere cookie presence is not the success criterion.
2. All three invalid submissions fail to grant access to `/account`, disclose no supplied password in response, and expose an understandable error.
3. The stale cookie cannot authorize the next protected request: the guard rejects/redirects it as unauthenticated.

### TC-009 — Labeled account-email reset request

**Trace:** REQ-009; TASK-003, TASK-005. **Mode:** pytest candidate, plus browser validation/accessibility inspection. **Evidence:** S, K.

**Preconditions:** Fresh app and anonymous request client with a CSRF token.

**Test data:** valid synthetic email; empty email; malformed email; invalid/missing CSRF.

**Steps**
1. Preconditions: Fresh app and anonymous request client with a CSRF token. Test data: valid synthetic email; empty email; malformed email; invalid/missing CSRF. Action: GET `/forgot-password`, parse the server-supplied email label, editable field, CSRF field and submit action.
2. Submit a syntactically valid email with valid CSRF.
3. On isolated fixtures submit each invalid input/CSRF variant; inspect private link count before and after and browser validation/focus.

**Expected results**
1. The visitor can focus a programmatically labeled account-email field and submit the form without JavaScript.
2. A rendered generic acknowledgement is returned, without a link or account-existence claim.
3. Invalid/missing input or CSRF produces no reset link and no successful reset request; validation is perceivable and keyboard-accessible. No unspecified exact error copy is asserted.

### TC-010 — Eligible known request issues private usable link

**Trace:** REQ-010; TASK-003, TASK-005. **Mode:** pytest candidate. **Evidence:** S, K.

**Preconditions:** Fresh app, private same-process sink fixture, known synthetic account below quota and controlled UTC clock.

**Test data:** known normalized email and a separate unknown valid-format email; valid CSRF for each request.

**Steps**
1. Preconditions: Fresh app, private same-process sink fixture, known synthetic account below quota and controlled UTC clock. Test data: known normalized email and a separate unknown valid-format email; valid CSRF for each request. Action: Record sink count; POST a known email to `/forgot-password`, then privately obtain the added link.
2. Follow that link before expiry as an anonymous client.
3. Inspect public POST status/headers/body and accessible routes for bearer-link or sink disclosure; submit the unknown email in a comparable fixture.

**Expected results**
1. Exactly one additional private reset-link event exists for the known account; its link is not empty.
2. The private link opens the account's server-rendered new-password form before expiry.
3. Neither acknowledgement nor public headers/endpoint publishes the link or token; the unknown account adds zero links. No external delivery is invoked.

### TC-011 — Known, unknown and throttled public parity

**Trace:** REQ-011; TASK-003, TASK-005. **Mode:** pytest candidate. **Evidence:** K.

**Preconditions:** Isolated equivalent request contexts, same HTTP method, valid-format normalized email inputs, valid CSRF/session state and controlled time; quota state prepared privately for the throttled branch.

**Test data:** eligible known account A, unknown valid-format account U, already-five-accepted known account A in a comparable fixture.

**Steps**
1. Preconditions: Isolated equivalent request contexts, same HTTP method, valid-format normalized email inputs, valid CSRF/session state and controlled time; quota state prepared privately for the throttled branch. Test data: eligible known account A, unknown valid-format account U, already-five-accepted known account A in a comparable fixture. Action: Capture the full public response to an eligible known request, including status, public headers (including redirect target when present) and body.
2. Capture responses to otherwise equivalent unknown and throttled requests with comparable CSRF/session context; compare all public components without normalizing away account-dependent differences.
3. Inspect the sink in each isolated fixture separately, not through public HTTP.

**Expected results**
1. The known request returns a generic acknowledgement without email, quota state, token or link.
2. Known, unknown and throttled responses have equal status, public headers/redirect destination and body; no existence/limit distinction is revealed. No timing-equality threshold is invented.
3. The eligible known branch adds one private link, the unknown and suppressed branches add zero; public parity must **not** be inferred from equal sink contents.

### TC-012 — Five accepted per known account in a rolling hour

**Trace:** REQ-012; TASK-003, TASK-005. **Mode:** pytest candidate. **Evidence:** K.

**Preconditions:** Fresh isolated app, locked known-account quota, controllable UTC clock and private sink.

**Test data:** known account A, independently seeded known account B; five requests for A accepted at `t0` (or distinct instants sharing the same oldest `t0`).

**Steps**
1. Preconditions: Fresh isolated app, locked known-account quota, controllable UTC clock and private sink. Test data: known account A, independently seeded known account B; five requests for A accepted at `t0` (or distinct instants sharing the same oldest `t0`). Action: With valid CSRF, submit five requests for A from `t0`; count only accepted private links.
2. At `t0 + 3599 seconds`, submit A's sixth request; compare its public response with the accepted acknowledgement and count sink links again.
3. At `t0 + 3600 seconds`, submit A's next request; count sink links.
4. In parallel/independent state, submit a request for B before B reaches its own limit.

**Expected results**
1. Five requests yield exactly five private links for A.
2. The sixth yields **zero additional** links, leaving A at five; its status, headers and body remain the same as the generic eligible/unknown response.
3. At the oldest acceptance +3600 boundary, one request can be accepted, raising the private link count to six overall while maintaining at most five accepted in the current rolling 3600-second window.
4. B's eligible request adds its own private link without consuming A's quota. No numeric unknown-account quota is imposed.

### TC-013 — Single-use and concurrent replay

**Trace:** REQ-013; TASK-004, TASK-005. **Mode:** pytest candidate. **Evidence:** K.

**Preconditions:** Fresh known account, private link fixture, valid CSRF and controlled clock before expiry.

**Test data:** original password `Old!demo`, new passwords `First!demo`, `Second!demo`; a separate fresh link/isolated fixture for concurrent POSTs.

**Steps**
1. Preconditions: Fresh known account, private link fixture, valid CSRF and controlled clock before expiry. Test data: original password `Old!demo`, new passwords `First!demo`, `Second!demo`; a separate fresh link/isolated fixture for concurrent POSTs. Action: Privately obtain a fresh token; submit one valid reset POST with `First!demo`, then replay the same link with `Second!demo`.
2. Verify credentials and count owner-success events before/after replay.
3. With a separately issued unused link, coordinate two simultaneous valid reset POSTs carrying different passwords; record both outcomes, final accepted password and success-event count.

**Expected results**
1. First submission succeeds; replay is rejected or reaches an unavailable-link state and cannot complete a second reset.
2. `First!demo` remains the accepted password, `Second!demo` is not accepted from the replay, and replay adds zero owner-success events.
3. Exactly one concurrent submission can succeed and exactly one success event is recorded; the final accepted password equals the **single** winner's submitted value, not both. Failed attempts do not mutate account credentials.

### TC-014 — Expiry measured from issuance at both boundaries

**Trace:** REQ-014; TASK-004, TASK-005. **Mode:** pytest candidate. **Evidence:** K.

**Preconditions:** Controlled UTC clock, known synthetic account and valid CSRF; separate isolated fixtures or independent unused links so the successful boundary check cannot consume the expired-case token.

**Test data:** issuance time `t0`; candidate passwords `Before!demo` and `At!demo`.

**Steps**
1. Preconditions: Controlled UTC clock, known synthetic account and valid CSRF; separate isolated fixtures or independent unused links so the successful boundary check cannot consume the expired-case token. Test data: issuance time `t0`; candidate passwords `Before!demo` and `At!demo`. Action: Issue a link at `t0`, keep it unused, advance to `t0 + 29:59` and submit a valid reset with `Before!demo`.
2. In an independent fixture issue another link at `t0`, keep it unused, advance to exactly `t0 + 30:00` and submit with `At!demo`; retry later.
3. Open a third valid form at +29:59, advance to +30:00 before POST and submit to test POST-time revalidation.

**Expected results**
1. The pre-expiry link completes the reset and `Before!demo` becomes the accepted password.
2. The **separate unused** link is rejected exactly at issuance +1800 seconds and later; `At!demo` never becomes the password and no success notification is created.
3. A form opened before expiry cannot bypass expiry at submission. Expiry is never extended by GET or measured from page-open time.

### TC-015 — Valid reset updates password; invalid submissions do not

**Trace:** REQ-015; TASK-004, TASK-005. **Mode:** pytest candidate, plus browser form/accessibility inspection. **Evidence:** S, K.

**Preconditions:** Fresh synthetic account, valid unexpired unused private link and CSRF-protected reset form.

**Test data:** old password `Old!demo`, distinct nonempty new password `New!demo`; missing password, missing/invalid CSRF and invalid token in independent fixtures.

**Steps**
1. Preconditions: Fresh synthetic account, valid unexpired unused private link and CSRF-protected reset form. Test data: old password `Old!demo`, distinct nonempty new password `New!demo`; missing password, missing/invalid CSRF and invalid token in independent fixtures. Action: GET the valid link and inspect associated new-password label, password-type control and CSRF token; submit `New!demo` with valid CSRF.
2. Sign in from clean clients using first `Old!demo`, then `New!demo`; inspect the reset confirmation for password/link disclosure.
3. In separate untouched fixtures submit missing password, invalid/missing CSRF and invalid token; compare stored credential outcome, private success events and browser error/focus behavior.

**Expected results**
1. An editable, labeled masked new-password form is server-rendered; valid submission gives a neutral success confirmation.
2. Old credentials no longer authorize sign-in; new credentials do; confirmation contains neither the password nor bearer link.
3. Each invalid attempt leaves the previously valid password unchanged, creates no success event and displays a perceivable error or neutral unavailable state. Only nonempty new input is assumed; no unsupported maximum length or additional policy is tested.

### TC-016 — Reset invalidates every independent active session

**Trace:** REQ-016; TASK-004, TASK-005. **Mode:** pytest candidate. **Evidence:** K.

**Preconditions:** App with known synthetic account A and separate account B, session registry/epoch guard and valid reset link for A.

**Test data:** two independent cookie jars `A1`/`A2`, third reset client, B's own cookie jar.

**Steps**
1. Preconditions: App with known synthetic account A and separate account B, session registry/epoch guard and valid reset link for A. Test data: two independent cookie jars `A1`/`A2`, third reset client, B's own cookie jar. Action: Sign into A separately with `A1` and `A2`; prove each can GET guarded `/account`. Sign into B and prove B access.
2. Through the third client complete one valid reset for A.
3. Retry `/account` with each old cookie jar, then with B's jar for comparison.

**Expected results**
1. Both A clients were independently authenticated before reset, rather than sharing a single cookie.
2. The reset completes once.
3. **Both** previously active A clients fail authentication on their next protected request; B remains authenticated. Revoking only the resetter's session is insufficient.

### TC-017 — Exactly one owner notification for each successful reset

**Trace:** REQ-017; TASK-004, TASK-005. **Mode:** pytest candidate. **Evidence:** S, K.

**Preconditions:** Fresh synthetic owner, private same-process notification sink, controllable clock and sufficient request quota.

**Test data:** two distinct fresh links for two sequential successful resets; replay, invalid and expired links as failure controls.

**Steps**
1. Preconditions: Fresh synthetic owner, private same-process notification sink, controllable clock and sufficient request quota. Test data: two distinct fresh links for two sequential successful resets; replay, invalid and expired links as failure controls. Action: Record the count of **successful-reset notification events**, excluding link-request events; complete the first reset and privately inspect new events.
2. Privately issue and complete a second fresh reset; inspect event count and each recipient.
3. Replay a consumed link and try invalid/expired links; recheck success-event count and public HTML.

**Expected results**
1. The first completion adds exactly one owner-addressed success event in the memory sink.
2. The second completion adds exactly one more, for two total; both recipients match that synthetic account's owner and neither event claims external delivery.
3. Failure controls add **zero** success events, and no private notification data or bearer link appears in public HTML.

### TC-018 — Documented Python 3.12 Flask local startup

**Trace:** REQ-018; TASK-001, TASK-005, TASK-006. **Mode:** pytest/import smoke candidate plus local documentation inspection. **Evidence:** S.

**Preconditions:** Fresh local Python 3.12 environment with the project's documented dependencies; no hosting.

**Test data:** documented local start/import command and GET requests for sign-in and recovery pages.

**Steps**
1. Preconditions: Fresh local Python 3.12 environment with the project's documented dependencies; no hosting. Test data: documented local start/import command and GET requests for sign-in and recovery pages. Action: Review the local-only setup/start instructions and declare/verify the Python interpreter version is 3.12.
2. Follow those instructions to import/start the Flask app factory locally; GET `/sign-in` and `/forgot-password` using its test client.

**Expected results**
1. Instructions identify a usable Python 3.12 local invocation, without a deployment prerequisite.
2. Factory imports/starts without startup error and Flask serves HTML responses containing sign-in and reset-request forms. This is a future check, not a claim startup has already succeeded.

### TC-019 — Pages and state are server-rendered

**Trace:** REQ-019; TASK-001, TASK-002, TASK-003, TASK-004, TASK-005. **Mode:** pytest candidate for response HTML, browser no-JavaScript inspection. **Evidence:** S.

**Preconditions:** Local app and fixtures with a privately issued valid reset link, valid CSRF and clean clients.

**Test data:** sign-in, reset-request, valid new-password, validation/error and success responses.

**Steps**
1. Preconditions: Local app and fixtures with a privately issued valid reset link, valid CSRF and clean clients. Test data: sign-in, reset-request, valid new-password, validation/error and success responses. Action: GET `/sign-in`, `/forgot-password` and the valid private link; parse response bodies without running scripts.
2. Submit representative valid and invalid forms and inspect returned server HTML/redirect destinations; repeat form navigation with browser JavaScript disabled.

**Expected results**
1. Responses already contain usable headings, associated fields, form actions and CSRF controls for each requested page; no client-rendered bootstrap is needed to expose content.
2. Generic acknowledgement, reset confirmation or perceivable error content can be reached without a client-rendered app. Browser inspection validates practical non-JavaScript operation; only sign-in appearance is pictured.

### TC-020 — Synthetic accounts and isolated app state

**Trace:** REQ-020; TASK-001, TASK-005, TASK-006. **Mode:** pytest isolation candidate plus repository inspection. **Evidence:** S.

**Preconditions:** Two separately instantiated local app factories and inspectable configuration/source.

**Test data:** explicitly synthetic seeded account A and separately configured synthetic account B.

**Steps**
1. Preconditions: Two separately instantiated local app factories and inspectable configuration/source. Test data: explicitly synthetic seeded account A and separately configured synthetic account B. Action: Inspect seed/configuration for synthetic account records and hashed sample credentials; sign in with a configured synthetic account.
2. Mutate account/session/reset state in app instance 1 and inspect independent instance 2.
3. Inspect code/dependencies/docs for a production identity integration or real account material.

**Expected results**
1. Locally defined synthetic account signs in without reaching a real user database.
2. Instance 2 does not inherit instance 1's mutable sessions, tokens, quota or notifications; its synthetic fixture is independent.
3. Reviewed repository/config does not contain production identity integration or real credentials. Source inspection supports, but cannot prove the absence of every conceivable uninspected external interaction.

### TC-021 — Memory-only private notification sink

**Trace:** REQ-021; TASK-003, TASK-004, TASK-005, TASK-006. **Mode:** pytest state/isolation candidate plus repository inspection. **Evidence:** S.

**Preconditions:** Two independent local app instances, authorized same-process sink fixture and synthetic account.

**Test data:** one eligible request link and one successful-reset notification.

**Steps**
1. Preconditions: Two independent local app instances, authorized same-process sink fixture and synthetic account. Test data: one eligible request link and one successful-reset notification. Action: Request a reset and complete it; inspect each event privately through the first instance's sink fixture.
2. Construct a second fresh app/restart-equivalent fixture; inspect its sink, and inspect the first app's public routes/responses for a sink or bearer-link endpoint.
3. Inspect source/configuration for real mail/SMS or other external notification transport.

**Expected results**
1. The link event and owner success event are locally inspectable **only** in the first instance's in-memory sink.
2. Fresh instance has no inherited events; no public HTTP endpoint or response reveals links/sink entries.
3. No external delivery is required or configured; the check does not claim production persistence or actual email delivery.

### TC-022 — Pytest regression suite covers approved behavior

**Trace:** REQ-022; TASK-005, TASK-006. **Mode:** prospective automated suite run plus test-content inspection. **Evidence:** S, K.

**Preconditions:** Application and tests have been implemented and local Python 3.12 test dependencies installed; not yet true at design time.

**Test data:** isolated fixtures, fixed/advancing UTC clock, distinct synthetic users and independent cookie jars.

**Steps**
1. Preconditions: Application and tests have been implemented and local Python 3.12 test dependencies installed; not yet true at design time. Test data: isolated fixtures, fixed/advancing UTC clock, distinct synthetic users and independent cookie jars. Action: Review test files to map prospective TC-001–TC-021 checks to assertions, including HTML semantics, invalid input/CSRF, private effects and authorization.
2. Check explicit known/unknown/throttled status/headers/body parity, five/six/+3599/+3600 link counts, unused +29:59/+30:00 token boundaries, replay/concurrent completion, old-session invalidation and one owner event per success.
3. After implementation, run documented `python3.12 -m pytest` locally and record its actual exit status and failures.

**Expected results**
1. Tests assert concrete outcomes for REQ-001–REQ-021; HTML/CSS-only assertions are labeled partial for visual/accessibility fidelity.
2. The listed boundary/security behaviors are exercised with public responses and private effects checked separately, without sleeps, real accounts or external messaging.
3. A successful future run exits zero with passing tests; any failure is reported, not waived or presented here as already run. Documentation and no-deployment checks remain inspection-only.

### TC-023 — Production limitations are explicitly documented

**Trace:** REQ-023; TASK-006. **Mode:** documentation inspection **only**, not pytest. **Evidence:** S.

**Preconditions:** Delivered project documentation and local demonstration instructions are available.

**Test data:** README/local setup and production-limitation sections.

**Steps**
1. Preconditions: Delivered project documentation and local demonstration instructions are available. Test data: README/local setup and production-limitation sections. Action: Read documented local Python 3.12 startup, synthetic-account use and authorized private sink inspection procedure.
2. Inspect limitation statements for memory loss on process restart, single-process/worker boundary, non-durable quota/session revocation, absence of real email and missing production reliability/security operations.
3. Check whether documentation misleadingly calls the demo production-ready or instructs public bearer-link display.

**Expected results**
1. A local reader can identify the synthetic account and in-memory sink as demonstration mechanisms, not real identity or delivery.
2. Documentation explicitly says the app is **not production-ready as-is** and describes the listed memory/durability/multi-worker and operational limits.
3. No public sink inspection or unwarranted production/deployment claim is present. This is a proposed review criterion, not a claim the docs already exist.

### TC-024 — No deployment workflow, instructions or action

**Trace:** REQ-024; TASK-006. **Mode:** delivered-tree/diff and work-record inspection **only**, not pytest. **Evidence:** S.

**Preconditions:** Final delivery diff/tree and authorized work/delivery record are available.

**Test data:** workflow manifests, deploy scripts, hosting configuration, project docs and deployment action history.

**Steps**
1. Preconditions: Final delivery diff/tree and authorized work/delivery record are available. Test data: workflow manifests, deploy scripts, hosting configuration, project docs and deployment action history. Action: Inspect the delivered diff/tree for newly added deployment workflow manifests, deploy scripts and hosting/deploy configuration.
2. Read project docs for instructions to deploy the app.
3. Inspect the work/delivery record for any performed deployment action; record any inaccessible records as a verification limitation rather than inferring absence from source.

**Expected results**
1. No newly added deployment workflows, scripts or deployment configuration appear in delivered changes.
2. No deployment instructions were added.
3. The accessible work record shows no deployment was performed; if the record is unavailable, that part remains explicitly **unverified**. Source inspection alone does not establish that no deployment happened.

## Coverage by approved acceptance criterion

| Requirement / criterion | Proposed case | Approved task links | Verification |
| --- | --- | --- | --- |
| REQ-001 | TC-001 | TASK-002, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-002 | TC-002 | TASK-002, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-003 | TC-003 | TASK-002, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-004 | TC-004 | TASK-002, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-005 | TC-005 | TASK-003, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-006 | TC-006 | TASK-002, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-007 | TC-007 | TASK-002, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-008 | TC-008 | TASK-002, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-009 | TC-009 | TASK-003, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-010 | TC-010 | TASK-003, TASK-005 | Pytest candidate |
| REQ-011 | TC-011 | TASK-003, TASK-005 | Pytest candidate |
| REQ-012 | TC-012 | TASK-003, TASK-005 | Pytest candidate |
| REQ-013 | TC-013 | TASK-004, TASK-005 | Pytest candidate |
| REQ-014 | TC-014 | TASK-004, TASK-005 | Pytest candidate; before/at-expiry clauses |
| REQ-015 | TC-015 | TASK-004, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-016 | TC-016 | TASK-004, TASK-005 | Pytest candidate |
| REQ-017 | TC-017 | TASK-004, TASK-005 | Pytest candidate |
| REQ-018 | TC-018 | TASK-001, TASK-005, TASK-006 | Pytest candidate + supplemental inspection |
| REQ-019 | TC-019 | TASK-001, TASK-002, TASK-003, TASK-004, TASK-005 | Pytest candidate + supplemental inspection |
| REQ-020 | TC-020 | TASK-001, TASK-005, TASK-006 | Pytest candidate + supplemental inspection |
| REQ-021 | TC-021 | TASK-003, TASK-004, TASK-005, TASK-006 | Pytest candidate + supplemental inspection |
| REQ-022 | TC-022 | TASK-005, TASK-006 | Pytest candidate + supplemental inspection |
| REQ-023 | TC-023 | TASK-006 | Inspection only (not pytest) |
| REQ-024 | TC-024 | TASK-006 | Inspection only (not pytest) |

**Coverage reconciliation:** REQ-001–REQ-024: 24/24 criteria assigned to TC-001–TC-024; no uncovered requirement or approved exclusion. Both acceptance clauses of REQ-014 use independently unused links before and at expiry. TASK-001–TASK-006 all linked; TASK-005 supplies prospective pytest coverage rather than replacing behavioral implementation tasks. TC-023 and TC-024 remain inspection-only. Browser visual fidelity, typed masking, keyboard focus/operation and absence-of-integration claims cannot be proved from HTML/CSS unit assertions alone. An inaccessible delivery record leaves the no-deployment-action check unverified.

## Assumptions and verification limits

- These are proposed verification scenarios, not executed checks; the reviewed repository does not yet have a runnable application or pytest suite. Routes such as /sign-in, /forgot-password and /account follow approved solution design, not observed existing behavior.
- An isolated Python 3.12 Flask app factory, synthetic accounts, private same-process notification sink, injectable UTC clock and independent cookie jars provide deterministic local pytest fixtures; no real user, external notification or deployment is used.
- The five-accepted-requests-per-account-per-hour rule is interpreted as a rolling 3600-second window for each known synthetic account; no numeric limit for unknown identifiers is inferred. Equivalent syntactically valid requests retain an identical public outcome.
- An unused link is usable strictly before its issuance time plus 1800 seconds and invalid at or after that instant; this boundary convention implements the approved interpretation of the 30-minute lifetime.
- The image establishes static sign-in appearance only. Masking, navigation, focus, browser accessibility and pixel fidelity require implementation and inspection; no runtime behavior is attributed to the image.
- Only a nonempty new password is assumed. No password maximum length, additional composition policy, exact unpictured-page copy, or unknown-account quota is specified.
- TC-023 and TC-024 require documentation, repository and accessible work-record inspection rather than pytest; inaccessible deployment records leave the no-deployment-action part unverified, not implicitly passed.

## Open questions (nonblocking)

- What exact layout and copy should unpictured reset-request, invalid-link, success and signed-in pages use? — The supplied image depicts only sign-in; tests assert structure and behavior without inventing exact recovery copy.
- Is a further password policy, maximum length or particular authenticated-success presentation required? — Current scenarios exercise a distinct nonempty password without adding unsupported limits.
- Should invalid, expired and consumed reset links use identical neutral error wording? — No particular error text is specified; the tests require no credential mutation or sensitive disclosure.
- What authorized same-process sink-inspection procedure and perceivable validation/progress wording should local demonstrators use? — The tests use a private fixture and prohibit public bearer-link or notification endpoints.
- How should unknown account identifiers be accounted for, if at all, under recovery-request controls? — The standard sets five per account per hour; the approved design limits known synthetic accounts and retains unknown-account public parity without imposing a numeric unknown quota.
