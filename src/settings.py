"""設定管理モジュール - JSON永続化"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# 設定ファイルパス
SETTINGS_FILE = Path(__file__).parent.parent / "data" / "settings.json"

# デフォルト設定
DEFAULT_SETTINGS = {
    "steps_goal": 8000,
    "notification_enabled": True,
    "updated_at": None,
    # リマインダー設定
    "bedtime_reminder_enabled": False,
    "bedtime_reminder_time": "22:30",  # HH:MM 形式
    "bedtime_reminder_channel_id": None,
    # 目標達成通知設定
    "goal_notification_enabled": False,
    "goal_notification_channel_id": None,
    "goal_achieved_today": False,  # 今日達成済みフラグ
    "last_goal_check_date": None,
}


class SettingsManager:
    """設定の読み書きを管理"""

    def __init__(self, file_path: Path = SETTINGS_FILE):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self) -> None:
        """設定ファイルの存在確認・初期化"""
        if not self.file_path.parent.exists():
            self.file_path.parent.mkdir(parents=True)
        if not self.file_path.exists():
            self._save(DEFAULT_SETTINGS.copy())

    def _load(self) -> dict:
        """設定を読み込み"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_SETTINGS.copy()

    def _save(self, data: dict) -> None:
        """設定を保存"""
        data["updated_at"] = datetime.now().isoformat()
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        data = self._load()
        return data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """設定値を保存"""
        data = self._load()
        data[key] = value
        self._save(data)

    def get_steps_goal(self) -> int:
        """歩数目標を取得"""
        return self.get("steps_goal", DEFAULT_SETTINGS["steps_goal"])

    def set_steps_goal(self, value: int) -> None:
        """歩数目標を設定"""
        self.set("steps_goal", value)

    def get_all(self) -> dict:
        """全設定を取得"""
        return self._load()

    def reset(self) -> None:
        """設定をリセット"""
        self._save(DEFAULT_SETTINGS.copy())

    # リマインダー関連
    def get_bedtime_reminder(self) -> dict:
        """就寝リマインダー設定を取得"""
        data = self._load()
        return {
            "enabled": data.get("bedtime_reminder_enabled", False),
            "time": data.get("bedtime_reminder_time", "22:30"),
            "channel_id": data.get("bedtime_reminder_channel_id"),
        }

    def set_bedtime_reminder(self, enabled: bool, time: str = None, channel_id: int = None) -> None:
        """就寝リマインダー設定を保存"""
        data = self._load()
        data["bedtime_reminder_enabled"] = enabled
        if time:
            data["bedtime_reminder_time"] = time
        if channel_id:
            data["bedtime_reminder_channel_id"] = channel_id
        self._save(data)

    # 目標達成通知関連
    def get_goal_notification(self) -> dict:
        """目標達成通知設定を取得"""
        data = self._load()
        return {
            "enabled": data.get("goal_notification_enabled", False),
            "channel_id": data.get("goal_notification_channel_id"),
            "achieved_today": data.get("goal_achieved_today", False),
            "last_check_date": data.get("last_goal_check_date"),
        }

    def set_goal_notification(self, enabled: bool, channel_id: int = None) -> None:
        """目標達成通知設定を保存"""
        data = self._load()
        data["goal_notification_enabled"] = enabled
        if channel_id:
            data["goal_notification_channel_id"] = channel_id
        self._save(data)

    def mark_goal_achieved(self, achieved: bool, check_date: str = None) -> None:
        """目標達成状態を更新"""
        data = self._load()
        data["goal_achieved_today"] = achieved
        if check_date:
            data["last_goal_check_date"] = check_date
        self._save(data)

    def reset_daily_flags(self, current_date: str) -> None:
        """日付が変わったらフラグをリセット"""
        data = self._load()
        if data.get("last_goal_check_date") != current_date:
            data["goal_achieved_today"] = False
            data["last_goal_check_date"] = current_date
            self._save(data)
