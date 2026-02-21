"""settings.py のユニットテスト"""

import json

from settings import DEFAULT_SETTINGS, SettingsManager


class TestSettingsManagerInit:
    def test_creates_file_on_init(self, tmp_path):
        """初期化時に設定ファイルが作成される"""
        file_path = tmp_path / "data" / "settings.json"
        manager = SettingsManager(file_path)

        assert file_path.exists()
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["steps_goal"] == DEFAULT_SETTINGS["steps_goal"]

    def test_preserves_existing_file(self, tmp_path):
        """既存の設定ファイルを上書きしない"""
        file_path = tmp_path / "settings.json"
        existing = {"steps_goal": 12000, "updated_at": "2026-01-01T00:00:00"}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        manager = SettingsManager(file_path)
        assert manager.get("steps_goal") == 12000


class TestSettingsManagerGetSet:
    def setup_method(self, method, tmp_path=None):
        pass

    def _make_manager(self, tmp_path):
        return SettingsManager(tmp_path / "settings.json")

    def test_get_default(self, tmp_path):
        """存在しないキーはデフォルト値を返す"""
        manager = self._make_manager(tmp_path)
        assert manager.get("nonexistent", "fallback") == "fallback"

    def test_set_and_get(self, tmp_path):
        """設定を保存して取得できる"""
        manager = self._make_manager(tmp_path)
        manager.set("steps_goal", 10000)
        assert manager.get("steps_goal") == 10000

    def test_set_updates_updated_at(self, tmp_path):
        """setで updated_at が更新される"""
        manager = self._make_manager(tmp_path)
        manager.set("steps_goal", 5000)
        assert manager.get("updated_at") is not None

    def test_get_all(self, tmp_path):
        """全設定を取得できる"""
        manager = self._make_manager(tmp_path)
        all_settings = manager.get_all()
        assert "steps_goal" in all_settings
        assert "notification_enabled" in all_settings


class TestSettingsManagerStepsGoal:
    def test_get_steps_goal_default(self, tmp_path):
        """デフォルトの歩数目標"""
        manager = SettingsManager(tmp_path / "settings.json")
        assert manager.get_steps_goal() == 8000

    def test_set_steps_goal(self, tmp_path):
        """歩数目標を変更"""
        manager = SettingsManager(tmp_path / "settings.json")
        manager.set_steps_goal(15000)
        assert manager.get_steps_goal() == 15000


class TestSettingsManagerReset:
    def test_reset(self, tmp_path):
        """リセットでデフォルトに戻る"""
        manager = SettingsManager(tmp_path / "settings.json")
        manager.set("steps_goal", 99999)
        manager.reset()
        assert manager.get("steps_goal") == DEFAULT_SETTINGS["steps_goal"]


class TestSettingsManagerBedtimeReminder:
    def test_get_bedtime_reminder_default(self, tmp_path):
        """就寝リマインダーのデフォルト値"""
        manager = SettingsManager(tmp_path / "settings.json")
        reminder = manager.get_bedtime_reminder()
        assert reminder["enabled"] is False
        assert reminder["time"] == "22:30"
        assert reminder["channel_id"] is None

    def test_set_bedtime_reminder(self, tmp_path):
        """就寝リマインダーを設定"""
        manager = SettingsManager(tmp_path / "settings.json")
        manager.set_bedtime_reminder(enabled=True, time="23:00", channel_id=123456)
        reminder = manager.get_bedtime_reminder()
        assert reminder["enabled"] is True
        assert reminder["time"] == "23:00"
        assert reminder["channel_id"] == 123456


class TestSettingsManagerGoalNotification:
    def test_get_goal_notification_default(self, tmp_path):
        """目標達成通知のデフォルト値"""
        manager = SettingsManager(tmp_path / "settings.json")
        notif = manager.get_goal_notification()
        assert notif["enabled"] is False
        assert notif["achieved_today"] is False

    def test_set_goal_notification(self, tmp_path):
        """目標達成通知を設定"""
        manager = SettingsManager(tmp_path / "settings.json")
        manager.set_goal_notification(enabled=True, channel_id=789)
        notif = manager.get_goal_notification()
        assert notif["enabled"] is True
        assert notif["channel_id"] == 789

    def test_mark_goal_achieved(self, tmp_path):
        """目標達成マーク"""
        manager = SettingsManager(tmp_path / "settings.json")
        manager.mark_goal_achieved(True, "2026-02-20")
        notif = manager.get_goal_notification()
        assert notif["achieved_today"] is True
        assert notif["last_check_date"] == "2026-02-20"


class TestSettingsManagerDailyFlags:
    def test_reset_daily_flags_on_new_date(self, tmp_path):
        """日付が変わるとフラグがリセットされる"""
        manager = SettingsManager(tmp_path / "settings.json")
        manager.mark_goal_achieved(True, "2026-02-19")
        manager.reset_daily_flags("2026-02-20")

        notif = manager.get_goal_notification()
        assert notif["achieved_today"] is False
        assert notif["last_check_date"] == "2026-02-20"

    def test_no_reset_on_same_date(self, tmp_path):
        """同じ日付ではフラグがリセットされない"""
        manager = SettingsManager(tmp_path / "settings.json")
        manager.mark_goal_achieved(True, "2026-02-20")
        manager.reset_daily_flags("2026-02-20")

        notif = manager.get_goal_notification()
        assert notif["achieved_today"] is True


class TestSettingsManagerCorruptFile:
    def test_corrupt_json_returns_defaults(self, tmp_path):
        """破損したJSONファイルはデフォルト値を返す"""
        file_path = tmp_path / "settings.json"
        file_path.write_text("{{invalid json")

        manager = SettingsManager(file_path)
        assert manager.get("steps_goal") == DEFAULT_SETTINGS["steps_goal"]
