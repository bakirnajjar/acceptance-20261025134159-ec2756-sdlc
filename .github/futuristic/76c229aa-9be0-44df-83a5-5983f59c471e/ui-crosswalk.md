# UI evidence-to-requirement crosswalk (T001)

**Applicable.** One static sign-in wireframe is supplied; it does not establish functioning interactions, a reset page, or an authenticated screen. This inventory supports, but is not, the final UI contract. Requirements are linked by their approved `requirements_analysis` identifiers; that stage was read by key and supplied no locator, so no `stage_output` citation is invented.

**Evidence key (source type / source ID / locator):**
- **A:** `attachment / 941402b9-bfd8-414c-a6e4-2fc2dce190a1 / sign-in-wireframe.png`.
- **S:** `user_story / user_story / characters 0-16000`.
- **K:** `knowledge / bcf198d8-a628-401c-8641-b726fcbd00b5 / v1, chunk 0` (ACC-STD-01–03). Other identical search results are not independent policies.

## Pictured screen: sign-in

| Approved IDs | Evidence-to-UI mapping |
| --- | --- |
| REQ-001 | **Observed [A]:** White page, centered thin dark-outlined rectangular card and prominent bold “Sign in” heading. |
| REQ-002 | **Observed [A]:** “Email address” label above an input showing `name@example.com` placeholder. |
| REQ-003 | **Observed [A]:** “Password” label above an input displaying masked-looking `********` placeholder. **Proposed (inferred, not observed) [A, S]:** Typed password characters are actually masked; a static image cannot verify input semantics. |
| REQ-004 | **Observed [A]:** Blue underlined “Forgot password?” link below password input; **K** also requires the link. |
| REQ-006 | **Observed [A]:** Wide dark “Sign in” button. |
| REQ-007 | **Observed [A]:** Footer “No account? Contact your administrator.” |

**Proposed (inferred, not observed) [A, S, K], REQ-002–REQ-006, REQ-008:** The fields, link and button will be operable, with explicit associated labels and accessible names, keyboard traversal in reading order, visible focus and sufficient text/control contrast. On empty or invalid credentials, give a clear, non-secret-disclosing error near the fields and announce it to assistive technology; preserve the email on error but not a password. A submission/loading state should prevent duplicate activation and announce progress if perceptible. No actual click behavior, keyboard accessibility, contrast compliance, authentication or active session is demonstrated by the picture.

## Intended UI behavior and unpictured screens

Every entry below is **Proposed (inferred, not observed)**, not evidence of an existing screen. Exact visual design and copy beyond the pictured sign-in page remain unspecified.

| Screen / purpose and approved IDs | Components, actions and proposed accessibility and states |
| --- | --- |
| Sign-in interaction and authenticated result — REQ-003, REQ-005, REQ-008 | [A, S, K] The link opens reset request; valid synthetic credentials establish an active session and a minimal authenticated result. That result should identify the authenticated state without revealing secrets, provide keyboard-operable navigation/sign-out if offered, a clear heading and focus destination, and readable contrast. For invalid/empty input show accessible feedback; during submission show progress/avoid duplicate action; an authenticated state is **not** pictured. |
| Reset-request form — REQ-005, REQ-009 | [S, K] A server-rendered form accepts an account email as the identifier (approved assumption A2), with associated label, accessible submit/back-to-sign-in actions, logical focus order, visible focus and contrast. Empty/malformed email yields an announced field error; submission has non-revealing progress/duplicate-submit handling; no account-existence hint or public link is shown. |
| Generic request acknowledgement — REQ-010, REQ-011, REQ-012 | [S, K] Same public message and response outcome for known/unknown accounts, including when a known account is at its five-per-account-per-hour limit; never expose account existence or a reset link. Give an accessible confirmation heading/status and keyboard-operable route to sign-in; no sensitive details on an empty/no-link outcome, no account-specific error or loading difference. For eligible known synthetic accounts, a usable link is recorded only in the in-memory sink for local demonstration/tests (approved assumption A3), not displayed publicly. Limit handling is a nonvisual rule, not proof from the wireframe. |
| New-password form for a valid link — REQ-010, REQ-013, REQ-014, REQ-015 | [S, K] A locally accessed, unused, unexpired link opens a server-rendered form to enter a new masked password. Provide labeled control(s), accessible names, keyboard/focus order, visible focus and contrast; announce empty/invalid input without echoing secrets, prevent duplicate submission with progress feedback. A link remains usable before 30 minutes since issue; invalid at or after that boundary under approved assumption A5. Password rules and exact fields are not specified. |
| Invalid, used or expired link state — REQ-013, REQ-014 | [K] Reject without changing the password; present a generic accessible error with a keyboard-operable path to request a fresh link, a heading/focus target and sufficient contrast. This is an error/empty-link state rather than an exposed account or token detail; if processing is perceptible, announce progress without revealing link validity in advance. |
| Reset success and return to sign-in — REQ-015, REQ-016, REQ-017 | [S, K] Confirm success without displaying the new password, offer an accessible sign-in route, set heading/status focus and readable contrast. Handle no-longer-valid/duplicate submissions as the generic error state, and announce progress before completion. Successful reset changes the password, invalidates **every** active session and records an owner notification in the in-memory sink after **each** successful reset; these effects are not evidenced by a success screen and notifications are not claimed as real email or a public UI. |

### Stepwise proposed flows (not observed)

1. **Sign-in [REQ-001–REQ-008; A, S, K]:** Open pictured sign-in layout → enter synthetic email and password (actual masking must be implemented) → submit → show accessible validation or a minimal authenticated state with an active session. Only the static layout is **Observed [A]**.
2. **Recovery request [REQ-004, REQ-005, REQ-009–REQ-012; A, S, K]:** Follow “Forgot password?” → enter account email → submit → show identical public acknowledgement for known and unknown identifiers with no public link. For an eligible known account, issue a usable link into the local in-memory sink; after five requests in a rolling hour, do not issue another link (approved assumption A4), while keeping the public response indistinguishable.
3. **Recovery completion [REQ-010, REQ-013–REQ-017; S, K]:** For local demonstration retrieve the known account's link from the sink, not the public response → open the new-password form before expiry → enter and submit a new password → reject used/expired/invalid links without mutation; on successful reset consume the link once, update password, invalidate every active session, record an owner notification in memory, then offer sign-in with the new password. Expiry is measured from issue time (invalid at/after 30 minutes under A5).

## Requirements without direct wireframe coverage

**Proposed (inferred, not observed) [A, S, K]:** REQ-005's destination, REQ-003's actual masking, and all of REQ-008–REQ-017 require interaction or unpictured screens; no reset-request, acknowledgement, new-password, invalid-link, success, authenticated-result or notification view is supplied. REQ-018 (Python 3.12/Flask), REQ-019 (server-rendered pages), REQ-020 (synthetic accounts), REQ-021 (in-memory notification sink), REQ-022 (pytest coverage), REQ-023 (production limitations documented) and REQ-024 (no deployment) are nonvisual implementation/delivery constraints **[S]**; UI appearance cannot establish any of them. The reset policy for REQ-011–REQ-017 also requires behavioral verification **[K]**, not visual inference. No live app or interaction/test result is evidence here.

**Open questions:** What exact copy/layout should the unpictured reset and authenticated screens use? What password policy and sign-in success UX are intended? Should invalid/used/expired links share one message or vary without disclosing secrets? How is the local sink inspected by authorized demonstrators without placing reset links in public pages? What validation and progress presentation is appropriate for server-rendered forms? These questions do not change the observed image or imply real email delivery.
