"""TASK-004 reset completion and private success-event regression tests."""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

from flask.testing import FlaskClient
from werkzeug.security import check_password_hash

from local_auth_demo import create_app, session_digest


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
        return f"synthetic-reset-{self.count}"


def csrf_on(page) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def issue_link(app, email: str = "owner@example.test") -> str:
    client = app.test_client()
    csrf = csrf_on(client.get("/forgot-password"))
    response = client.post("/forgot-password", data={"csrf_token": csrf, "email": email})
    assert response.status_code == 200
    return app.extensions["local_auth_demo"].sink.links_snapshot()[-1].url


def reset_form(client: FlaskClient, link: str) -> str:
    page = client.get(link)
    assert page.status_code == 200
    assert '<label for="new-password">New password</label>' in page.get_data(as_text=True)
    assert 'name="new_password" type="password"' in page.get_data(as_text=True)
    return csrf_on(page)


def complete(client: FlaskClient, link: str, csrf: str, password: str):
    return client.post(link, data={"csrf_token": csrf, "new_password": password})


def sign_in(app, password: str, email: str = "owner@example.test"):
    client = app.test_client()
    csrf = csrf_on(client.get("/sign-in"))
    response = client.post(
        "/sign-in", data={"csrf_token": csrf, "email": email, "password": password}
    )
    return client, response


def test_tc_013_replay_cannot_change_password_or_add_event() -> None:
    app = create_app(synthetic_accounts={"owner@example.test": "Old!demo"})
    link = issue_link(app)
    client = app.test_client()
    csrf = reset_form(client, link)
    first = complete(client, link, csrf, "First!demo")
    assert first.status_code == 200
    assert b"Password reset" in first.data
    services = app.extensions["local_auth_demo"]
    (event,) = services.sink.successes_snapshot()
    assert event.account_id == event.recipient == "owner@example.test"

    replay = complete(client, link, csrf, "Second!demo")
    unavailable = client.get(link)
    assert replay.status_code == unavailable.status_code == 200
    assert replay.data == unavailable.data
    assert tuple(replay.headers.items()) == tuple(unavailable.headers.items())
    assert b"Reset link unavailable" in replay.data
    assert link.encode() not in replay.data
    assert services.sink.successes_snapshot() == (event,)
    with services.store.lock:
        assert services.store.reset_tokens[session_digest(link.rsplit("/", 1)[1])].consumed
        assert services.store.accounts["owner@example.test"].session_epoch == 1
        assert check_password_hash(
            services.store.accounts["owner@example.test"].password_hash, "First!demo"
        )
    assert sign_in(app, "Second!demo")[1].status_code == 401


def test_tc_013_simultaneous_posts_only_one_wins() -> None:
    app = create_app(synthetic_accounts={"owner@example.test": "Old!demo"})
    link = issue_link(app)
    clients = (app.test_client(), app.test_client())
    csrf_values = tuple(reset_form(client, link) for client in clients)
    barrier = Barrier(2)

    def submit(index: int):
        barrier.wait(timeout=10)
        password = ("First!demo", "Second!demo")[index]
        return password, complete(clients[index], link, csrf_values[index], password)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(submit, range(2)))
    winners = [password for password, response in results if b"Password reset" in response.data]
    losers = [response for _, response in results if b"Reset link unavailable" in response.data]
    assert len(winners) == len(losers) == 1
    assert all(response.status_code == 200 for _, response in results)
    services = app.extensions["local_auth_demo"]
    (success_event,) = services.sink.successes_snapshot()
    assert success_event.account_id == success_event.recipient == "owner@example.test"
    with services.store.lock:
        account = services.store.accounts["owner@example.test"]
        assert account.session_epoch == 1
        assert check_password_hash(account.password_hash, winners[0])
        assert not check_password_hash(
            account.password_hash, ({"First!demo", "Second!demo"} - set(winners)).pop()
        )


