"""oura_client.py のユニットテスト"""

from datetime import date
from unittest.mock import MagicMock, patch

from oura_client import OuraClient


class TestOuraClientRequest:
    def setup_method(self):
        self.client = OuraClient("test_token")

    @patch("oura_client.requests.get")
    def test_successful_request(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"score": 80}]}
        mock_get.return_value = mock_response

        result = self.client._get("daily_sleep", {"start_date": "2026-02-17"})
        assert result["data"][0]["score"] == 80

    @patch("oura_client.requests.get")
    def test_retry_on_429(self, mock_get):
        # 1回目: 429, 2回目: 成功
        mock_429 = MagicMock()
        mock_429.status_code = 429

        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.json.return_value = {"data": []}

        mock_get.side_effect = [mock_429, mock_ok]

        client = OuraClient("test_token", retry_backoff=0.01)
        result = client._get("daily_sleep", {})
        assert result == {"data": []}
        assert mock_get.call_count == 2

    @patch("oura_client.requests.get")
    def test_retry_on_500(self, mock_get):
        # 1回目: 500, 2回目: 成功
        mock_500 = MagicMock()
        mock_500.status_code = 500

        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.json.return_value = {"data": []}

        mock_get.side_effect = [mock_500, mock_ok]

        client = OuraClient("test_token", retry_backoff=0.01)
        result = client._get("daily_sleep", {})
        assert result == {"data": []}


class TestOuraClientGetRange:
    def setup_method(self):
        self.client = OuraClient("test_token")

    @patch("oura_client.requests.get")
    def test_get_range_returns_data_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"score": 80, "day": "2026-02-15"},
                {"score": 82, "day": "2026-02-16"},
                {"score": 78, "day": "2026-02-17"},
            ]
        }
        mock_get.return_value = mock_response

        result = self.client._get_range(
            "daily_sleep", date(2026, 2, 15), date(2026, 2, 17)
        )
        assert len(result) == 3
        assert result[0]["score"] == 80
        assert result[2]["day"] == "2026-02-17"

    @patch("oura_client.requests.get")
    def test_get_range_empty(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        result = self.client._get_range(
            "daily_sleep", date(2026, 2, 15), date(2026, 2, 17)
        )
        assert result == []


class TestOuraClientGetSleep:
    def setup_method(self):
        self.client = OuraClient("test_token")

    @patch("oura_client.requests.get")
    def test_get_sleep_returns_first(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"score": 82, "day": "2026-02-17"}]
        }
        mock_get.return_value = mock_response

        result = self.client.get_sleep(date(2026, 2, 17))
        assert result is not None
        assert result["score"] == 82

    @patch("oura_client.requests.get")
    def test_get_sleep_no_data(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        result = self.client.get_sleep(date(2026, 2, 17))
        assert result is None


class TestOuraClientBuildPeriodData:
    def setup_method(self):
        self.client = OuraClient("test_token")

    @patch("oura_client.requests.get")
    def test_build_period_data(self, mock_get):
        """_build_period_dataが3回のAPI呼び出しでデータを構築することを確認"""
        # 3つのエンドポイントに対してそれぞれレスポンスを返す
        def side_effect(url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200

            if "daily_sleep" in url:
                mock_resp.json.return_value = {
                    "data": [
                        {"score": 80, "day": "2026-02-16"},
                        {"score": 85, "day": "2026-02-17"},
                    ]
                }
            elif "daily_readiness" in url:
                mock_resp.json.return_value = {
                    "data": [
                        {"score": 75, "day": "2026-02-16"},
                        {"score": 78, "day": "2026-02-17"},
                    ]
                }
            elif "daily_activity" in url:
                mock_resp.json.return_value = {
                    "data": [
                        {"score": 70, "steps": 8000, "day": "2026-02-16"},
                        {"score": 90, "steps": 12000, "day": "2026-02-17"},
                    ]
                }
            else:
                mock_resp.json.return_value = {"data": []}
            return mock_resp

        mock_get.side_effect = side_effect

        result = self.client._build_period_data(date(2026, 2, 16), date(2026, 2, 17))

        # API呼び出しが3回であること（日数分ループではない）
        assert mock_get.call_count == 3

        # daily_dataの構造確認
        assert len(result["daily_data"]) == 2
        assert result["daily_data"][0]["sleep_score"] == 80
        assert result["daily_data"][1]["sleep_score"] == 85

        # スコア配列の確認
        assert result["sleep_scores"] == [80, 85]
        assert result["readiness_scores"] == [75, 78]
        assert result["activity_scores"] == [70, 90]
        assert result["steps_list"] == [8000, 12000]


class TestOuraClientWeeklyData:
    def setup_method(self):
        self.client = OuraClient("test_token")

    @patch("oura_client.requests.get")
    def test_weekly_data_structure(self, mock_get):
        """get_weekly_dataの戻り値構造を確認"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"score": 80, "day": "2026-02-17", "steps": 8000},
            ]
        }
        mock_get.return_value = mock_response

        result = self.client.get_weekly_data(date(2026, 2, 17))

        assert "start_date" in result
        assert "end_date" in result
        assert "daily_data" in result
        assert "averages" in result
        assert "totals" in result

        # averagesのキー確認
        avg = result["averages"]
        assert "sleep" in avg
        assert "readiness" in avg
        assert "activity" in avg
        assert "steps" in avg


class TestOuraClientMonthlyData:
    def setup_method(self):
        self.client = OuraClient("test_token")

    @patch("oura_client.requests.get")
    def test_monthly_data_structure(self, mock_get):
        """get_monthly_dataの戻り値構造を確認"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"score": 80, "day": "2026-02-17", "steps": 8000},
            ]
        }
        mock_get.return_value = mock_response

        result = self.client.get_monthly_data(date(2026, 2, 17), days=7)

        assert "start_date" in result
        assert "end_date" in result
        assert "days" in result
        assert result["days"] == 7
        assert "daily_data" in result
        assert "stats" in result
        assert "totals" in result

        # statsのキー確認
        stats = result["stats"]
        assert "sleep" in stats
        for key in ["avg", "min", "max", "count"]:
            assert key in stats["sleep"]
