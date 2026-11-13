"""Oura OAuth の初回認可。実行時にのみブラウザと loopback callback を使用する。"""

import base64
import hashlib
import secrets
import socket
import sys
import threading
import time
import webbrowser
from getpass import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from oura_auth import (  # noqa: E402
    TOKEN_URL,
    USER_AGENT,
    _save_keychain,
    save_github_secret,
)

AUTHORIZE_URL = "https://cloud.ouraring.com/oauth/authorize"
REDIRECT_URI = "http://localhost:8765/callback"
SCOPES = "daily personal heartrate workout"


def make_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorization_url(client_id: str, state: str, challenge: str) -> str:
    return (
        AUTHORIZE_URL
        + "?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": REDIRECT_URI,
                "scope": SCOPES,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
    )


def exchange_code(code: str, verifier: str, client_id: str, client_secret: str) -> dict[str, str | int]:
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": client_id,
                "client_secret": client_secret,
                "code_verifier": verifier,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("refresh_token"), str)
            or not payload["refresh_token"]
            or not isinstance(payload.get("access_token"), str)
            or not payload["access_token"]
            or int(payload["expires_in"]) <= 0
        ):
            raise ValueError
        return payload
    except (requests.RequestException, KeyError, TypeError, ValueError, AttributeError):
        raise RuntimeError("Oura の認可コード交換に失敗しました") from None


class CallbackServer(HTTPServer):
    def __init__(self, address: tuple[str, int], family: socket.AddressFamily, expected_state: str) -> None:
        self.address_family = family
        self.expected_state = expected_state
        self.code: str | None = None
        self.completed = threading.Event()
        super().__init__(address, CallbackHandler)

    def server_bind(self) -> None:
        if self.address_family == socket.AF_INET6:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        super().server_bind()


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        server: CallbackServer = self.server  # type: ignore[assignment]
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        valid = parsed.path == "/callback" and params.get("state") == [server.expected_state]
        if valid and len(params.get("code", [])) == 1:
            server.code = params["code"][0]
            server.completed.set()
            status, message = 200, "認可が完了しました。このタブを閉じてください。"
        elif valid and "error" in params:
            server.completed.set()
            status, message = 400, "認可が拒否されました。"
        else:
            status, message = 400, "無効な callback です。"
        body = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        # URL に認可コードが含まれるので HTTP サーバーのログは出さない。
        return


def wait_for_code(state: str, authorization_url: str) -> str:
    servers: list[CallbackServer] = []
    try:
        servers.append(CallbackServer(("127.0.0.1", 8765), socket.AF_INET, state))
        servers.append(CallbackServer(("::1", 8765), socket.AF_INET6, state))
    except OSError:
        for server in servers:
            server.server_close()
        raise RuntimeError("callback 用ポート 8765 を開けませんでした") from None
    threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in servers]
    try:
        for thread in threads:
            thread.start()
        # client_id を標準出力へ出さず、実際の URL はブラウザに渡す。
        print("認可 URL: https://cloud.ouraring.com/oauth/authorize?client_id=[非表示]&...")
        try:
            opened = webbrowser.open(authorization_url)
        except Exception:
            raise RuntimeError("ブラウザを開けませんでした") from None
        if not opened:
            raise RuntimeError("ブラウザを開けませんでした")
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            for server in servers:
                if server.completed.wait(timeout=0.2):
                    if server.code:
                        return server.code
                    raise RuntimeError("Oura の認可が拒否されました")
        raise RuntimeError("認可 callback が時間内に届きませんでした")
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            if thread.is_alive():
                thread.join()


def main() -> None:
    client_id = getpass("Oura Client ID: ")
    client_secret = getpass("Oura Client Secret: ")
    write_token = getpass("GitHub Secrets 更新用 PAT: ")
    if not client_id or not client_secret or not write_token:
        raise RuntimeError("必須の認証情報が入力されていません")
    verifier, challenge = make_pkce()
    state = secrets.token_urlsafe(32)
    code = wait_for_code(state, build_authorization_url(client_id, state, challenge))
    payload = exchange_code(code, verifier, client_id, client_secret)
    values = {
        "OURA_CLIENT_ID": client_id,
        "OURA_CLIENT_SECRET": client_secret,
        "OURA_REFRESH_TOKEN": str(payload["refresh_token"]),
        "OURA_ACCESS_TOKEN": str(payload["access_token"]),
        "OURA_ACCESS_TOKEN_EXPIRES_AT": str(int(time.time()) + int(payload["expires_in"])),
    }
    failures = [name for name, value in values.items() if not save_github_secret(name, value, write_token)]
    if failures:
        raise RuntimeError("GitHub Secrets の保存に失敗しました。設定を確認してください")
    if sys.platform == "darwin":
        for name, value in values.items():
            if not _save_keychain(name, value):
                print(f"Keychain {name} の保存に失敗しました")
    print("Oura OAuth 認証情報を GitHub Secrets に保存しました")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError) as exc:
        # 例外文だけを表示し、HTTP 応答や入力値を出さない。
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
