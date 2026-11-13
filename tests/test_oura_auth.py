"""OAuth 更新・保存・フォールバックのオフライン検証。"""

import time
from unittest.mock import Mock

import pytest
import requests

from oura_auth import TokenResolver, save_github_secret
from oura_client import OuraClient


def resolver(expires_at: str | None = None) -> TokenResolver:
    return TokenResolver("client", "secret", "old-refresh", "old-access", expires_at, "write-token")


def token_response() -> Mock:
    return Mock(
        status_code=200,
        json=Mock(return_value={"access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 3600}),
        raise_for_status=Mock(),
    )


def test_unexpired_token_is_reused(monkeypatch):
    post = Mock(side_effect=AssertionError("refresh 不要"))
    monkeypatch.setattr(requests, "post", post)
    assert resolver(str(int(time.time()) + 3600)).resolve() == "old-access"
    post.assert_not_called()


def test_expired_token_rotates_and_persists(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    post = Mock(return_value=token_response())
    saved = []
    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(
        "oura_auth.save_github_secret", lambda name, value, token: saved.append((name, value, token)) or True
    )
    current = resolver("1")
    assert current.resolve() == "new-access"
    assert current.refresh_token == "new-refresh"
    assert saved[0] == ("OURA_REFRESH_TOKEN", "new-refresh", "write-token")
    assert saved[1] == ("OURA_ACCESS_TOKEN", "new-access", "write-token")
    assert saved[2][0] == "OURA_ACCESS_TOKEN_EXPIRES_AT"
    assert post.call_args.kwargs["data"]["refresh_token"] == "old-refresh"
    assert post.call_args.kwargs["headers"]["User-Agent"]


def test_persist_failure_keeps_current_run(monkeypatch, caplog):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(requests, "post", Mock(return_value=token_response()))
    monkeypatch.setattr("oura_auth.save_github_secret", lambda *args: False)
    assert resolver("1").resolve() == "new-access"
    assert "失敗" in caplog.text
    assert "new-refresh" not in caplog.text
    assert "new-access" not in caplog.text


def test_missing_write_token_warns_and_continues(monkeypatch, caplog):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(requests, "post", Mock(return_value=token_response()))
    current = resolver("1")
    current.write_token = None
    assert current.resolve() == "new-access"
    assert "再認可" in caplog.text


def test_pat_fallback_without_complete_oauth(monkeypatch):
    post = Mock(side_effect=AssertionError("refresh 不要"))
    monkeypatch.setattr(requests, "post", post)
    assert TokenResolver("client", None, "refresh", "pat").resolve() == "pat"
    with pytest.raises(ValueError, match="認証情報"):
        TokenResolver(None, None, None, None).resolve()


def test_401_refreshes_once(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(requests, "post", Mock(return_value=token_response()))
    monkeypatch.setattr("oura_auth.save_github_secret", lambda *args: True)
    unauthorized = Mock(status_code=401, raise_for_status=Mock(side_effect=requests.HTTPError()))
    success = Mock(status_code=200, raise_for_status=Mock(), json=Mock(return_value={"data": []}))
    get = Mock(side_effect=[unauthorized, success])
    monkeypatch.setattr(requests, "get", get)
    client = OuraClient("old-access", token_resolver=resolver(str(int(time.time()) + 3600)))
    assert client._get("daily_sleep") == {"data": []}
    assert get.call_count == 2
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer new-access"
    assert get.call_args.kwargs["headers"]["User-Agent"]


def test_gh_secret_uses_stdin_only(monkeypatch):
    run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr("oura_auth.subprocess.run", run)
    assert save_github_secret("OURA_REFRESH_TOKEN", "private-value", "write-token")
    assert "private-value" not in str(run.call_args.args)
    assert run.call_args.kwargs["input"] == "private-value"
    assert run.call_args.kwargs["env"]["GH_TOKEN"] == "write-token"


def test_local_keychain_reads_and_persists_rotated_tokens(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr("oura_auth.sys.platform", "darwin")
    stored = {
        "OURA_CLIENT_ID": "client",
        "OURA_CLIENT_SECRET": "secret",
        "OURA_REFRESH_TOKEN": "old-refresh",
        "OURA_ACCESS_TOKEN": "old-access",
        "OURA_ACCESS_TOKEN_EXPIRES_AT": "1",
    }
    monkeypatch.setattr("oura_auth._keychain_value", stored.get)
    monkeypatch.setattr("oura_auth._save_keychain", lambda name, value: stored.update({name: value}) or True)
    monkeypatch.setattr(requests, "post", Mock(return_value=token_response()))
    assert TokenResolver.from_environment().resolve() == "new-access"
    assert stored["OURA_REFRESH_TOKEN"] == "new-refresh"
    assert stored["OURA_ACCESS_TOKEN"] == "new-access"
