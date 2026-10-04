"""Issue35: 診断経路の秘匿と既存 payload/失敗伝播を合成データで検証."""
import logging
from unittest.mock import Mock

import pytest
import requests

import main
from discord_client import DiscordClient

SECRET = "TOKEN_WEBHOOK_SENTINEL"
HEALTH = "PRIVATE_HEALTH_SENTINEL"


def response(status=204, text=HEALTH):
    result = requests.Response()
    result.status_code = status
    result._content = text.encode()
    result.url = "https://example.invalid/" + SECRET
    return result


@pytest.fixture(autouse=True)
def fake_configuration(monkeypatch):
    monkeypatch.setenv("OURA_ACCESS_TOKEN", SECRET)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.invalid/" + SECRET)
    monkeypatch.setenv("DAILY_STEPS_GOAL", "8000")
    monkeypatch.setattr("time.sleep", lambda _: None)


def assert_private(caplog, capsys, payloads=()):
    captured = capsys.readouterr()
    for text in (caplog.text, captured.out, captured.err, str(payloads)):
        assert SECRET not in text
        assert HEALTH not in text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.parametrize("status", [401, 429, 500, 503])
@pytest.mark.parametrize("length", [1, 1000])
def test_discord_response_body_never_logged(monkeypatch, caplog, capsys, status, length):
    caplog.set_level(logging.DEBUG)
    post = Mock(return_value=response(status, (HEALTH + SECRET) * length))
    monkeypatch.setattr(requests, "post", post)
    assert DiscordClient("https://example.invalid/" + SECRET).send_message("normal") is False
    assert post.call_count == (3 if status in DiscordClient.RETRY_STATUS_CODES else 1)
    assert_private(caplog, capsys)
    assert f"status={status}" in caplog.text


@pytest.mark.parametrize("error_type", [requests.Timeout, requests.RequestException, requests.exceptions.InvalidURL])
def test_discord_request_error_never_logged(monkeypatch, caplog, capsys, error_type):
    error = error_type(SECRET + HEALTH)
    error.__cause__ = ValueError(HEALTH)
    post = Mock(side_effect=error)
    monkeypatch.setattr(requests, "post", post)
    assert DiscordClient("https://example.invalid/" + SECRET).send_message("normal") is False
    assert post.call_count == 3
    assert_private(caplog, capsys)


@pytest.mark.parametrize("slot", ["morning", "noon", "night"])
@pytest.mark.parametrize("kind", ["http", "timeout", "unexpected"])
def test_report_error_notice_contains_only_safe_diagnostics(monkeypatch, caplog, capsys, slot, kind):
    if kind == "http":
        error = requests.HTTPError(SECRET + HEALTH, response=response(401))
    elif kind == "timeout":
        error = requests.Timeout(SECRET + HEALTH)
    else:
        error = ValueError(SECRET + HEALTH)
    error.__cause__ = RuntimeError(HEALTH)
    monkeypatch.setattr(requests, "get", Mock(side_effect=error))
    sent = []
    def post(url, **kwargs):
        sent.append(kwargs["json"])
        return response()
    monkeypatch.setattr(requests, "post", post)
    assert getattr(main, "send_" + slot + "_report")() is False
    assert len(sent) == 1
    assert "エラー" in sent[0]["content"]
    assert_private(caplog, capsys, sent)


@pytest.mark.parametrize("slot", ["morning", "noon", "night"])
@pytest.mark.parametrize("second_failure", ["false", "exception"])
def test_failed_error_notice_is_bounded(monkeypatch, caplog, capsys, slot, second_failure):
    monkeypatch.setattr(requests, "get", Mock(side_effect=requests.Timeout(SECRET)))
    post = Mock(return_value=response(500), side_effect=RuntimeError(HEALTH) if second_failure == "exception" else None)
    monkeypatch.setattr(requests, "post", post)
    assert getattr(main, "send_" + slot + "_report")() is False
    assert post.call_count == (3 if second_failure == "false" else 1)
    assert_private(caplog, capsys)


def test_normal_health_payload_is_preserved(monkeypatch, caplog, capsys):
    post = Mock(return_value=response())
    monkeypatch.setattr(requests, "post", post)
    sections = [{"title": "Sleep", "description": HEALTH, "fields": [{"name": "Score", "value": "82"}]}]
    assert DiscordClient("https://example.invalid/" + SECRET).send_health_report("Morning", sections)
    assert post.call_args.kwargs["json"] == {
        "username": "Oura Ring Bot", "content": "Morning", "embeds": [
            {"title": "Sleep", "description": HEALTH, "color": 0x00D4AA, "fields": sections[0]["fields"]}
        ]}
    assert_private(caplog, capsys)


@pytest.mark.parametrize("slot", ["morning", "night"])
def test_optional_weekly_failure_still_sends_report(monkeypatch, caplog, capsys, slot):
    monkeypatch.setattr(requests, "get", Mock(return_value=response(200, '{"data": []}')))
    monkeypatch.setattr(main.OuraClient, "get_weekly_data", Mock(side_effect=requests.Timeout(SECRET + HEALTH)))
    post = Mock(return_value=response())
    monkeypatch.setattr(requests, "post", post)
    assert getattr(main, "send_" + slot + "_report")() is True
    assert post.call_count == 1
    assert "embeds" in post.call_args.kwargs["json"]
    assert_private(caplog, capsys, [post.call_args.kwargs["json"]])


