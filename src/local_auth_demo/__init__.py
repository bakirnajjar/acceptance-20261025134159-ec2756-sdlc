"""Local-only Flask demonstration with isolated synthetic application state."""

import os
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

from flask import Flask, redirect, render_template, request, session, url_for
from flask.sessions import SecureCookieSessionInterface
from werkzeug.security import check_password_hash

from .state import SAMPLE_ACCOUNTS, MemoryStore, SessionRecord, normalize_email


class LocalSessionInterface(SecureCookieSessionInterface):
    """Use Secure on HTTPS while allowing the documented loopback HTTP demo."""

    def get_cookie_secure(self, app: Flask) -> bool:
        return request.is_secure or super().get_cookie_secure(app)


def session_digest(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


class Clock(Protocol):
    """Return an aware UTC instant; test clocks may advance without sleeping."""

    def now(self) -> datetime: ...


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True)
class AppServices:
    """Internal composition root, never exposed through a public HTTP route."""

    store: MemoryStore
    clock: Clock
    token_generator: Callable[[], str]


def create_app(
    *,
    clock: Clock | None = None,
    token_generator: Callable[[], str] | None = None,
    synthetic_accounts: Mapping[str, str] | None = None,
) -> Flask:
    """Create an independent local app; credentials are synthetic test data only."""
    app = Flask(__name__)
    # An unset key is random per app/restart, never a checked-in signing secret.
    app.secret_key = os.environ.get("LOCAL_AUTH_DEMO_SECRET_KEY") or secrets.token_hex(32)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    app.session_interface = LocalSessionInterface()
    app.extensions["local_auth_demo"] = AppServices(
        store=MemoryStore.with_synthetic_accounts(
            SAMPLE_ACCOUNTS if synthetic_accounts is None else synthetic_accounts
        ),
        clock=clock if clock is not None else UtcClock(),
        token_generator=(
            token_generator if token_generator is not None else lambda: secrets.token_urlsafe(32)
        ),
    )

    def csrf_token() -> str:
        token = session.get("csrf_token")
        if not isinstance(token, str) or not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    def valid_csrf() -> bool:
        expected = session.get("csrf_token")
        supplied = request.form.get("csrf_token")
        return (
            isinstance(expected, str)
            and isinstance(supplied, str)
            and bool(expected)
            and secrets.compare_digest(expected, supplied)
        )

    def current_account_id() -> str | None:
        token = session.get("session_id")
        if not isinstance(token, str) or not token:
            return None
        store = app.extensions["local_auth_demo"].store
        with store.lock:
            record = store.sessions.get(session_digest(token))
            account = store.accounts.get(record.account_id) if record is not None else None
            if account is not None and record.epoch == account.session_epoch:
                return account.id
        session.pop("session_id", None)
        return None

    @app.route("/sign-in", methods=["GET", "POST"])
    def sign_in():
        if request.method == "GET":
            return render_template("sign_in.html", csrf_token=csrf_token())
        if not valid_csrf():
            return (
                render_template(
                    "sign_in.html",
                    csrf_token=csrf_token(),
                    error="Your form expired. Please try again.",
                ),
                400,
            )

        email = normalize_email(request.form.get("email", ""))
        password = request.form.get("password", "")
        store = app.extensions["local_auth_demo"].store
        # Verification and registration share a lock with future reset commits.
        with store.lock:
            account = store.accounts.get(email)
            if account is not None and check_password_hash(account.password_hash, password):
                old_token = session.get("session_id")
                if isinstance(old_token, str):
                    store.sessions.pop(session_digest(old_token), None)
                # Session identifiers are independently random, not derived from credentials
                # or from the injectable reset-token generator.
                token = secrets.token_urlsafe(32)
                while session_digest(token) in store.sessions:
                    token = secrets.token_urlsafe(32)
                store.sessions[session_digest(token)] = SessionRecord(
                    account_id=account.id, epoch=account.session_epoch
                )
                session["session_id"] = token
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("account"))
        return (
            render_template(
                "sign_in.html",
                csrf_token=csrf_token(),
                error="Invalid email or password. Please try again.",
            ),
            401,
        )

    @app.get("/account")
    def account():
        if current_account_id() is None:
            return redirect(url_for("sign_in"))
        return render_template("account.html", csrf_token=csrf_token())

    @app.post("/sign-out")
    def sign_out():
        if current_account_id() is None:
            return redirect(url_for("sign_in"))
        if not valid_csrf():
            return (
                render_template(
                    "account.html",
                    csrf_token=csrf_token(),
                    error="Your form expired. Please try again.",
                ),
                400,
            )
        token = session.pop("session_id")
        store = app.extensions["local_auth_demo"].store
        with store.lock:
            store.sessions.pop(session_digest(token), None)
        session.clear()
        return redirect(url_for("sign_in"))

    @app.get("/forgot-password")
    def forgot_password() -> str:
        return render_template("forgot_password.html")

    return app
