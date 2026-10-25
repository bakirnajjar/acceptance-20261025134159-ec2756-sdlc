# Requirements analysis

Schema version: `1.0`. Stage: `requirements_analysis`.

## Source references

Each key below denotes the **exact** source-reference object shown. `K1–K5` in a requirement means all five individual knowledge references, not a synthesized reference.

| Key | Source reference |
| --- | --- |
| S | `{"source_type":"user_story","source_id":"user_story","locator":"characters 0-16000"}` |
| A | `{"source_type":"attachment","source_id":"941402b9-bfd8-414c-a6e4-2fc2dce190a1","locator":"sign-in-wireframe.png"}` |
| K1 | `{"source_type":"knowledge","source_id":"bcf198d8-a628-401c-8641-b726fcbd00b5","locator":"v1, chunk 0"}` |
| K2 | `{"source_type":"knowledge","source_id":"cce5b6f4-4162-4c51-b630-53f545d0ba49","locator":"v1, chunk 0"}` |
| K3 | `{"source_type":"knowledge","source_id":"1937b905-d187-4938-bf60-77b0df7f74b1","locator":"v1, chunk 0"}` |
| K4 | `{"source_type":"knowledge","source_id":"2609b851-90c5-4738-aae5-16c1eaa6d477","locator":"v1, chunk 0"}` |
| K5 | `{"source_type":"knowledge","source_id":"99467581-e0f3-4ba3-a177-7343cb1097b5","locator":"v1, chunk 0"}` |

## Requirements

| ID | Statement | Acceptance criterion | Sources |
| --- | --- | --- | --- |
| REQ-001 | The sign-in page displays a rectangular outlined card on a white page, headed “Sign in”. | Given a visitor opens the sign-in page, when the page renders, then an outlined rectangular sign-in card with the heading “Sign in” is visible against a white page. | S, A |
| REQ-002 | The sign-in page displays an email input labeled “Email address” with the placeholder `name@example.com`. | Given the sign-in page is open, when its form renders, then the email input has that label and placeholder. | A |
| REQ-003 | The sign-in page displays a password input labeled “Password” with masked entry and the wireframe’s `********` placeholder. | Given the sign-in page is open, when the password field renders and a visitor types into it, then the label and placeholder are displayed and entered characters are masked. | A |
| REQ-004 | The sign-in page displays a blue, underlined “Forgot password?” link. | Given the sign-in page is open, when the card renders, then the blue underlined link with that exact text is visible. | A, K1–K5 |
| REQ-005 | The “Forgot password?” link opens the reset-request flow. | Given the sign-in page is open, when the visitor follows the “Forgot password?” link, then a page or form for requesting a reset opens. | A, K1–K5 |
| REQ-006 | The sign-in card displays a dark “Sign in” button. | Given the sign-in page is open, when the form renders, then a dark button with the text “Sign in” is visible. | A |
| REQ-007 | The sign-in page displays the footer “No account? Contact your administrator.” | Given the sign-in page is open, when its footer renders, then this exact text is visible beneath the sign-in form/card. | A |
| REQ-008 | A valid synthetic account can sign in and acquire an active session. | Given a configured synthetic account and its current credentials, when its owner submits the sign-in form, then that account has an authenticated active session that can later be invalidated by a reset. | S |
| REQ-009 | The reset-request page accepts an account identifier to request a password reset. | Given a visitor has opened the reset-request flow, when the page renders, then the visitor can submit an account email for a reset request. | S, K1–K5 |
| REQ-010 | A reset request for a known synthetic account issues a usable reset link. | Given a known synthetic account is below the request limit, when its email is submitted for a reset, then a link enabling that account's password-reset flow is issued through the application's in-memory mechanism. | S, K1–K5 |
| REQ-011 | Reset-request responses do not reveal whether the requested account exists. | Given otherwise equivalent requests for a known account and an unknown identifier, when they are submitted, then the public response is identical, including the displayed message and response outcome; it does not expose existence or a reset link. | K1–K5 |
| REQ-012 | A known account cannot receive more than five reset requests per hour. | Given five reset requests were accepted for one synthetic account during the relevant hour, when a sixth request for that account arrives within that hour, then no additional reset link is issued for it; a request outside that window can be accepted. | K1–K5 |
| REQ-013 | A reset link cannot successfully reset a password more than once. | Given a valid link has completed a reset, when someone attempts a second reset with the same link, then the second reset is rejected without changing the password. | K1–K5 |
| REQ-014 | Reset links expire 30 minutes after issuance. | Given a reset link was issued, when it is submitted at or after 30 minutes from issuance, then the reset is rejected without changing the password. | K1–K5 |
| REQ-015 | Submitting a valid reset link with a new password updates that synthetic account's password. | Given an unexpired, unused reset link for a synthetic account, when the owner completes the reset with a new password, then the account accepts the new password for subsequent sign-in. | S, K1–K5 |
| REQ-016 | Completing a successful password reset signs the account out of every active session. | Given the account has one or more active sessions, when its password reset completes, then each previously active session is no longer authenticated. | K1–K5 |
| REQ-017 | Every successful reset notifies its account owner. | Given a successful password reset, when the reset completes, then an owner-addressed notification of that reset is recorded; unsuccessful attempts do not count as successful resets. | S, K1–K5 |
| REQ-018 | The application runs with Python 3.12 and Flask. | Given the documented local application setup uses Python 3.12, when the app is started, then Flask serves the password-reset application. | S |
| REQ-019 | The application's sign-in and reset pages are server-rendered. | Given a request for a sign-in or reset page, when Flask handles it, then the response contains the page's rendered form/content from the server rather than depending on a client-rendered application. | S |
| REQ-020 | The application uses synthetic accounts rather than real account records. | Given the app is started for local demonstration or tests, when an account is used, then it comes from synthetic account data, with no production identity integration. | S |
| REQ-021 | Notifications use an in-memory sink rather than external delivery. | Given a reset-related notification is generated, when it is delivered, then it is inspectable in the in-memory sink and no real delivery service is required. | S |
| REQ-022 | Automated pytest tests cover the implemented reset and sign-in requirements. | Given the project is installed for local testing, when pytest is run, then automated tests exercise the sign-in/reset flows, request parity and limit, link single-use and expiry, session invalidation, and owner notification. | S, K1–K5 |
| REQ-023 | The project documents production limitations. | Given a reader opens the project documentation, when they review the password-reset app's limitations, then they can identify that synthetic accounts and in-memory notifications are demonstration mechanisms and that the app is not production-ready as-is. | S |
| REQ-024 | The delivered project contains no deployment or deployment workflow. | Given the delivered repository, when it is inspected, then there are no newly added deployment workflows or instructions to deploy, and the work does not deploy the app. | S |

