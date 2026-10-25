"""TASK-002 traceable HTML/CSS and synthetic session checks.

Static assertions are only partial evidence for pictured appearance and browser
focus/masking behavior; they do not assert live browser fidelity.
"""

import re

from flask.testing import FlaskClient

from local_auth_demo import create_app, session_digest


def token_on(response_text: str) -> str:
    match = re.search(r'<input type="hidden" name="csrf_token" value="([^"]+)"', response_text)
    assert match is not None
    return match.group(1)


def sign_in(client: FlaskClient, email: str, password: str):
    csrf = token_on(client.get("/sign-in").get_data(as_text=True))
    return client.post(
        "/sign-in", data={"email": email, "password": password, "csrf_token": csrf}
    )


def test_tc_001_card_heading_white_background_and_thin_outline() -> None:
    client = create_app().test_client()
    page = client.get("/sign-in").get_data(as_text=True)
    css = client.get("/static/styles.css").get_data(as_text=True)
    assert '<section class="panel sign-in-panel" aria-labelledby="sign-in-title">' in page
    assert '<h1 id="sign-in-title">Sign in</h1>' in page
    assert "background: #fff;" in css
    assert "width: min(100%, 340px);" in css
    assert "margin: 20px auto;" in css
    assert "border: 1px solid #333;" in css


def test_tc_002_email_label_placeholder_and_focus_style() -> None:
    client = create_app().test_client()
    page = client.get("/sign-in").get_data(as_text=True)
    css = client.get("/static/styles.css").get_data(as_text=True)
    assert '<label for="email">Email address</label>' in page
    assert 'id="email" name="email" type="email" placeholder="name@example.com"' in page
    assert ":focus-visible" in css
    assert "outline: 2px solid #0645ad;" in css


def test_tc_003_password_label_masking_markup_and_no_reflection() -> None:
    client = create_app().test_client()
    page = client.get("/sign-in").get_data(as_text=True)
    assert '<label for="password">Password</label>' in page
    assert 'id="password" name="password" type="password" placeholder="********"' in page
    response = sign_in(client, "demo@example.test", "DemoSecret!")
    assert response.status_code == 401
    assert "DemoSecret!" not in response.get_data(as_text=True)
    assert 'role="alert"' in response.get_data(as_text=True)
    assert client.get("/account").status_code == 302


def test_tc_004_recovery_link_is_local_blue_and_underlined() -> None:
    client = create_app().test_client()
    page = client.get("/sign-in").get_data(as_text=True)
    css = client.get("/static/styles.css").get_data(as_text=True)
    assert '<a class="recovery-link" href="/forgot-password">Forgot password?</a>' in page
    assert "a { color: #0645ad; text-decoration: underline; }" in css
    assert client.get("/forgot-password").status_code == 200


def test_tc_006_wide_dark_submit_button() -> None:
    client = create_app().test_client()
    page = client.get("/sign-in").get_data(as_text=True)
    css = client.get("/static/styles.css").get_data(as_text=True)
    assert '<button type="submit">Sign in</button>' in page
    assert "width: 100%;" in css
    assert "background: #292929;" in css
    assert "color: #fff;" in css


def test_tc_007_footer_is_exactly_beneath_form_inside_card() -> None:
    page = create_app().test_client().get("/sign-in").get_data(as_text=True)
    assert re.search(
        r"</form>\s*<p class=\"sign-in-footer\">"
        r"No account\? Contact your administrator\.</p>\s*</section>",
        page,
    )


