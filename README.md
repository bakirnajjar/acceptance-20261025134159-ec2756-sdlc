# acceptance-20261025134159-ec2756-sdlc
Synthetic Futuristic acceptance test repository for SDLC stage outputs. No real data. Safe to delete.

## Local Python scaffold

This is a Python 3.12 Flask/Jinja **scaffold only**. It includes dependency
management and a smoke test, but no application factory, pages, sign-in or
recovery behavior yet. It uses synthetic data only.

Install [uv](https://docs.astral.sh/uv/) and make Python 3.12 available, then
run from the repository root:

```sh
uv sync --python 3.12
```

Build (compile-check the source and tests):

```sh
uv run --python 3.12 python3.12 -m compileall -q src tests
```

Test:

```sh
uv run --python 3.12 python3.12 -m pytest
```

The approved `python3.12 -m pytest` form also works after activating the
virtual environment with `source .venv/bin/activate`. Without activation,
use `uv run` as above so the dev dependencies are available.

Lint:

```sh
uv run --python 3.12 ruff check .
```

Start (future task): **not available in this scaffold**. Once a later task
provides `create_app` and HTML routes, the planned local development command
is `uv run --python 3.12 flask --app local_auth_demo:create_app run --debug`.
Do not run it against this scaffold: there is no Flask application to serve yet.
No deployment or external integration is provided.