def test_optional_stress_failure_is_safe(monkeypatch, caplog, capsys):
    monkeypatch.setattr(requests, "get", Mock(side_effect=requests.Timeout(HEALTH)))
    assert main.OuraClient(SECRET).get_daily_stress() is None
    assert_private(caplog, capsys)


def test_noon_skip_does_not_log_steps(monkeypatch, caplog, capsys):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(main.OuraClient, "get_activity", lambda *a: {"steps": 987654321})
    monkeypatch.setattr(main.OuraClient, "get_sleep", lambda *a: None)
    monkeypatch.setattr(main.OuraClient, "get_sleep_details", lambda *a: None)
    monkeypatch.setattr(main, "format_noon_report", lambda *a: ("title", [], False))
    post = Mock(side_effect=AssertionError("unexpected POST"))
    monkeypatch.setattr(requests, "post", post)
    assert main.send_noon_report() is True
    assert post.call_count == 0
    assert "987,654,321" not in caplog.text
    assert "987654321" not in caplog.text
    assert_private(caplog, capsys)


def test_invalid_configuration_is_safe(monkeypatch, caplog, capsys):
    monkeypatch.setenv("DAILY_STEPS_GOAL", SECRET + HEALTH)
    monkeypatch.setattr(requests, "post", Mock(return_value=response()))
    assert main.send_noon_report() is False
    assert_private(caplog, capsys)


@pytest.mark.parametrize("slot", ["morning", "noon", "night"])
@pytest.mark.parametrize("status", [401, 429, 503])
def test_http_failures_through_cli(monkeypatch, caplog, capsys, slot, status):
    monkeypatch.setattr("sys.argv", ["main.py", "--type", slot])
    get = Mock(return_value=response(status, HEALTH + SECRET))
    post = Mock(return_value=response(500, HEALTH))
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(requests, "post", post)
    with pytest.raises(SystemExit) as exit_info:
        main.main()
    assert exit_info.value.code == 1
    assert get.call_count == 3  # Oura の既存リトライ契約
    assert post.call_count == 3  # エラー通知1呼出、最大3試行
    assert_private(caplog, capsys, [c.kwargs["json"] for c in post.call_args_list])


def test_actual_invalid_webhook_url_is_safe(monkeypatch, caplog, capsys):
    # requests の URL 検証を実行し、transport への到達は禁止する.
    transport = Mock(side_effect=AssertionError("unexpected transport"))
    monkeypatch.setattr(requests.Session, "send", transport)
    assert DiscordClient("https://example.invalid:" + SECRET + "/webhook").send_message("normal") is False
    assert transport.call_count == 0
    assert_private(caplog, capsys)


def test_safe_diagnostic_never_stringifies_exception(caplog, capsys):
    from diagnostics import safe_diagnostic
    class HostileError(Exception):
        def __str__(self):
            raise AssertionError("must not stringify")
    text = safe_diagnostic(HostileError(), provider=SECRET, operation=HEALTH, status=SECRET, attempt=HEALTH)
    assert text == "provider=unknown operation=unknown error=unexpected"
    assert_private(caplog, capsys)


def test_test_entrypoint_unexpected_error_is_safe(monkeypatch, caplog, capsys):
    monkeypatch.setattr("sys.argv", ["main.py", "--test"])
    monkeypatch.setattr(requests, "post", Mock(side_effect=RuntimeError(SECRET + HEALTH)))
    with pytest.raises(SystemExit) as exit_info:
        main.main()
    assert exit_info.value.code == 1
    assert_private(caplog, capsys)


@pytest.mark.parametrize("slot", ["morning", "noon", "night"])
def test_success_through_real_clients_and_formatters(
    monkeypatch, caplog, capsys, slot, sample_sleep_data, sample_sleep_details,
    sample_readiness_data, sample_activity_data,
):
    import json
    from datetime import date
    monkeypatch.setattr(main, "get_jst_today", lambda: date(2026, 2, 17))
    monkeypatch.setattr(main, "get_jst_hour", lambda: 13)
    items = {"daily_sleep": sample_sleep_data, "sleep": sample_sleep_details,
             "daily_readiness": sample_readiness_data, "daily_activity": sample_activity_data}
    sent = []
    def send(request, **kwargs):
        if request.method == "GET":
            endpoint = request.url.split("?")[0].rsplit("/", 1)[1]
            return response(200, json.dumps({"data": [items[endpoint]]}))
        sent.append(json.loads(request.body))
        return response()
    # descriptor binding を避け、requests.PreparedRequest を引数に受け取る.
    monkeypatch.setattr(requests.Session, "send", Mock(side_effect=send))
    assert getattr(main, "send_" + slot + "_report")() is True
    assert len(sent) == 1
    assert sent[0]["embeds"]
    assert_private(caplog, capsys)
