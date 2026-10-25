"""Per-application, process-local state for synthetic demonstration identities.

All reads and writes to the mutable mappings must occur while holding ``lock``.
Later session, quota, reset, and notification operations must share that lock so
their state transitions cannot interleave inside a single process.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock

from werkzeug.security import generate_password_hash

SAMPLE_ACCOUNTS = {"demo@example.test": "SamplePass!123"}


def normalize_email(email: str) -> str:
    """Use one identity key for synthetic account lookup and future requests."""
    return email.strip().casefold()


@dataclass
class Account:
    id: str
    email: str
    password_hash: str
    session_epoch: int = 0


@dataclass(frozen=True)
class SessionRecord:
    account_id: str
    epoch: int


@dataclass
class ResetTokenRecord:
    account_id: str
    issued_at: datetime
    consumed: bool = False


@dataclass(frozen=True)
class ResetLinkEvent:
    account_id: str
    recipient: str
    url: str
    issued_at: datetime


@dataclass(frozen=True)
class ResetSuccessEvent:
    account_id: str
    recipient: str
    completed_at: datetime


class MemoryNotificationSink:
    """Private per-app reset events; snapshots are only for same-process callers."""

    def __init__(self, lock: RLock) -> None:
        self._lock = lock
        self._links: list[ResetLinkEvent] = []
        self._successes: list[ResetSuccessEvent] = []

    def record_link(self, account_id: str, recipient: str, url: str, issued_at: datetime) -> None:
        with self._lock:
            self._links.append(ResetLinkEvent(account_id, recipient, url, issued_at))

    def links_snapshot(self) -> tuple[ResetLinkEvent, ...]:
        with self._lock:
            return tuple(self._links)

    def record_success(self, account_id: str, recipient: str, completed_at: datetime) -> None:
        with self._lock:
            self._successes.append(ResetSuccessEvent(account_id, recipient, completed_at))

    def successes_snapshot(self) -> tuple[ResetSuccessEvent, ...]:
        with self._lock:
            return tuple(self._successes)


@dataclass
class MemoryStore:
    """One instance per app; future services index only session/token digests."""

    lock: RLock = field(default_factory=RLock)
    accounts: dict[str, Account] = field(default_factory=dict)
    sessions: dict[str, SessionRecord] = field(default_factory=dict)
    reset_requests: dict[str, list[datetime]] = field(default_factory=dict)
    reset_tokens: dict[str, ResetTokenRecord] = field(default_factory=dict)

    @classmethod
    def with_synthetic_accounts(cls, credentials: Mapping[str, str]) -> "MemoryStore":
        store = cls()
        for email, password in credentials.items():
            key = normalize_email(email)
            if not key or not password or key in store.accounts:
                raise ValueError("Synthetic account emails must be unique and nonempty")
            store.accounts[key] = Account(
                id=key,
                email=key,
                password_hash=generate_password_hash(password),
            )
        return store
