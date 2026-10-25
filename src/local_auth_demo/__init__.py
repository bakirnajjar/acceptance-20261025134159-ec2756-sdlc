"""Local-only Flask demonstration with isolated synthetic application state."""

import os
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from flask import Flask, render_template

from .state import SAMPLE_ACCOUNTS, MemoryStore


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
    app.extensions["local_auth_demo"] = AppServices(
        store=MemoryStore.with_synthetic_accounts(
            SAMPLE_ACCOUNTS if synthetic_accounts is None else synthetic_accounts
        ),
        clock=clock if clock is not None else UtcClock(),
        token_generator=(
            token_generator if token_generator is not None else lambda: secrets.token_urlsafe(32)
        ),
    )

    @app.get("/sign-in")
    def sign_in() -> str:
        return render_template("sign_in.html")

    @app.get("/forgot-password")
    def forgot_password() -> str:
        return render_template("forgot_password.html")

    return app
