# acceptance-20261025134159-ec2756-sdlc
Synthetic Futuristic acceptance test repository for SDLC stage outputs. No real data. Safe to delete.

## Local Python scaffold

This is a local-only Python 3.12 Flask/Jinja demonstration. It serves
server-rendered sign-in, recovery-request and reset-link forms backed by
isolated process-local state. Sign-in uses synthetic hashed credentials,
CSRF-protected POSTs and revocable registry-backed sessions. Recovery accepts
CSRF-protected email requests and records eligible links in a private in-memory
sink, not an email service. Reset completion (`POST /reset/<token>`) is not yet
implemented. No real accounts, identity service or email are used.

Install [uv](https://docs.astral.sh/uv/) and make Python 3.12 available, then
run from the repository root:

```sh
uv sync --python 3.12
```

Build (compile-check the source and tests):

```sh
uv run --python 3.12 python3.12 -m compileall -q src tests
```

Test:

```sh
uv run --python 3.12 python3.12 -m pytest
```

The approved `python3.12 -m pytest` form also works after activating the
virtual environment with `source .venv/bin/activate`. Without activation,
use `uv run` as above so the dev dependencies are available.

Lint:

```sh
uv run --python 3.12 ruff check .
```

Start locally from the repository root (Flask defaults to loopback):

```sh
uv run --python 3.12 flask --app local_auth_demo:create_app run
```

Open `http://127.0.0.1:5000/sign-in` or `/forgot-password`. The factory seeds
only the **synthetic** `demo@example.test` account with sample password
`SamplePass!123`, stored as a Werkzeug password hash, not a plaintext account
record. These public sample credentials are not production secrets. The sign-in
form obtains a per-client CSRF value on GET; successful sign-in redirects to
`/account`, where the server checks the session registry and account epoch on
every request. The sign-out form POST invalidates the registry entry and clears
the cookie. Tests may pass their own `synthetic_accounts` mapping to `create_app`;
each invocation creates a new locked store with independent accounts, sessions,
quotas, reset-token indexes and private link events. A `Clock.now()` returning
an aware UTC datetime and a secure URL-safe token generator may be injected
for deterministic tests; defaults use the UTC system clock and
`secrets.token_urlsafe(32)`. Session IDs use independent cryptographically
random values; only SHA-256 digests are stored in the session and reset-token
indexes. Eligible known accounts receive at most five accepted requests in
the past rolling 3600 seconds. Known, unknown and suppressed valid submissions
share a generic public acknowledgement. The private per-app sink is accessible
only to same-process code/tests via
`app.extensions["local_auth_demo"].sink.links_snapshot()`; never expose its
bearer links over HTTP or logs. An unused link opens the reset form before
1800 seconds from issuance, but no password changes until reset completion is
implemented. Future reset commits must share the lock with sign-in transitions.

`LOCAL_AUTH_DEMO_SECRET_KEY` is optional for a **local-only** fixed Flask
signing key; without it, a fresh cryptographic key is generated per app
instance and lost on restart. No key is checked in. State is not durable,
coordinated between workers or suitable for production; no external
integrations are provided.
