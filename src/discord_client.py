"""Discord Webhook Client"""

import requests
from typing import Optional


class DiscordClient:
    """Discord Webhook クライアント"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

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

        response = requests.post(self.webhook_url, json=payload)
        return response.status_code == 204

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

        response = requests.post(self.webhook_url, json=payload)
        return response.status_code == 204

    def send_health_report(
        self,
        title: str,
        sections: list[dict],
        color: int = 0x00D4AA,
    ) -> bool:
        """健康レポート用の複数Embedを送信"""
        embeds = []

        for section in sections:
            embed = {
                "title": section.get("title", ""),
                "description": section.get("description", ""),
                "color": section.get("color", color),
            }

            if section.get("fields"):
                embed["fields"] = section["fields"]

            embeds.append(embed)

        payload = {
            "username": "Oura Ring Bot",
            "content": title,
            "embeds": embeds,
        }

        response = requests.post(self.webhook_url, json=payload)
        return response.status_code == 204