def test_tc_014_issue_time_boundary_and_open_form_expiry() -> None:
    # Each boundary has an independent unused token; a successful reset cannot
    # accidentally make the expiry assertion pass by consuming its token.
    for age, password, should_succeed in (
        (1799, "Before!demo", True),
        (1800, "At!demo", False),
        (1801, "Later!demo", False),
    ):
        clock = AdvancingClock()
        app = create_app(
            clock=clock,
            token_generator=TokenSource(),
            synthetic_accounts={"owner@example.test": "Old!demo"},
        )
        link = issue_link(app)
        client = app.test_client()
        csrf = reset_form(client, link)
        clock.advance(age)
        response = complete(client, link, csrf, password)
        services = app.extensions["local_auth_demo"]
        with services.store.lock:
            account = services.store.accounts["owner@example.test"]
            token_record = services.store.reset_tokens[session_digest(link.rsplit("/", 1)[1])]
            assert check_password_hash(
                account.password_hash, password if should_succeed else "Old!demo"
            )
            assert token_record.consumed is should_succeed
        assert len(services.sink.successes_snapshot()) == int(should_succeed)
        assert (b"Password reset" in response.data) is should_succeed
        if should_succeed:
            assert sign_in(app, "Old!demo")[1].status_code == 401
            assert sign_in(app, password)[1].status_code == 302
        else:
            assert b"Reset link unavailable" in response.data
            assert sign_in(app, password)[1].status_code == 401
            assert sign_in(app, "Old!demo")[1].status_code == 302
            clock.advance(3600)
            assert b"Reset link unavailable" in complete(client, link, csrf, password).data

    clock = AdvancingClock()
    app = create_app(
        clock=clock,
        token_generator=TokenSource(),
        synthetic_accounts={"owner@example.test": "Old!demo"},
    )
    link = issue_link(app)
    clock.advance(1799)
    client = app.test_client()
    csrf = reset_form(client, link)
    clock.advance(1)
    assert b"Reset link unavailable" in complete(client, link, csrf, "Late!demo").data
    services = app.extensions["local_auth_demo"]
    with services.store.lock:
        assert check_password_hash(
            services.store.accounts["owner@example.test"].password_hash, "Old!demo"
        )
        assert not services.store.reset_tokens[session_digest(link.rsplit("/", 1)[1])].consumed
    assert services.sink.successes_snapshot() == ()


def test_tc_015_valid_post_changes_credentials_and_errors_do_not_mutate() -> None:
    clock = AdvancingClock()
    app = create_app(
        clock=clock,
        synthetic_accounts={"owner@example.test": "Old!demo"},
    )
    link = issue_link(app)
    client = app.test_client()
    csrf = reset_form(client, link)
    services = app.extensions["local_auth_demo"]
    for data in (
        {"csrf_token": csrf},
        {"csrf_token": csrf, "new_password": ""},
        {"csrf_token": "", "new_password": "New!demo"},
        {"csrf_token": "invalid", "new_password": "New!demo"},
        {"new_password": "New!demo"},
    ):
        response = client.post(link, data=data)
        assert response.status_code == 400
        assert b'role="alert"' in response.data
        assert b'aria-describedby="reset-error"' in response.data
        assert b"New!demo" not in response.data
        with services.store.lock:
            assert check_password_hash(
                services.store.accounts["owner@example.test"].password_hash, "Old!demo"
            )
            assert not services.store.reset_tokens[session_digest(link.rsplit("/", 1)[1])].consumed
        assert services.sink.successes_snapshot() == ()
    unknown = client.post(
        "/reset/not-a-real-link", data={"csrf_token": csrf, "new_password": "New!demo"}
    )
    assert b"Reset link unavailable" in unknown.data
    assert b"New!demo" not in unknown.data
    assert services.sink.successes_snapshot() == ()
    assert sign_in(app, "Old!demo")[1].status_code == 302

    success = complete(client, link, csrf, "New!demo")
    assert success.status_code == 200
    assert b"Password reset" in success.data
    assert link.encode() not in success.data + str(success.headers).encode()
    assert b"New!demo" not in success.data + str(success.headers).encode()
    assert "no-store" in success.headers["Cache-Control"]
    assert success.headers["Referrer-Policy"] == "no-referrer"
    assert sign_in(app, "Old!demo")[1].status_code == 401
    new_client, authenticated = sign_in(app, "New!demo")
    assert authenticated.status_code == 302
    assert new_client.get("/account").status_code == 200


def test_tc_015_invalid_expired_and_consumed_posts_share_neutral_response() -> None:
    clock = AdvancingClock()
    app = create_app(
        clock=clock,
        token_generator=TokenSource(),
        synthetic_accounts={"owner@example.test": "Old!demo"},
    )
    consumed_link = issue_link(app)
    expired_link = issue_link(app)
    client = app.test_client()
    csrf = reset_form(client, consumed_link)
    assert complete(client, consumed_link, csrf, "New!demo").status_code == 200
    clock.advance(1800)
    data = {"csrf_token": csrf, "new_password": "Unexpected!demo"}
    outcomes = [
        client.post(path, data=data)
        for path in (consumed_link, expired_link, "/reset/unknown-token")
    ]
    assert all(response.status_code == 200 for response in outcomes)
    assert outcomes[0].data == outcomes[1].data == outcomes[2].data
    assert [tuple(response.headers.items()) for response in outcomes] == [
        tuple(outcomes[0].headers.items())
    ] * 3
    assert b"Reset link unavailable" in outcomes[0].data
    services = app.extensions["local_auth_demo"]
    assert len(services.sink.successes_snapshot()) == 1
    with services.store.lock:
        assert check_password_hash(
            services.store.accounts["owner@example.test"].password_hash, "New!demo"
        )
        assert not services.store.reset_tokens[
            session_digest(expired_link.rsplit("/", 1)[1])
        ].consumed

