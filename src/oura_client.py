"""Oura Ring API Client"""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class OuraClient:
    """Oura API v2 クライアント"""

    BASE_URL = "https://api.ouraring.com/v2/usercollection"
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        access_token: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def _request(self, url: str, params: Optional[dict] = None) -> dict:
        """APIリクエストを実行（リトライ付き）"""
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.timeout,
                )
                if response.status_code in self.RETRY_STATUS_CODES and attempt < self.max_retries:
                    time.sleep(self.retry_backoff * attempt)
                    continue
                response.raise_for_status()
                return response.json()
            except requests.RequestException:
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * attempt)
                    continue
                raise

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """APIリクエストを実行"""
        url = f"{self.BASE_URL}/{endpoint}"
        return self._request(url, params)

    def _get_range(self, endpoint: str, start_date: date, end_date: date) -> list[dict]:
        """指定期間のデータを一括取得し、data配列を返す"""
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        data = self._get(endpoint, params)
        return data.get("data", [])

    def get_sleep_range(self, start_date: date, end_date: date) -> dict[str, dict]:
        """指定期間の睡眠サマリーを取得（日付文字列→データの辞書）"""
        items = self._get_range("daily_sleep", start_date, end_date)
        return {item["day"]: item for item in items if "day" in item}

    def get_sleep_details_range(self, start_date: date, end_date: date) -> dict[str, dict]:
        """指定期間の睡眠詳細データを取得（日付文字列→データの辞書）

        日付ごとにlong_sleepを優先して返す。
        """
        # 睡眠は前夜に開始するため、1日前から取得
        params = {
            "start_date": (start_date - timedelta(days=1)).isoformat(),
            "end_date": end_date.isoformat(),
        }
        data = self._get("sleep", params)
        items = data.get("data", [])

        # 日付ごとにlong_sleepを優先してグループ化
        result: dict[str, dict] = {}
        for item in items:
            day = item.get("day")
            if not day:
                continue
            if day not in result or item.get("type") == "long_sleep":
                result[day] = item
        return result

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

        # 睡眠は前夜に開始するため、前日から当日の範囲で検索
        # 例: 12/30の睡眠データ → 12/29夜〜12/30朝 → start=12/29, end=12/30
        params = {
            "start_date": (target_date - timedelta(days=1)).isoformat(),
            "end_date": target_date.isoformat(),
        }

        data = self._get("sleep", params)
        if data.get("data"):
            sleeps = data["data"]

            def extract_sleep_date(entry: dict) -> Optional[date]:
                day_value = entry.get("day")
                if day_value:
                    try:
                        return date.fromisoformat(day_value)
                    except ValueError:
                        pass

                for key in ("bedtime_end", "end_datetime"):
                    iso_value = entry.get(key)
                    if not iso_value:
                        continue
                    try:
                        dt = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
                        return dt.date()
                    except ValueError:
                        continue
                return None

            # 対象日の睡眠データを探す（type="long_sleep"がメインの睡眠）
            long_sleeps = [entry for entry in sleeps if entry.get("type") == "long_sleep"]
            for sleep in long_sleeps:
                if extract_sleep_date(sleep) == target_date:
                    return sleep

            if long_sleeps:
                return long_sleeps[0]

            for sleep in sleeps:
                if extract_sleep_date(sleep) == target_date:
                    return sleep

            return sleeps[0]
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
        return self._request(url)

    def get_all_daily_data(self, target_date: Optional[date] = None) -> dict:
        """1日分の全データを取得"""
        return {
            "sleep": self.get_sleep(target_date),
            "sleep_details": self.get_sleep_details(target_date),
            "readiness": self.get_readiness(target_date),
            "activity": self.get_activity(target_date),
            "date": (target_date or date.today() - timedelta(days=1)).isoformat(),
        }

    def get_heart_rate(self, target_date: Optional[date] = None) -> list[dict]:
        """心拍数データを取得（HRV含む）"""
        if target_date is None:
            target_date = date.today()

        params = {
            "start_datetime": f"{target_date.isoformat()}T00:00:00+09:00",
            "end_datetime": f"{target_date.isoformat()}T23:59:59+09:00",
        }

        data = self._get("heartrate", params)
        return data.get("data", [])

    def get_workout(self, target_date: Optional[date] = None) -> list[dict]:
        """ワークアウトデータを取得"""
        if target_date is None:
            target_date = date.today()

        params = {
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        }

        data = self._get("workout", params)
        return data.get("data", [])

    def get_workouts_range(self, start_date: date, end_date: date) -> list[dict]:
        """期間指定でワークアウトデータを取得"""
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        data = self._get("workout", params)
        return data.get("data", [])

    def _build_period_data(self, start_date: date, end_date: date) -> dict:
        """指定期間のsleep/readiness/activityデータを一括取得して整形する"""
        # 3エンドポイントを各1回ずつ呼び出し（ループ呼び出しの代わり）
        sleep_list = self._get_range("daily_sleep", start_date, end_date)
        readiness_list = self._get_range("daily_readiness", start_date, end_date)
        activity_list = self._get_range("daily_activity", start_date, end_date)

        # dayフィールドでインデックス化
        sleep_by_day = {item["day"]: item for item in sleep_list if "day" in item}
        readiness_by_day = {item["day"]: item for item in readiness_list if "day" in item}
        activity_by_day = {item["day"]: item for item in activity_list if "day" in item}

        # 日別データを構築
        sleep_scores: list[int] = []
        readiness_scores: list[int] = []
        activity_scores: list[int] = []
        steps_list: list[int] = []
        daily_data: list[dict] = []

        current = start_date
        while current <= end_date:
            day_str = current.isoformat()
            sleep = sleep_by_day.get(day_str)
            readiness = readiness_by_day.get(day_str)
            activity = activity_by_day.get(day_str)

            day_data = {
                "date": day_str,
                "sleep_score": sleep.get("score") if sleep else None,
                "readiness_score": readiness.get("score") if readiness else None,
                "activity_score": activity.get("score") if activity else None,
                "steps": activity.get("steps") if activity else None,
            }
            daily_data.append(day_data)

            if sleep and sleep.get("score"):
                sleep_scores.append(sleep["score"])
            if readiness and readiness.get("score"):
                readiness_scores.append(readiness["score"])
            if activity:
                if activity.get("score"):
                    activity_scores.append(activity["score"])
                if activity.get("steps"):
                    steps_list.append(activity["steps"])

            current += timedelta(days=1)

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily_data": daily_data,
            "sleep_scores": sleep_scores,
            "readiness_scores": readiness_scores,
            "activity_scores": activity_scores,
            "steps_list": steps_list,
        }

    def get_weekly_data(self, end_date: Optional[date] = None) -> dict:
        """過去7日間のデータを取得"""
        if end_date is None:
            end_date = date.today()
        start_date = end_date - timedelta(days=6)

        period = self._build_period_data(start_date, end_date)
        sleep_scores = period["sleep_scores"]
        readiness_scores = period["readiness_scores"]
        activity_scores = period["activity_scores"]
        steps_list = period["steps_list"]

        return {
            "start_date": period["start_date"],
            "end_date": period["end_date"],
            "daily_data": period["daily_data"],
            "averages": {
                "sleep": sum(sleep_scores) / len(sleep_scores) if sleep_scores else None,
                "readiness": sum(readiness_scores) / len(readiness_scores) if readiness_scores else None,
                "activity": sum(activity_scores) / len(activity_scores) if activity_scores else None,
                "steps": sum(steps_list) / len(steps_list) if steps_list else None,
            },
            "totals": {
                "steps": sum(steps_list) if steps_list else 0,
            },
        }

    def get_daily_stress(self, target_date: Optional[date] = None) -> Optional[dict]:
        """日次ストレスデータを取得"""
        if target_date is None:
            target_date = date.today()

        params = {
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        }

        try:
            data = self._get("daily_stress", params)
            if data.get("data"):
                return data["data"][0]
        except requests.RequestException:
            logger.warning("ストレスデータの取得に失敗しました", exc_info=True)
        return None

    def get_monthly_data(self, end_date: Optional[date] = None, days: int = 30) -> dict:
        """過去N日間のデータを取得（月間サマリー用）"""
        if end_date is None:
            end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        period = self._build_period_data(start_date, end_date)
        sleep_scores = period["sleep_scores"]
        readiness_scores = period["readiness_scores"]
        activity_scores = period["activity_scores"]
        steps_list = period["steps_list"]

        def calc_stats(scores: list) -> dict:
            if not scores:
                return {"avg": None, "min": None, "max": None, "count": 0}
            return {
                "avg": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores),
                "count": len(scores),
            }

        return {
            "start_date": period["start_date"],
            "end_date": period["end_date"],
            "days": days,
            "daily_data": period["daily_data"],
            "stats": {
                "sleep": calc_stats(sleep_scores),
                "readiness": calc_stats(readiness_scores),
                "activity": calc_stats(activity_scores),
                "steps": calc_stats(steps_list),
            },
            "totals": {
                "steps": sum(steps_list) if steps_list else 0,
            },
        }
