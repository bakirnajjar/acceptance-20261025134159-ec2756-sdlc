"""TASK-003 traceable recovery, quota, and private-link tests."""

import hashlib
import logging
import re
from datetime import UTC, datetime, timedelta

from flask.testing import FlaskClient

from local_auth_demo import create_app
from local_auth_demo.state import ResetTokenRecord


class FixedClock:
    def __init__(self) -> None:
        self.instant = datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self.instant

    def advance(self, seconds: int) -> None:
        self.instant += timedelta(seconds=seconds)


class TokenSource:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> str:
        self.count += 1
        return f"synthetic-test-token-{self.count}"


def csrf_from(client: FlaskClient) -> str:
    response = client.get("/forgot-password")
    assert response.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def submit(client: FlaskClient, csrf: str, email: str):
    return client.post("/forgot-password", data={"csrf_token": csrf, "email": email})


def public_response(response):
    return response.status_code, tuple(response.headers.items()), response.data


def test_tc_005_anonymous_local_navigation_and_labeled_form() -> None:
    client = create_app().test_client()
    sign_in = client.get("/sign-in").get_data(as_text=True)
    assert '<a class="recovery-link" href="/forgot-password">Forgot password?</a>' in sign_in
    page = client.get("/forgot-password")
    assert page.status_code == 200
    assert '<form method="post" action="/forgot-password">' in page.get_data(as_text=True)
    assert '<label for="email">Email address</label>' in page.get_data(as_text=True)
    assert 'id="email" name="email" type="email"' in page.get_data(as_text=True)
    assert 'name="csrf_token"' in page.get_data(as_text=True)
    assert "no-store" in page.headers["Cache-Control"]


def test_tc_009_validation_and_csrf_do_not_issue_links() -> None:
    app = create_app(clock=FixedClock(), token_generator=TokenSource())
    for email, csrf_override in (
        ("", None),
        ("not-an-email", None),
        ("person@invalid", None),
        ("demo@example.test", ""),
        ("demo@example.test", "wrong-csrf"),
    ):
        client = app.test_client()
        csrf = csrf_from(client)
        response = submit(client, csrf if csrf_override is None else csrf_override, email)
        assert response.status_code == 400
        assert b'role="alert"' in response.data
        assert b'aria-describedby="forgot-error"' in response.data
        assert b'name="csrf_token"' in response.data
    client = app.test_client()
    csrf_from(client)
    missing = client.post("/forgot-password", data={"email": "demo@example.test"})
    assert missing.status_code == 400
    assert b'role="alert"' in missing.data
    assert app.extensions["local_auth_demo"].sink.links_snapshot() == ()
    assert app.extensions["local_auth_demo"].store.reset_tokens == {}


def test_tc_010_private_digest_link_and_usable_reset_get() -> None:
    clock, tokens = FixedClock(), TokenSource()
    app = create_app(clock=clock, token_generator=tokens)
    client = app.test_client()
    csrf = csrf_from(client)
    response = submit(client, csrf, " DEMO@EXAMPLE.TEST ")
    assert response.status_code == 200
    services = app.extensions["local_auth_demo"]
    (event,) = services.sink.links_snapshot()
    assert event.account_id == event.recipient == "demo@example.test"
    assert event.issued_at == clock.now()
    assert event.url == "/reset/synthetic-test-token-1"
    digest = hashlib.sha256(b"synthetic-test-token-1").hexdigest()
    with services.store.lock:
        assert set(services.store.reset_tokens) == {digest}
        assert services.store.reset_tokens[digest] == ResetTokenRecord(event.account_id, clock.now())
        assert event.url not in repr(services.store.reset_tokens)
        assert "synthetic-test-token-1" not in repr(services.store.reset_tokens)
    for public_part in (response.data.decode(), str(response.headers)):
        assert event.url not in public_part
        assert "synthetic-test-token-1" not in public_part
        assert event.recipient not in public_part
    page = app.test_client().get(event.url)
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert '<label for="new-password">New password</label>' in html
    assert 'name="new_password" type="password"' in html
    assert '<form method="post" action="/reset/synthetic-test-token-1">' in html
    assert 'name="csrf_token"' in html
    assert "no-store" in page.headers["Cache-Control"]
    assert page.headers["Referrer-Policy"] == "no-referrer"
    assert app.test_client().get(event.url).status_code == 200  # GET does not consume.
    assert services.sink.links_snapshot() == (event,)
    rejected = app.test_client().post(event.url, data={"new_password": "NotAccepted!"})
    assert rejected.status_code == 400  # Missing CSRF never consumes the link.
    assert b'role="alert"' in rejected.data
    with services.store.lock:
        assert not services.store.reset_tokens[digest].consumed
    assert services.sink.successes_snapshot() == ()


