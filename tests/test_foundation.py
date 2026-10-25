"""Incremental TC-018/019/020 checks for the local foundation."""

import hashlib
import re
import sys
from datetime import UTC, datetime

from flask import Flask
from werkzeug.security import check_password_hash, generate_password_hash

from local_auth_demo import create_app
from local_auth_demo.state import Account, ResetTokenRecord, SessionRecord


def test_tc_018_python312_factory_serves_local_pages() -> None:
    assert sys.version_info[:2] == (3, 12)
    app = create_app()
    assert isinstance(app, Flask)
    for path in ("/sign-in", "/forgot-password"):
        response = app.test_client().get(path)
        assert response.status_code == 200
        assert response.mimetype == "text/html"
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
    assert client.post("/forgot-password").status_code == 405


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