def test_tc_016_reset_revokes_all_owner_sessions_but_not_other_account() -> None:
    app = create_app(
        synthetic_accounts={
            "owner@example.test": "Old!demo",
            "other@example.test": "Other!demo",
        }
    )
    first, first_login = sign_in(app, "Old!demo")
    second, second_login = sign_in(app, "Old!demo")
    other, other_login = sign_in(app, "Other!demo", "other@example.test")
    assert all(response.status_code == 302 for response in (first_login, second_login, other_login))
    for client in (first, second, other):
        assert client.get("/account").status_code == 200
    with first.session_transaction() as cookie:
        first_digest = session_digest(cookie["session_id"])
    with second.session_transaction() as cookie:
        second_digest = session_digest(cookie["session_id"])
    with other.session_transaction() as cookie:
        other_digest = session_digest(cookie["session_id"])
    assert len({first_digest, second_digest, other_digest}) == 3

    link = issue_link(app)
    resetter = app.test_client()
    assert complete(resetter, link, reset_form(resetter, link), "New!demo").status_code == 200
    store = app.extensions["local_auth_demo"].store
    with store.lock:
        assert first_digest not in store.sessions
        assert second_digest not in store.sessions
        assert store.sessions[other_digest].account_id == "other@example.test"
        assert store.accounts["owner@example.test"].session_epoch == 1
        assert store.accounts["other@example.test"].session_epoch == 0
    assert first.get("/account").status_code == second.get("/account").status_code == 302
    assert other.get("/account").status_code == 200


def test_tc_017_tc_019_tc_021_private_owner_events_and_server_pages() -> None:
    clock = AdvancingClock()
    app = create_app(
        clock=clock,
        token_generator=TokenSource(),
        synthetic_accounts={"owner@example.test": "Old!demo"},
    )
    services = app.extensions["local_auth_demo"]
    for password in ("First!demo", "Second!demo"):
        link = issue_link(app)
        client = app.test_client()
        page = client.get(link)
        assert '<form method="post" action="' in page.get_data(as_text=True)
        assert "<script" not in page.get_data(as_text=True)
        csrf = csrf_on(page)
        confirmation = complete(client, link, csrf, password)
        assert confirmation.status_code == 200
        assert b"<h1>Password reset</h1>" in confirmation.data
        assert "<script" not in confirmation.get_data(as_text=True)
        assert link.encode() not in confirmation.data
        assert b"Reset link unavailable" in complete(client, link, csrf, password).data
        assert len(services.sink.successes_snapshot()) == (1 if password == "First!demo" else 2)
    assert len(services.sink.links_snapshot()) == 2
    successes = services.sink.successes_snapshot()
    assert all(
        event.account_id == event.recipient == "owner@example.test"
        and event.completed_at == clock.now()
        for event in successes
    )
    assert all(not hasattr(event, "url") and not hasattr(event, "password") for event in successes)
    assert b"Reset link unavailable" in app.test_client().post(
        "/reset/invalid", data={"csrf_token": "any", "new_password": "Third!demo"}
    ).data
    expired_link = issue_link(app)
    expiring_client = app.test_client()
    expiring_csrf = reset_form(expiring_client, expired_link)
    clock.advance(1800)
    expired = complete(expiring_client, expired_link, expiring_csrf, "Third!demo")
    assert expired.status_code == 200
    assert b"Reset link unavailable" in expired.data
    assert expired_link.encode() not in expired.data
    assert services.sink.successes_snapshot() == successes
    fresh = create_app(synthetic_accounts={"owner@example.test": "Old!demo"})
    assert fresh.extensions["local_auth_demo"].sink.links_snapshot() == ()
    assert fresh.extensions["local_auth_demo"].sink.successes_snapshot() == ()
    for path in ("/sink", "/notifications", "/reset-links"):
        assert app.test_client().get(path).status_code == 404
