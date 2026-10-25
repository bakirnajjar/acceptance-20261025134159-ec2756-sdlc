"""Local startup and complete synthetic flow checks.

HTTP/HTML checks cannot establish browser focus, keyboard operation, typed
masking or pixel fidelity; those portions of TC-001–TC-007/019 need manual
browser inspection.
"""

import ast
import hashlib
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from flask import Flask
from flask.testing import FlaskClient
from werkzeug.security import check_password_hash, generate_password_hash

from local_auth_demo import create_app
from local_auth_demo.state import Account, ResetTokenRecord, SessionRecord


class AdvancingClock:
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
        return f"foundation-token-{self.count}"


def csrf_on(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def post_form(client: FlaskClient, path: str, **fields):
    csrf = csrf_on(client.get(path))
    return client.post(path, data={"csrf_token": csrf, **fields})


def test_tc_018_python312_factory_serves_local_pages() -> None:
    """README's local commands and actual Flask HTML are both checked."""
    assert sys.version_info[:2] == (3, 12)
    readme = Path(__file__).resolve().parents[1].joinpath("README.md").read_text()
    assert "uv sync --python 3.12" in readme
    assert "uv run --python 3.12 flask --app local_auth_demo:create_app run" in readme
    assert "uv run --python 3.12 python3.12 -m pytest" in readme
    app = create_app()
    assert isinstance(app, Flask)
    for path, form in (
        ("/sign-in", '<form method="post" action="/sign-in">'),
        ("/forgot-password", '<form method="post" action="/forgot-password">'),
    ):
        response = app.test_client().get(path)
        assert response.status_code == 200
        assert response.mimetype == "text/html"
        assert form in response.get_data(as_text=True)
    assert app.test_client().get("/static/styles.css").status_code == 200


def test_tc_019_foundation_forms_are_server_rendered() -> None:
    client = create_app().test_client()
    sign_in = client.get("/sign-in").get_data(as_text=True)
    forgot = client.get("/forgot-password").get_data(as_text=True)
    assert '<form method="post" action="/sign-in">' in sign_in
    assert '<label for="email">Email address</label>' in sign_in
    assert '<label for="password">Password</label>' in sign_in
    assert '<form method="post" action="/forgot-password">' in forgot
    assert '<label for="email">Email address</label>' in forgot
    assert '<link rel="stylesheet" href="/static/styles.css">' in forgot
    assert "<script" not in sign_in + forgot
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', sign_in)
    assert csrf is not None
    signed_in = client.post(
        "/sign-in",
        data={
            "csrf_token": csrf.group(1),
            "email": "demo@example.test",
            "password": "SamplePass!123",
        },
    )
    assert signed_in.status_code == 302
    assert signed_in.headers["Location"].endswith("/account")
    assert "<h1>Account</h1>" in client.get("/account").get_data(as_text=True)
    # Sign-in rotates the CSRF secret; use the current rendered request form.
    current_forgot = client.get("/forgot-password").get_data(as_text=True)
    forgot_csrf = re.search(r'name="csrf_token" value="([^"]+)"', current_forgot)
    assert forgot_csrf is not None
    recovery = client.post(
        "/forgot-password",
        data={"csrf_token": forgot_csrf.group(1), "email": "demo@example.test"},
    )
    assert recovery.status_code == 200
    assert b"Request received" in recovery.data
    assert b"demo@example.test" not in recovery.data


def test_tc_020_synthetic_hashed_accounts_and_isolated_state() -> None:
    first = create_app()
    second = create_app()
    one = first.extensions["local_auth_demo"].store
    two = second.extensions["local_auth_demo"].store
    assert one is not two
    assert one.lock is not two.lock
    with one.lock, two.lock:
        first_account = one.accounts["demo@example.test"]
        second_account = two.accounts["demo@example.test"]
        assert first_account is not second_account
        assert first_account.password_hash != "SamplePass!123"
        assert check_password_hash(first_account.password_hash, "SamplePass!123")
        assert check_password_hash(second_account.password_hash, "SamplePass!123")
        one.accounts["other@example.test"] = Account(
            id="other@example.test",
            email="other@example.test",
            password_hash=generate_password_hash("OnlySynthetic!"),
        )
        first_account.session_epoch += 1
        issued_at = datetime(2026, 1, 1, tzinfo=UTC)
        one.reset_requests[first_account.id] = [issued_at]
        session_digest = hashlib.sha256(b"synthetic-session").hexdigest()
        token_digest = hashlib.sha256(b"synthetic-token").hexdigest()
        one.sessions[session_digest] = SessionRecord(first_account.id, first_account.session_epoch)
        one.reset_tokens[token_digest] = ResetTokenRecord(first_account.id, issued_at)
        assert "other@example.test" not in two.accounts
        assert second_account.session_epoch == 0
        assert not two.sessions and not two.reset_requests and not two.reset_tokens

    custom = create_app(synthetic_accounts={" TEST@EXAMPLE.TEST ": "OnlySynthetic!"})
    custom_store = custom.extensions["local_auth_demo"].store
    with custom_store.lock:
        assert set(custom_store.accounts) == {"test@example.test"}
        assert check_password_hash(
            custom_store.accounts["test@example.test"].password_hash, "OnlySynthetic!"
        )
    assert "test@example.test" not in two.accounts


def test_tc_020_clock_and_token_source_are_per_app_injectable() -> None:
    class FixedClock:
        def now(self) -> datetime:
            return datetime(2026, 1, 1, tzinfo=UTC)

    clock = FixedClock()
    generator = lambda: "synthetic-test-token"
    services = create_app(clock=clock, token_generator=generator).extensions["local_auth_demo"]
    assert services.clock is clock
    assert services.clock.now().tzinfo is UTC
    assert services.token_generator is generator
    assert create_app().extensions["local_auth_demo"].token_generator() != generator()


def test_tc_019_no_javascript_full_sign_in_recovery_and_reset_flow() -> None:
    """Server HTML and form POSTs cover the flow; browser JS-disabled use is manual."""
    app = create_app(
        token_generator=TokenSource(),
        synthetic_accounts={"owner@example.test": "Old!demo"},
    )
    client = app.test_client()
    sign_in = client.get("/sign-in")
    assert '<form method="post" action="/sign-in">' in sign_in.get_data(as_text=True)
    invalid_login = post_form(
        client, "/sign-in", email="owner@example.test", password="Wrong!demo"
    )
    assert invalid_login.status_code == 401
    assert b'role="alert"' in invalid_login.data
    assert "<script" not in invalid_login.get_data(as_text=True)
    assert client.get("/account").status_code == 302
    recovery_path = re.search(
        r'href="(/forgot-password)"', sign_in.get_data(as_text=True)
    )
    assert recovery_path is not None
    forgot = client.get(recovery_path.group(1))
    assert '<form method="post" action="/forgot-password">' in forgot.get_data(as_text=True)
    assert '<label for="email">Email address</label>' in forgot.get_data(as_text=True)
    invalid_request = client.post(
        "/forgot-password", data={"csrf_token": csrf_on(forgot), "email": "not-an-email"}
    )
    assert invalid_request.status_code == 400
    assert b'role="alert"' in invalid_request.data
    assert app.extensions["local_auth_demo"].sink.links_snapshot() == ()
    acknowledgement = client.post(
        "/forgot-password",
        data={"csrf_token": csrf_on(forgot), "email": "owner@example.test"},
    )
    assert acknowledgement.status_code == 200
    assert b"<h1>Request received</h1>" in acknowledgement.data
    (link_event,) = app.extensions["local_auth_demo"].sink.links_snapshot()
    reset = client.get(link_event.url)
    assert reset.status_code == 200
    reset_html = reset.get_data(as_text=True)
    assert '<form method="post" action="' + link_event.url + '">' in reset_html
    assert '<label for="new-password">New password</label>' in reset_html
    assert 'name="new_password" type="password"' in reset_html
    invalid_reset = client.post(
        link_event.url, data={"csrf_token": csrf_on(reset), "new_password": ""}
    )
    assert invalid_reset.status_code == 400
    assert b'role="alert"' in invalid_reset.data
    assert app.extensions["local_auth_demo"].sink.successes_snapshot() == ()
    confirmation = client.post(
        link_event.url,
        data={"csrf_token": csrf_on(reset), "new_password": "New!demo"},
    )
    assert confirmation.status_code == 200
    assert b"<h1>Password reset</h1>" in confirmation.data
    assert link_event.url.encode() not in confirmation.data
    for response in (sign_in, forgot, acknowledgement, reset, invalid_reset, confirmation):
        assert "<script" not in response.get_data(as_text=True)
    assert post_form(
        client, "/sign-in", email="owner@example.test", password="Old!demo"
    ).status_code == 401
    authenticated = post_form(
        client, "/sign-in", email="owner@example.test", password="New!demo"
    )
    assert authenticated.status_code == 302
    assert authenticated.headers["Location"].endswith("/account")
    assert b"<h1>Account</h1>" in client.get("/account").data


def test_tc_020_independent_synthetic_identity_and_mutable_state_flow() -> None:
    """A configured test account works only in its own process-local app."""
    first = create_app(
        token_generator=TokenSource(),
        synthetic_accounts={"one@example.test": "One!demo"},
    )
    second = create_app(synthetic_accounts={"two@example.test": "Two!demo"})
    first_client, second_client = first.test_client(), second.test_client()
    assert post_form(
        first_client, "/sign-in", email="one@example.test", password="One!demo"
    ).status_code == 302
    assert first_client.get("/account").status_code == 200
    assert post_form(
        second_client, "/sign-in", email="one@example.test", password="One!demo"
    ).status_code == 401
    assert second_client.get("/account").status_code == 302
    assert post_form(
        second_client, "/sign-in", email="two@example.test", password="Two!demo"
    ).status_code == 302
    assert second_client.get("/account").status_code == 200
    assert post_form(
        first_client, "/forgot-password", email="one@example.test"
    ).status_code == 200
    first_services, second_services = (
        first.extensions["local_auth_demo"],
        second.extensions["local_auth_demo"],
    )
    assert len(first_services.store.sessions) == len(second_services.store.sessions) == 1
    assert len(first_services.store.reset_requests["one@example.test"]) == 1
    assert len(first_services.store.reset_tokens) == 1
    assert second_services.store.reset_requests == second_services.store.reset_tokens == {}
    assert second_services.sink.links_snapshot() == ()
    assert set(first_services.store.accounts) == {"one@example.test"}
    assert set(second_services.store.accounts) == {"two@example.test"}
    # The absence of all external identity integrations needs repository inspection.


def test_tc_021_private_sink_complete_flow_and_fresh_instance() -> None:
    """Events stay in the originating app; external-delivery absence is an inspection."""
    app = create_app(
        clock=AdvancingClock(),
        token_generator=TokenSource(),
        synthetic_accounts={"owner@example.test": "Old!demo"},
    )
    services = app.extensions["local_auth_demo"]
    fresh = create_app(synthetic_accounts={"owner@example.test": "Old!demo"})
    client = app.test_client()
    acknowledgement = post_form(client, "/forgot-password", email="owner@example.test")
    (link_event,) = services.sink.links_snapshot()
    assert link_event.account_id == link_event.recipient == "owner@example.test"
    assert link_event.url.startswith("/reset/")
    assert services.sink.successes_snapshot() == ()
    assert link_event.url.encode() not in acknowledgement.data
    assert link_event.url not in str(acknowledgement.headers)
    reset = client.get(link_event.url)
    confirmed = client.post(
        link_event.url,
        data={"csrf_token": csrf_on(reset), "new_password": "New!demo"},
    )
    assert confirmed.status_code == 200
    (success_event,) = services.sink.successes_snapshot()
    assert success_event.account_id == success_event.recipient == "owner@example.test"
    assert success_event.completed_at == services.clock.now()
    assert not hasattr(success_event, "url")
    assert link_event.url.encode() not in confirmed.data
    assert b"owner@example.test" not in confirmed.data
    assert fresh.extensions["local_auth_demo"].sink.links_snapshot() == ()
    assert fresh.extensions["local_auth_demo"].sink.successes_snapshot() == ()
    for path in ("/sink", "/notifications", "/reset-links"):
        assert client.get(path).status_code == 404
    assert services.sink.links_snapshot() == (link_event,)
    assert services.sink.successes_snapshot() == (success_event,)


def test_tc_022_suite_collects_each_approved_automated_case() -> None:
    """Map each TC-001–TC-021 to discoverable, executable pytest functions.

    This guards the coverage map, not the browser/manual portions. Other
    tests exercise the public/private behavior rather than merely naming it.
    """
    test_dir = Path(__file__).parent
    names = {
        node.name
        for path in test_dir.glob("test_*.py")
        for node in ast.parse(path.read_text()).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }
    assert all(
        any(name.startswith(f"test_tc_{case:03d}_") for name in names)
        for case in range(1, 22)
    )
