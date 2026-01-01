"""設定管理モジュール - JSON永続化"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any


# 設定ファイルパス
SETTINGS_FILE = Path(__file__).parent.parent / "data" / "settings.json"

# デフォルト設定
DEFAULT_SETTINGS = {
    "steps_goal": 8000,
    "notification_enabled": True,
    "updated_at": None,
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
