# acceptance-20261025134159-ec2756-sdlc
Synthetic Futuristic acceptance test repository for SDLC stage outputs. No real data. Safe to delete.

## Local-only Python 3.12 demo

This Flask/Jinja app serves server-rendered sign-in, recovery-request and
reset-link forms using isolated, process-local state. It uses only synthetic
accounts and a private in-memory notification sink: it does not contact a real
identity provider or deliver email or SMS.

Install [uv](https://docs.astral.sh/uv/) and make Python 3.12 available. From
the repository root, install the locked dependencies (including test and lint
tools) into `.venv`:

```sh
uv sync --python 3.12
```

Build (compile-check source and tests) from the repository root:

```sh
uv run --python 3.12 python3.12 -m compileall -q src tests
```

Test from the repository root:

```sh
uv run --python 3.12 python3.12 -m pytest
```

Alternatively, run pytest **directly** inside the activated environment:

```sh
source .venv/bin/activate
python3.12 -m pytest
deactivate
```

Outside the activated environment, use `uv run` so the project's dev
dependencies are available.

Lint from the repository root:

```sh
uv run --python 3.12 ruff check .
```

Start the local development server from the repository root (Flask defaults to
loopback; stop it with Ctrl-C):

```sh
uv run --python 3.12 flask --app local_auth_demo:create_app run
```

### Try the synthetic flow

Open `http://127.0.0.1:5000/sign-in` or
`http://127.0.0.1:5000/forgot-password`. The sole default account is the
**synthetic** `demo@example.test` with sample password `SamplePass!123`.
These published example values are not live secrets; never enter real
credentials or use real account data in this demo. The password is stored as a
Werkzeug hash, not as a plaintext account record. Sign-in uses a CSRF-protected
form and redirects to `/account`; sign-out is a CSRF-protected POST.

Submit that synthetic email on `/forgot-password` to receive a generic public
acknowledgement. Known, unknown and quota-suppressed valid requests receive the
same public response. Up to five requests per known account in a rolling hour
record reset links in the **private** per-app sink; nothing is mailed or shown
on the acknowledgement page. A link is single-use and valid strictly before
30 minutes from issuance. GET the link, submit a nonempty new synthetic
password with the form's CSRF token, and the reset changes the hash, invalidates
all that account's active sessions and records one private owner success event.
The old password no longer signs in. Do not paste bearer links into logs,
public responses or screenshots.

For an end-to-end reset without email delivery, run this *in one Python
process*, separate from the Flask CLI server above. This uses Flask's test
client to inspect the same app instance's private sink; a separate terminal
or app process cannot inspect the running server's memory:

```sh
uv run --python 3.12 python3.12
```

At its Python prompt:

```python
from local_auth_demo import create_app

app = create_app()
client = app.test_client()
client.get("/forgot-password")
with client.session_transaction() as cookie:
    csrf = cookie["csrf_token"]
ack = client.post("/forgot-password", data={
    "csrf_token": csrf, "email": "demo@example.test",
})
assert ack.status_code == 200
sink = app.extensions["local_auth_demo"].sink  # private same-process API only
(link_event,) = sink.links_snapshot()
assert sink.successes_snapshot() == ()
page = client.get(link_event.url)  # keep the bearer URL private
assert page.status_code == 200
with client.session_transaction() as cookie:
    csrf = cookie["csrf_token"]
result = client.post(link_event.url, data={
    "csrf_token": csrf, "new_password": "NewSynthetic!123",
})
assert result.status_code == 200
assert len(sink.successes_snapshot()) == 1
```

The sink exposes immutable snapshots via `links_snapshot()` and
`successes_snapshot()` only to authorized code with a reference to this
process's app. Do not expose the sink through an HTTP endpoint or print its
bearer links. Tests can pass `synthetic_accounts` to `create_app` for isolated
fixtures; each factory invocation has fresh accounts, sessions, quota and
token indexes, and events. Tests may also inject a `Clock.now()` returning
aware UTC time and a URL-safe token generator; the defaults use the system UTC
clock and cryptographic randomness. Session IDs are independently random, and
the session and reset-token indexes store SHA-256 digests.

### Production limitations (TC-023 / TC-024)

This demonstration is **not production-ready as-is**. Everything in the
account, session, reset-token, quota and notification stores exists only in
one app instance's memory. Restarting the process loses that state (including
issued links, notification events, quota history and session/revocation state).
It must run as a single worker for coherent local behavior: concurrent
processes/workers do not share quota enforcement, sessions, token consumption
or revocation. The sink is not durable notification delivery; there is no
external mail service, real identity system or persistent account store.

Production would require separately designed durable atomic state and
multi-worker coordination, reliable notification delivery, secret/key rotation
and credential lifecycle, HTTPS and security/privacy/timing review, abuse
controls, monitoring, recovery and operational guarantees. Local CSRF, hashing
and cookie settings are not a claim of production-grade security.
`LOCAL_AUTH_DEMO_SECRET_KEY` is an optional **local-only** Flask signing-key
environment variable; when unset a new random key is generated per app
instance and lost on restart. Do not put real keys in this repository or logs.
No hosting, deployment, deployment workflow or deployment instructions are
provided or authorized here.
