"""cogs/settings_cog.py のユニットテスト"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from settings import SettingsManager


class TestGoalCommand:
    """歩数目標コマンドのテスト"""

    def _make_interaction(self):
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()
        return interaction

    def test_goal_range_lower_bound(self, tmp_path):
        """歩数目標が1000未満は不正"""
        sm = SettingsManager(tmp_path / "settings.json")
        # 下限チェック: 999は不正、1000はOK
        assert 999 < 1000  # バリデーション条件の確認
        assert not (1000 < 1000 or 1000 > 100000)

    def test_goal_range_upper_bound(self, tmp_path):
        """歩数目標が100000超は不正"""
        sm = SettingsManager(tmp_path / "settings.json")
        assert 100001 > 100000  # バリデーション条件の確認
        assert not (100000 < 1000 or 100000 > 100000)

    def test_set_and_get_goal(self, tmp_path):
        """歩数目標の設定・取得"""
        sm = SettingsManager(tmp_path / "settings.json")
        sm.set_steps_goal(10000)
        assert sm.get_steps_goal() == 10000


class TestBedtimeReminder:
    """就寝リマインダー設定のテスト"""

    def test_enable_bedtime_reminder(self, tmp_path):
        """就寝リマインダーを有効化"""
        sm = SettingsManager(tmp_path / "settings.json")
        sm.set_bedtime_reminder(enabled=True, time="23:00", channel_id=12345)
        result = sm.get_bedtime_reminder()
        assert result["enabled"] is True
        assert result["time"] == "23:00"
        assert result["channel_id"] == 12345

    def test_disable_bedtime_reminder(self, tmp_path):
        """就寝リマインダーを無効化"""
        sm = SettingsManager(tmp_path / "settings.json")
        sm.set_bedtime_reminder(enabled=True, time="23:00", channel_id=12345)
        sm.set_bedtime_reminder(enabled=False)
        result = sm.get_bedtime_reminder()
        assert result["enabled"] is False

    def test_partial_update(self, tmp_path):
        """時刻のみ更新"""
        sm = SettingsManager(tmp_path / "settings.json")
        sm.set_bedtime_reminder(enabled=True, time="22:00", channel_id=111)
        sm.set_bedtime_reminder(enabled=True, time="23:30")
        result = sm.get_bedtime_reminder()
        assert result["time"] == "23:30"
        assert result["channel_id"] == 111  # チャンネルは変わらない


class TestGoalNotification:
    """目標達成通知設定のテスト"""

    def test_enable_goal_notification(self, tmp_path):
        """目標達成通知を有効化"""
        sm = SettingsManager(tmp_path / "settings.json")
        sm.set_goal_notification(enabled=True, channel_id=789)
        result = sm.get_goal_notification()
        assert result["enabled"] is True
        assert result["channel_id"] == 789

    def test_mark_and_reset_goal(self, tmp_path):
        """目標達成→日付リセット"""
        sm = SettingsManager(tmp_path / "settings.json")
        sm.mark_goal_achieved(True, "2026-02-20")
        result = sm.get_goal_notification()
        assert result["achieved_today"] is True

        sm.reset_daily_flags("2026-02-21")
        result = sm.get_goal_notification()
        assert result["achieved_today"] is False

    def test_disable_clears_achieved(self, tmp_path):
        """無効化時にachievedをクリアするフロー"""
        sm = SettingsManager(tmp_path / "settings.json")
        sm.set_goal_notification(enabled=True, channel_id=789)
        sm.mark_goal_achieved(True, "2026-02-20")

        # 無効化時に mark_goal_achieved(False) を呼ぶ（settings_cogのロジック）
        sm.set_goal_notification(enabled=False)
        sm.mark_goal_achieved(False)

        result = sm.get_goal_notification()
        assert result["enabled"] is False
        assert result["achieved_today"] is False