## Assumptions

- acceptance-20261025134159-ec2756-skill-sentinel — the acceptance skill produced this output.
- A1. For a demonstrable reset/session-invalidation flow, locally defined synthetic credentials can sign in; no additional password policy, production identity provider, persistent account store, or specific post-sign-in UX is specified. Source: S.
- A2. The reset-request form accepts an email as the account identifier, consistent with the shown “Email address” field; the reset pages have simple server-rendered presentation, but their exact appearance and error copy are unspecified. Sources: S, A.
- A3. Reset links for known synthetic accounts and successful-reset notifications are observable through the in-memory sink for local demonstration and tests; no real email is sent. Public reset-request responses do not contain links. Sources: S, K1–K5.
- A4. Interpret “per account per hour” as a rolling hour for known synthetic accounts. Unknown-account public responses remain indistinguishable, but no unsupported numeric quota for nonexistent accounts is inferred. Sources: K1–K5.
- A5. Interpret “expire 30 minutes after issue” as invalid at or after the 30-minute boundary. Sources: K1–K5.
- Evidence markers. The fully read story had next_offset: null and no story end marker; do not invent one. The attachment read yielded only its source reference and the supplied visual observation has no acceptance attachment marker; do not invent one. Sources: S, A.

## Open questions (non-blocking)

| Question | Blocking | Assumption used |
| --- | --- | --- |
| What exact sign-in result and password policy should be used? | No | A1: a minimal locally demonstrable sign-in/session flow; no additional policy assumed. |
| How should unknown account identifiers be treated under the five-per-account-per-hour limit? | No | A4: enforce per known synthetic account; keep public response indistinguishable and do not invent an unknown-account quota. |
| What precise presentation and error text should the reset-request and new-password pages use? | No | A2: simple server-rendered pages; wireframe appearance is specified only for sign-in. |
| How should links be delivered without production notification infrastructure? | No | A3: expose them in the in-memory sink for local testing, not in public request responses. |
