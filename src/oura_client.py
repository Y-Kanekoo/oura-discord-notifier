"""Oura Ring API Client"""

import requests
from datetime import date, timedelta
from typing import Optional


class OuraClient:
    """Oura API v2 クライアント"""

    BASE_URL = "https://api.ouraring.com/v2/usercollection"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """APIリクエストを実行"""
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_sleep(self, target_date: Optional[date] = None) -> Optional[dict]:
        """睡眠データを取得（日次サマリー）"""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        params = {
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        }

        data = self._get("daily_sleep", params)
        if data.get("data"):
            return data["data"][0]
        return None

    def get_sleep_details(self, target_date: Optional[date] = None) -> Optional[dict]:
        """睡眠の詳細データを取得（実際の睡眠時間など）"""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        # 睡眠データは翌日にまたがる可能性があるため、前日から当日までの範囲で取得
        params = {
            "start_date": target_date.isoformat(),
            "end_date": (target_date + timedelta(days=1)).isoformat(),
        }

        data = self._get("sleep", params)
        if data.get("data"):
            # 対象日の睡眠データを探す（type="long_sleep"がメインの睡眠）
            for sleep in data["data"]:
                if sleep.get("type") == "long_sleep":
                    return sleep
            # long_sleepがなければ最初のデータを返す
            return data["data"][0]
        return None

    def get_readiness(self, target_date: Optional[date] = None) -> Optional[dict]:
        """Readiness（準備度）データを取得"""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        params = {
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        }

        data = self._get("daily_readiness", params)
        if data.get("data"):
            return data["data"][0]
        return None

    def get_activity(self, target_date: Optional[date] = None) -> Optional[dict]:
        """活動データを取得"""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        params = {
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        }

        data = self._get("daily_activity", params)
        if data.get("data"):
            return data["data"][0]
        return None

    def get_personal_info(self) -> dict:
        """ユーザー情報を取得"""
        url = "https://api.ouraring.com/v2/usercollection/personal_info"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_all_daily_data(self, target_date: Optional[date] = None) -> dict:
        """1日分の全データを取得"""
        return {
            "sleep": self.get_sleep(target_date),
            "sleep_details": self.get_sleep_details(target_date),
            "readiness": self.get_readiness(target_date),
            "activity": self.get_activity(target_date),
            "date": (target_date or date.today() - timedelta(days=1)).isoformat(),
        }
