"""Discord Webhook Client"""

import os
import time
from typing import Optional

import requests


class DiscordClient:
    """Discord Webhook クライアント"""

    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        webhook_url: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ):
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def _post(self, payload: dict) -> Optional[requests.Response]:
        """WebhookへのPOSTを実行（リトライ付き）"""
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=self.timeout,
                )
                should_retry = False
                if response.status_code == 429 and attempt < self.max_retries:
                    retry_after = None
                    try:
                        data = response.json()
                        raw = data.get("retry_after") if isinstance(data, dict) else None
                        if isinstance(raw, (int, float)):
                            retry_after = float(raw)
                    except (ValueError, KeyError):
                        retry_after = None
                    time.sleep(retry_after if retry_after else self.retry_backoff * attempt)
                    should_retry = True
                elif response.status_code in self.RETRY_STATUS_CODES and attempt < self.max_retries:
                    time.sleep(self.retry_backoff * attempt)
                    should_retry = True

                if should_retry:
                    continue

                if response.status_code != 204 and os.environ.get("DISCORD_WEBHOOK_DEBUG"):
                    body = response.text.strip()
                    if len(body) > 500:
                        body = body[:500] + "..."
                    print(f"Discord webhook status={response.status_code} body={body}")
                return response
            except requests.RequestException:
                if attempt == self.max_retries and os.environ.get("DISCORD_WEBHOOK_DEBUG"):
                    print("Discord webhook request failed with RequestException")
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * attempt)
                    continue
                return None
        return None

    def send_message(
        self,
        content: str,
        username: Optional[str] = "Oura Ring Bot",
        avatar_url: Optional[str] = None,
    ) -> bool:
        """テキストメッセージを送信"""
        payload = {
            "content": content,
            "username": username,
        }

        if avatar_url:
            payload["avatar_url"] = avatar_url

        response = self._post(payload)
        return response is not None and response.status_code == 204

    def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x7289DA,
        fields: Optional[list] = None,
        username: Optional[str] = "Oura Ring Bot",
        footer: Optional[str] = None,
    ) -> bool:
        """Embed形式のメッセージを送信"""
        embed = {
            "title": title,
            "description": description,
            "color": color,
        }

        if fields:
            embed["fields"] = fields

        if footer:
            embed["footer"] = {"text": footer}

        payload = {
            "username": username,
            "embeds": [embed],
        }

        response = self._post(payload)
        return response is not None and response.status_code == 204

    def send_health_report(
        self,
        title: str,
        sections: list[dict],
        color: int = 0x00D4AA,
    ) -> bool:
        """健康レポート用の複数Embedを送信"""
        if not sections:
            payload = {
                "username": "Oura Ring Bot",
                "content": title,
            }
            response = self._post(payload)
            return response is not None and response.status_code == 204

        def build_embed(section: dict) -> dict:
            embed = {
                "title": section.get("title", ""),
                "description": section.get("description", ""),
                "color": section.get("color", color),
            }

            if section.get("fields"):
                embed["fields"] = section["fields"]

            return embed

        success = True
        for index in range(0, len(sections), 10):
            chunk = sections[index:index + 10]
            embeds = [build_embed(section) for section in chunk]
            payload = {
                "username": "Oura Ring Bot",
                "embeds": embeds,
            }
            if index == 0:
                payload["content"] = title

            response = self._post(payload)
            if response is None or response.status_code != 204:
                success = False
                break

        return success
