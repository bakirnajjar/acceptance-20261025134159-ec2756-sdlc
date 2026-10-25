"""Local-only Flask demonstration with isolated synthetic application state."""

import logging
import os
import re
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Protocol

from flask import Flask, redirect, render_template, request, session, url_for
from flask.sessions import SecureCookieSessionInterface
from werkzeug.security import check_password_hash, generate_password_hash

from .state import (
    SAMPLE_ACCOUNTS,
    MemoryNotificationSink,
    MemoryStore,
    ResetTokenRecord,
    SessionRecord,
    normalize_email,
)

EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}"
)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
RESET_LIFETIME = timedelta(seconds=1800)
RESET_WINDOW = timedelta(seconds=3600)


class ResetPathLogFilter(logging.Filter):
    """Redact bearer path components from Werkzeug's local access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = re.sub(r"/reset/[A-Za-z0-9_-]+", "/reset/[redacted]", message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


# The local Flask CLI uses Werkzeug's process-wide access logger, not an app logger.
logging.getLogger("werkzeug").addFilter(ResetPathLogFilter())


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
    sink: MemoryNotificationSink


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
    store = MemoryStore.with_synthetic_accounts(
        SAMPLE_ACCOUNTS if synthetic_accounts is None else synthetic_accounts
    )
    app.extensions["local_auth_demo"] = AppServices(
        store=store,
        clock=clock if clock is not None else UtcClock(),
        token_generator=(
            token_generator if token_generator is not None else lambda: secrets.token_urlsafe(32)
        ),
        sink=MemoryNotificationSink(store.lock),
    )

    @app.after_request
    def protect_recovery_responses(response):
        if request.path == "/forgot-password" or request.path.startswith("/reset/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

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

    def available_reset_record(
        store: MemoryStore, token: str, now: datetime
    ) -> ResetTokenRecord | None:
        """Call only while holding store.lock; a POST must check again at commit."""
        if not TOKEN_PATTERN.fullmatch(token):
            return None
        record = store.reset_tokens.get(session_digest(token))
        if (
            record is None
            or record.consumed
            or record.account_id not in store.accounts
            or not (record.issued_at <= now < record.issued_at + RESET_LIFETIME)
        ):
            return None
        return record

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

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "GET":
            return render_template("forgot_password.html", csrf_token=csrf_token())
        if not valid_csrf():
            return (
                render_template(
                    "forgot_password.html",
                    csrf_token=csrf_token(),
                    error="Your form expired. Please try again.",
                ),
                400,
            )
        email = normalize_email(request.form.get("email", ""))
        if not EMAIL_PATTERN.fullmatch(email) or email.startswith(".") or ".." in email:
            return (
                render_template(
                    "forgot_password.html",
                    csrf_token=csrf_token(),
                    error="Enter a valid email address.",
                ),
                400,
            )

        services = app.extensions["local_auth_demo"]
        store = services.store
        with store.lock:
            account = store.accounts.get(email)
            if account is not None:
                now = services.clock.now()
                recent = [
                    instant
                    for instant in store.reset_requests.get(account.id, ())
                    if instant > now - RESET_WINDOW
                ]
                store.reset_requests[account.id] = recent
                if len(recent) < 5:
                    token = services.token_generator()
                    if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
                        raise ValueError("Reset token source must return a URL-safe token")
                    digest = session_digest(token)
                    # Do not overwrite an outstanding link if a source repeats a value.
                    if digest in store.reset_tokens:
                        raise ValueError("Reset token source returned a duplicate token")
                    store.reset_tokens[digest] = ResetTokenRecord(account.id, now)
                    store.reset_requests[account.id].append(now)
                    services.sink.record_link(
                        account.id,
                        account.email,
                        url_for("reset_password", token=token),
                        now,
                    )
        return render_template("forgot_acknowledgement.html")

    @app.route("/reset/<token>", methods=["GET", "POST"])
    def reset_password(token: str):
        services = app.extensions["local_auth_demo"]
        store = services.store
        with store.lock:
            available = available_reset_record(store, token, services.clock.now()) is not None
        if not available:
            return render_template("reset_unavailable.html")
        if request.method == "GET":
            return render_template("reset_password.html", token=token, csrf_token=csrf_token())
        if not valid_csrf():
            return (
                render_template(
                    "reset_password.html",
                    token=token,
                    csrf_token=csrf_token(),
                    error="Your form expired. Please try again.",
                ),
                400,
            )
        password = request.form.get("new_password", "")
        if not password:
            return (
                render_template(
                    "reset_password.html",
                    token=token,
                    csrf_token=csrf_token(),
                    error="Enter a new password.",
                ),
                400,
            )

        # Hash before taking the shared lock; expiry and consumption are checked
        # again under that lock before any account/session/notification mutation.
        password_hash = generate_password_hash(password)
        with store.lock:
            now = services.clock.now()
            record = available_reset_record(store, token, now)
            if record is None:
                return render_template("reset_unavailable.html")
            account = store.accounts[record.account_id]
            account.password_hash = password_hash
            record.consumed = True
            account.session_epoch += 1
            for digest, active in list(store.sessions.items()):
                if active.account_id == account.id:
                    del store.sessions[digest]
            services.sink.record_success(account.id, account.email, now)
        return render_template("reset_success.html")

    return app