def test_tc_008_valid_credentials_use_digest_registry_and_guarded_account() -> None:
    app = create_app(synthetic_accounts={" TEST@EXAMPLE.TEST ": "SyntheticPass!"})
    client = app.test_client()
    assert client.get("/account").status_code == 302
    response = sign_in(client, " Test@Example.Test ", "SyntheticPass!")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/account")
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert "SameSite=Lax" in response.headers["Set-Cookie"]
    assert "SyntheticPass!" not in response.headers["Set-Cookie"]
    assert client.get("/account").status_code == 200
    store = app.extensions["local_auth_demo"].store
    with client.session_transaction() as cookie:
        opaque_token = cookie["session_id"]
        assert cookie["csrf_token"]
    with store.lock:
        assert opaque_token not in store.sessions
        assert store.sessions[session_digest(opaque_token)].account_id == "test@example.test"
        assert store.sessions[session_digest(opaque_token)].epoch == 0

    # A signed cookie alone is not authorization without a matching registry entry.
    with store.lock:
        store.sessions.pop(session_digest(opaque_token))
    assert client.get("/account").status_code == 302
    with client.session_transaction() as cookie:
        assert "session_id" not in cookie
        cookie["session_id"] = "forged-but-signed-cookie-value"
    assert client.get("/account").status_code == 302


def test_tc_008_session_cookie_is_secure_when_request_uses_https() -> None:
    client = create_app().test_client()
    response = client.get("/sign-in", base_url="https://localhost")
    assert "Secure" in response.headers["Set-Cookie"]
    assert "HttpOnly" in response.headers["Set-Cookie"]


def test_tc_008_invalid_credentials_and_csrf_do_not_grant_access() -> None:
    app = create_app()
    for email, password in (
        ("demo@example.test", "WrongPassword!"),
        ("nobody@example.test", "WrongPassword!"),
    ):
        client = app.test_client()
        response = sign_in(client, email, password)
        assert response.status_code == 401
        assert b"Invalid email or password" in response.data
        assert password.encode() not in response.data
        assert client.get("/account").status_code == 302
    for csrf in ("", "not-the-csrf-token"):
        client = app.test_client()
        client.get("/sign-in")
        response = client.post(
            "/sign-in",
            data={
                "email": "demo@example.test",
                "password": "SamplePass!123",
                "csrf_token": csrf,
            },
        )
        assert response.status_code == 400
        assert b'role="alert"' in response.data
        assert b"SamplePass!123" not in response.data
        assert client.get("/account").status_code == 302
    assert not app.extensions["local_auth_demo"].store.sessions


def test_tc_008_epoch_revocation_rotation_and_csrf_protected_sign_out() -> None:
    app = create_app()
    client = app.test_client()
    assert sign_in(client, "demo@example.test", "SamplePass!123").status_code == 302
    with client.session_transaction() as cookie:
        original = cookie["session_id"]
    assert sign_in(client, "demo@example.test", "SamplePass!123").status_code == 302
    store = app.extensions["local_auth_demo"].store
    with client.session_transaction() as cookie:
        rotated = cookie["session_id"]
    with store.lock:
        assert rotated != original
        assert session_digest(original) not in store.sessions
    invalid = client.post("/sign-out", data={"csrf_token": "bad"})
    assert invalid.status_code == 400
    assert b'role="alert"' in invalid.data
    assert client.get("/account").status_code == 200
    account_page = client.get("/account").get_data(as_text=True)
    csrf = token_on(account_page)
    response = client.post("/sign-out", data={"csrf_token": csrf})
    assert response.status_code == 302
    assert client.get("/account").status_code == 302
    with store.lock:
        assert session_digest(rotated) not in store.sessions

    assert sign_in(client, "demo@example.test", "SamplePass!123").status_code == 302
    with store.lock:
        store.accounts["demo@example.test"].session_epoch += 1
    assert client.get("/account").status_code == 302
    with client.session_transaction() as cookie:
        assert "session_id" not in cookie


def test_tc_019_sign_in_and_account_are_server_rendered_without_scripts() -> None:
    client = create_app().test_client()
    sign_in_page = client.get("/sign-in").get_data(as_text=True)
    assert '<form method="post" action="/sign-in">' in sign_in_page
    assert token_on(sign_in_page)
    assert "<script" not in sign_in_page
    assert sign_in(client, "demo@example.test", "SamplePass!123").status_code == 302
    account_page = client.get("/account").get_data(as_text=True)
    assert '<form method="post" action="/sign-out">' in account_page
    assert token_on(account_page)
    assert "<script" not in account_page
