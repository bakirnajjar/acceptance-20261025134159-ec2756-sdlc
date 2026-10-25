# acceptance-20261025134159-ec2756-sdlc
Synthetic Futuristic acceptance test repository for SDLC stage outputs. No real data. Safe to delete.

## Local Python scaffold

This is a local-only Python 3.12 Flask/Jinja demonstration foundation. It
serves server-rendered sign-in and forgot-password forms, backed by isolated
process-local state. Only GET pages are implemented so far: submitting either
form currently returns HTTP 405. Authentication, sessions and recovery are
not implemented yet. No real accounts, identity service or email are used.

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
record. These public sample credentials are not production secrets and do not
yet allow sign-in. Tests may pass their own `synthetic_accounts` mapping to
`create_app`; each invocation creates a new locked store with independent
accounts, sessions, quotas and reset-token indexes (currently empty). A
`Clock.now()` returning an aware UTC datetime and a URL-safe token generator
may be injected for deterministic future recovery tests; defaults use the UTC
system clock and `secrets.token_urlsafe(32)`. Future session/reset operations
must use the store lock for shared state transitions. No tokens, notifications,
or reset links are issued by the GET-only foundation.

`LOCAL_AUTH_DEMO_SECRET_KEY` is optional for a **local-only** fixed Flask
signing key; without it, a fresh cryptographic key is generated per app
instance and lost on restart. No key is checked in. State is not durable,
coordinated between workers or suitable for production; no deployment or
external integrations are provided.
