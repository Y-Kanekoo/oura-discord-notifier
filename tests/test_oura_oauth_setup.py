"""初回認可の非シークレット経路。セットアップ本体は実行しない。"""

import sys
from io import BytesIO
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import requests

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from oura_oauth_setup import (  # noqa: E402
    REDIRECT_URI,
    SCOPES,
    CallbackHandler,
    build_authorization_url,
    exchange_code,
    make_pkce,
)


def test_authorization_url_has_exact_scope_redirect_and_pkce():
    verifier, challenge = make_pkce()
    assert 43 <= len(verifier) <= 128
    params = parse_qs(urlparse(build_authorization_url("client", "state", challenge)).query)
    assert params["redirect_uri"] == [REDIRECT_URI]
    assert params["scope"] == [SCOPES]
    assert params["state"] == ["state"]
    assert params["code_challenge"] == [challenge]
    assert params["code_challenge_method"] == ["S256"]


def test_code_exchange_uses_body_and_sanitizes_failure(monkeypatch):
    response = Mock(json=Mock(return_value={"access_token": "access", "refresh_token": "refresh", "expires_in": 3600}))
    monkeypatch.setattr(requests, "post", Mock(return_value=response))
    assert exchange_code("code", "verifier", "client", "secret")["refresh_token"] == "refresh"
    data = requests.post.call_args.kwargs["data"]
    assert data["redirect_uri"] == REDIRECT_URI
    assert data["code_verifier"] == "verifier"
    assert requests.post.call_args.kwargs["headers"]["User-Agent"]

    monkeypatch.setattr(requests, "post", Mock(side_effect=requests.Timeout("secret-value")))
    try:
        exchange_code("code", "verifier", "client", "secret")
    except RuntimeError as exc:
        assert "secret-value" not in str(exc)


def test_callback_checks_state_without_logging_code():
    server = SimpleNamespace(expected_state="expected", code=None, completed=Event())
    handler = object.__new__(CallbackHandler)
    handler.server = server
    handler.wfile = BytesIO()
    statuses = []
    handler.send_response = statuses.append
    handler.send_header = lambda *args: None
    handler.end_headers = lambda: None

    handler.path = "/callback?state=wrong&code=private-code"
    handler.do_GET()
    assert statuses[-1] == 400
    assert server.code is None
    assert not server.completed.is_set()
    assert b"private-code" not in handler.wfile.getvalue()

    handler.path = "/callback?state=expected&code=private-code"
    handler.do_GET()
    assert statuses[-1] == 200
    assert server.code == "private-code"
    assert server.completed.is_set()
    assert b"private-code" not in handler.wfile.getvalue()