def test_tc_011_equivalent_public_responses_and_distinct_private_effects() -> None:
    responses = []
    link_counts = []
    for kind in ("known", "unknown", "suppressed"):
        clock, tokens = FixedClock(), TokenSource()
        app = create_app(clock=clock, token_generator=tokens)
        services = app.extensions["local_auth_demo"]
        client = app.test_client()
        # The same pre-existing CSRF/session state for each POST, independent of GETs.
        with client.session_transaction() as cookie:
            cookie["csrf_token"] = "same-client-csrf"
        if kind == "suppressed":
            with services.store.lock:
                services.store.reset_requests["demo@example.test"] = [clock.now()] * 5
        response = submit(
            client,
            "same-client-csrf",
            "unknown@example.test" if kind == "unknown" else "demo@example.test",
        )
        responses.append(public_response(response))
        link_counts.append(len(services.sink.links_snapshot()))
        assert tokens.count == (1 if kind == "known" else 0)
    assert responses[0] == responses[1] == responses[2]
    assert responses[0][0] == 200
    assert b"Request received" in responses[0][2]
    assert b"demo@example.test" not in responses[0][2]
    assert link_counts == [1, 0, 0]


def test_tc_012_rolling_window_boundary_independent_accounts_and_unknowns() -> None:
    clock, tokens = FixedClock(), TokenSource()
    app = create_app(
        clock=clock,
        token_generator=tokens,
        synthetic_accounts={"a@example.test": "SyntheticA!", "b@example.test": "SyntheticB!"},
    )
    client = app.test_client()
    csrf = csrf_from(client)
    sink = app.extensions["local_auth_demo"].sink
    acknowledgements = [submit(client, csrf, "a@example.test") for _ in range(5)]
    assert len(sink.links_snapshot()) == 5
    clock.advance(3599)
    suppressed = submit(client, csrf, "a@example.test")
    assert public_response(suppressed) == public_response(acknowledgements[0])
    assert len(sink.links_snapshot()) == 5
    assert submit(client, csrf, "b@example.test").status_code == 200
    assert len(sink.links_snapshot()) == 6
    clock.advance(1)
    assert submit(client, csrf, "a@example.test").status_code == 200
    assert len(sink.links_snapshot()) == 7
    store = app.extensions["local_auth_demo"].store
    with store.lock:
        assert store.reset_requests["a@example.test"] == [clock.now()]
        assert store.reset_requests["b@example.test"] == [clock.now() - timedelta(seconds=1)]
    for _ in range(7):
        assert public_response(submit(client, csrf, "unknown@example.test")) == public_response(
            acknowledgements[0]
        )
    assert len(sink.links_snapshot()) == 7
    assert tokens.count == 7


def test_tc_019_tc_021_reset_pages_are_private_server_rendered_and_expire() -> None:
    clock = FixedClock()
    app = create_app(clock=clock, token_generator=TokenSource())
    services = app.extensions["local_auth_demo"]
    client = app.test_client()
    assert submit(client, csrf_from(client), "demo@example.test").status_code == 200
    (event,) = services.sink.links_snapshot()
    clock.advance(1799)
    valid_page = client.get(event.url)
    assert valid_page.status_code == 200
    assert "<script" not in valid_page.get_data(as_text=True)
    clock.advance(1)
    expired = client.get(event.url)
    invalid = client.get("/reset/no-such-token")
    with services.store.lock:
        services.store.reset_tokens[hashlib.sha256(b"synthetic-test-token-1").hexdigest()].consumed = True
    used = client.get(event.url)
    assert public_response(expired) == public_response(invalid) == public_response(used)
    assert b"Reset link unavailable" in expired.data
    assert b"/forgot-password" in expired.data
    assert event.url.encode() not in expired.data
    assert expired.headers["Referrer-Policy"] == "no-referrer"
    assert services.sink.links_snapshot() == (event,)
    for path in ("/notifications", "/sink", "/reset-links"):
        assert client.get(path).status_code == 404


def test_tc_021_local_access_log_redacts_bearer_path(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="werkzeug"):
        logging.getLogger("werkzeug").info(
            '"GET /reset/synthetic-test-token-1 HTTP/1.1" 200 -'
        )
    assert "synthetic-test-token-1" not in caplog.text
    assert "/reset/[redacted]" in caplog.text
