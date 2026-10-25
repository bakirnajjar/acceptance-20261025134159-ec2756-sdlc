"""Smoke checks for the project scaffold, not application behavior."""

from flask import Flask

import local_auth_demo


def test_flask_and_jinja_are_available() -> None:
    assert local_auth_demo.__name__ == "local_auth_demo"

    app = Flask(__name__)
    template = app.jinja_env.from_string("{{ message }}")
    assert template.render(message="Scaffold ready") == "Scaffold ready"
