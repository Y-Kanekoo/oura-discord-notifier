"""discord_client.py のユニットテスト"""

from unittest.mock import MagicMock, patch

from discord_client import DiscordClient


class TestDiscordClientPost:
    def setup_method(self):
        self.client = DiscordClient("https://discord.com/api/webhooks/test", retry_backoff=0.01)

    @patch("discord_client.requests.post")
    def test_successful_post(self, mock_post):
        """正常なPOSTリクエスト"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        result = self.client._post({"content": "test"})
        assert result is not None
        assert result.status_code == 204

    @patch("discord_client.requests.post")
    def test_retry_on_429_with_retry_after(self, mock_post):
        """429でretry_afterに従ってリトライする"""
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.json.return_value = {"retry_after": 0.01}

        mock_ok = MagicMock()
        mock_ok.status_code = 204

        mock_post.side_effect = [mock_429, mock_ok]

        result = self.client._post({"content": "test"})
        assert result.status_code == 204
        assert mock_post.call_count == 2

    @patch("discord_client.requests.post")
    def test_retry_on_500(self, mock_post):
        """500でリトライする"""
        mock_500 = MagicMock()
        mock_500.status_code = 500

        mock_ok = MagicMock()
        mock_ok.status_code = 204

        mock_post.side_effect = [mock_500, mock_ok]

        result = self.client._post({"content": "test"})
        assert result.status_code == 204
        assert mock_post.call_count == 2

    @patch("discord_client.requests.post")
    def test_no_retry_on_last_attempt_429(self, mock_post):
        """最終試行の429ではリトライしない"""
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.json.return_value = {"retry_after": 0.01}
        mock_429.text = ""

        mock_post.return_value = mock_429

        client = DiscordClient("https://test", max_retries=1, retry_backoff=0.01)
        result = client._post({"content": "test"})
        assert result.status_code == 429
        assert mock_post.call_count == 1

    @patch("discord_client.requests.post")
    def test_request_exception_returns_none(self, mock_post):
        """RequestExceptionで全リトライ失敗時はNoneを返す"""
        import requests
        mock_post.side_effect = requests.RequestException("connection error")

        result = self.client._post({"content": "test"})
        assert result is None


class TestDiscordClientSendMessage:
    def setup_method(self):
        self.client = DiscordClient("https://discord.com/api/webhooks/test", retry_backoff=0.01)

    @patch("discord_client.requests.post")
    def test_send_message_success(self, mock_post):
        """メッセージ送信成功"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        result = self.client.send_message("テストメッセージ")
        assert result is True

        # ペイロードの確認
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["content"] == "テストメッセージ"
        assert payload["username"] == "Oura Ring Bot"

    @patch("discord_client.requests.post")
    def test_send_message_failure(self, mock_post):
        """メッセージ送信失敗"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        result = self.client.send_message("テスト")
        assert result is False

    @patch("discord_client.requests.post")
    def test_send_message_with_avatar(self, mock_post):
        """アバターURL付きメッセージ"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        self.client.send_message("test", avatar_url="https://example.com/avatar.png")
        payload = mock_post.call_args[1]["json"]
        assert payload["avatar_url"] == "https://example.com/avatar.png"


class TestDiscordClientSendEmbed:
    def setup_method(self):
        self.client = DiscordClient("https://discord.com/api/webhooks/test", retry_backoff=0.01)

    @patch("discord_client.requests.post")
    def test_send_embed_success(self, mock_post):
        """Embed送信成功"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        result = self.client.send_embed("タイトル", "説明文", color=0xFF0000)
        assert result is True

        payload = mock_post.call_args[1]["json"]
        assert len(payload["embeds"]) == 1
        assert payload["embeds"][0]["title"] == "タイトル"
        assert payload["embeds"][0]["description"] == "説明文"
        assert payload["embeds"][0]["color"] == 0xFF0000

    @patch("discord_client.requests.post")
    def test_send_embed_with_fields_and_footer(self, mock_post):
        """フィールドとフッター付きEmbed"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        fields = [{"name": "フィールド1", "value": "値1", "inline": True}]
        self.client.send_embed("タイトル", "説明", fields=fields, footer="フッターテキスト")

        payload = mock_post.call_args[1]["json"]
        embed = payload["embeds"][0]
        assert embed["fields"] == fields
        assert embed["footer"]["text"] == "フッターテキスト"


class TestDiscordClientSendHealthReport:
    def setup_method(self):
        self.client = DiscordClient("https://discord.com/api/webhooks/test", retry_backoff=0.01)

    @patch("discord_client.requests.post")
    def test_send_health_report_success(self, mock_post):
        """健康レポート送信成功"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        sections = [
            {"title": "睡眠", "description": "スコア: 82", "color": 0x9B59B6},
            {"title": "活動", "description": "歩数: 9,500", "fields": [
                {"name": "目標", "value": "8,000歩", "inline": True}
            ]},
        ]

        result = self.client.send_health_report("朝レポート", sections)
        assert result is True

        payload = mock_post.call_args[1]["json"]
        assert payload["content"] == "朝レポート"
        assert len(payload["embeds"]) == 2

    @patch("discord_client.requests.post")
    def test_send_health_report_empty_sections(self, mock_post):
        """セクションが空の場合はテキストのみ送信"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        result = self.client.send_health_report("タイトルのみ", [])
        assert result is True

        payload = mock_post.call_args[1]["json"]
        assert payload["content"] == "タイトルのみ"
        assert "embeds" not in payload

    @patch("discord_client.requests.post")
    def test_send_health_report_chunking(self, mock_post):
        """11セクション以上は10件ずつチャンク送信"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        sections = [{"title": f"セクション{i}", "description": ""} for i in range(11)]

        result = self.client.send_health_report("大量セクション", sections)
        assert result is True
        # 2回に分けて送信される（10 + 1）
        assert mock_post.call_count == 2

        # 1回目のペイロード確認
        first_call = mock_post.call_args_list[0]
        first_payload = first_call[1]["json"]
        assert first_payload["content"] == "大量セクション"
        assert len(first_payload["embeds"]) == 10

        # 2回目のペイロード確認
        second_call = mock_post.call_args_list[1]
        second_payload = second_call[1]["json"]
        assert "content" not in second_payload
        assert len(second_payload["embeds"]) == 1

    @patch("discord_client.requests.post")
    def test_send_health_report_failure_stops_chunking(self, mock_post):
        """チャンク送信中にエラーが発生したら中断"""
        mock_ok = MagicMock()
        mock_ok.status_code = 204

        mock_fail = MagicMock()
        mock_fail.status_code = 400

        mock_post.side_effect = [mock_ok, mock_fail]

        sections = [{"title": f"セクション{i}", "description": ""} for i in range(11)]
        result = self.client.send_health_report("テスト", sections)
        assert result is False
