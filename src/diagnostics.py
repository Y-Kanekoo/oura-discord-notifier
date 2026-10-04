"""定期通知と共有 HTTP client の許可項目だけから診断を作る."""

import logging

import requests


def suppress_http_debug_logs() -> None:
    """requests の低層 DEBUG ログに URL/headers を出さない."""
    logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)


def safe_diagnostic(
    error: Exception | None = None,
    *,
    provider: str,
    operation: str,
    status: int | None = None,
    attempt: int | None = None,
) -> str:
    """原文・repr・chain・body を読まず、固定分類と検証済み整数だけ返す."""
    provider = provider if provider in {"oura", "discord", "notification"} else "unknown"
    operation = operation if operation in {
        "request", "send", "morning", "noon", "night", "weekly", "stress", "error_notice",
    } else "unknown"
    category = "unexpected"
    if isinstance(error, requests.Timeout):
        category = "timeout"
    elif isinstance(error, (requests.exceptions.InvalidURL, requests.exceptions.MissingSchema,
                            requests.exceptions.InvalidSchema)):
        category = "invalid_url"
    elif isinstance(error, requests.HTTPError):
        category = "http"
        if error.response is not None:
            status = error.response.status_code
    elif isinstance(error, requests.RequestException):
        category = "request"
    elif error is None and status is not None:
        category = "http"
    fields = [f"provider={provider}", f"operation={operation}", f"error={category}"]
    if type(status) is int and 100 <= status <= 599:
        fields.append(f"status={status}")
    if type(attempt) is int and attempt > 0:
        fields.append(f"attempt={attempt}")
    return " ".join(fields)
