"""Oura OAuth トークンの解決と安全な保存。"""

import logging
import os
import subprocess
import sys
import time

import requests

from diagnostics import suppress_http_debug_logs

TOKEN_URL = "https://api.ouraring.com/oauth/token"
USER_AGENT = "oura-discord-notifier/1.0"
REPOSITORY = "Y-Kanekoo/oura-discord-notifier"
KEYCHAIN_SERVICE = "oura-discord-notifier"
logger = logging.getLogger(__name__)


def save_github_secret(name: str, value: str, write_token: str) -> bool:
    """gh には値を標準入力だけで渡す。"""
    try:
        result = subprocess.run(
            ["gh", "secret", "set", name, "--repo", REPOSITORY],
            input=value,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
            env={**os.environ, "GH_TOKEN": write_token},
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _keychain_value(name: str) -> str | None:
    if sys.platform != "darwin":
        return None
    try:
        import keyring

        return keyring.get_password(KEYCHAIN_SERVICE, name)
    except Exception:
        logger.warning("Keychain の読み取りに失敗しました")
        return None


def _save_keychain(name: str, value: str) -> bool:
    if sys.platform != "darwin":
        return False
    try:
        import keyring

        keyring.set_password(KEYCHAIN_SERVICE, name, value)
        return True
    except Exception:
        return False


class TokenResolver:
    """1プロセス内で最新のトークンを保持する。"""

    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        refresh_token: str | None,
        access_token: str | None,
        expires_at: str | None = None,
        write_token: str | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.write_token = write_token
        try:
            self.expires_at = int(expires_at) if expires_at else None
        except ValueError:
            self.expires_at = None

    @classmethod
    def from_environment(cls) -> "TokenResolver":
        def token_value(name: str) -> str | None:
            if not os.environ.get("GITHUB_ACTIONS"):
                stored = _keychain_value(name)
                if stored:
                    return stored
            return os.environ.get(name)

        return cls(
            token_value("OURA_CLIENT_ID"),
            token_value("OURA_CLIENT_SECRET"),
            token_value("OURA_REFRESH_TOKEN"),
            token_value("OURA_ACCESS_TOKEN"),
            token_value("OURA_ACCESS_TOKEN_EXPIRES_AT"),
            os.environ.get("SECRETS_WRITE_TOKEN"),
        )

    @property
    def oauth_ready(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def resolve(self) -> str:
        if self.oauth_ready:
            if self.access_token and self.expires_at and time.time() < self.expires_at - 60:
                return self.access_token
            return self.refresh()
        if self.access_token:
            return self.access_token
        raise ValueError("Oura 認証情報が設定されていません")

    def refresh(self) -> str:
        if not self.oauth_ready:
            raise ValueError("Oura OAuth 認証情報が揃っていません")
        suppress_http_debug_logs()
        try:
            response = requests.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            access_token = payload["access_token"]
            refresh_token = payload["refresh_token"]
            expires_in = int(payload["expires_in"])
            if (
                not isinstance(access_token, str)
                or not access_token
                or not isinstance(refresh_token, str)
                or not refresh_token
                or expires_in <= 0
            ):
                raise ValueError
        except (requests.RequestException, KeyError, TypeError, ValueError):
            raise RuntimeError("Oura OAuth の更新に失敗しました。再認可が必要な可能性があります") from None

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = int(time.time()) + expires_in
        self._persist()
        return access_token

    def _persist(self) -> None:
        values = {
            "OURA_REFRESH_TOKEN": self.refresh_token,
            "OURA_ACCESS_TOKEN": self.access_token,
            "OURA_ACCESS_TOKEN_EXPIRES_AT": str(self.expires_at),
        }
        if os.environ.get("GITHUB_ACTIONS"):
            if not self.write_token:
                logger.warning("SECRETS_WRITE_TOKEN がないため次回 refresh 後は再認可が必要です")
                return
            for name, value in values.items():
                if not save_github_secret(name, value, self.write_token):
                    logger.warning("GitHub Secret %s の更新に失敗しました。次回は再認可が必要な可能性があります", name)
            return
        if sys.platform == "darwin":
            for name, value in values.items():
                if not _save_keychain(name, value):
                    logger.warning("Keychain %s の更新に失敗しました", name)
        else:
            logger.warning("更新した Oura トークンを永続化できませんでした。次回は再認可が必要です")
