"""cogs/scheduler.py のユニットテスト"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from discord.ext import commands

from cogs.scheduler import SchedulerCog

# ---------------------------------------------------------------------------
# 初期化テスト
# ---------------------------------------------------------------------------


class TestSchedulerCogInit:
    """SchedulerCog の初期化テスト"""

    def test_init(self):
        """SchedulerCog を正しく初期化できる"""
        bot = MagicMock(spec=commands.Bot)
        cog = SchedulerCog(bot)
        assert cog.bot is bot


# ---------------------------------------------------------------------------
# scheduler_loop テスト
# ---------------------------------------------------------------------------


class TestSchedulerLoop:
    """scheduler_loop のロジックテスト"""

    def _make_bot_with_channel(self):
        """テスト用botとチャンネルモックを作成"""
        bot = MagicMock(spec=commands.Bot)
        channel = AsyncMock()
        channel.send = AsyncMock()
        bot.get_channel = MagicMock(return_value=channel)
        return bot, channel

    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_daily_flags_reset(self, mock_now, mock_settings):
        """日付変更時にフラグがリセットされる"""
        from zoneinfo import ZoneInfo

        mock_now.return_value = datetime(2026, 2, 23, 0, 1, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_settings.get_bedtime_reminder.return_value = {"enabled": False}
        mock_settings.get_goal_notification.return_value = {"enabled": False}

        bot = MagicMock(spec=commands.Bot)
        cog = SchedulerCog(bot)

        # scheduler_loop のコールバックを直接呼び出す
        await cog.scheduler_loop.coro(cog)

        mock_settings.reset_daily_flags.assert_called_once_with("2026-02-23")

    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_bedtime_reminder_sent(self, mock_now, mock_settings):
        """就寝リマインダーが時刻一致で送信される"""
        from zoneinfo import ZoneInfo

        # 22:30 にリマインダーが設定されていて、現在時刻が 22:30
        mock_now.return_value = datetime(2026, 2, 23, 22, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_settings.get_bedtime_reminder.return_value = {
            "enabled": True,
            "time": "22:30",
            "channel_id": 999,
        }
        mock_settings.get_goal_notification.return_value = {"enabled": False}

        bot, channel = self._make_bot_with_channel()
        cog = SchedulerCog(bot)

        await cog.scheduler_loop.coro(cog)

        bot.get_channel.assert_called_with(999)
        channel.send.assert_called_once()
        assert "就寝時間" in channel.send.call_args[0][0]

    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_bedtime_reminder_not_sent_wrong_time(self, mock_now, mock_settings):
        """就寝リマインダーは時刻が一致しなければ送信されない"""
        from zoneinfo import ZoneInfo

        mock_now.return_value = datetime(2026, 2, 23, 21, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_settings.get_bedtime_reminder.return_value = {
            "enabled": True,
            "time": "22:30",
            "channel_id": 999,
        }
        mock_settings.get_goal_notification.return_value = {"enabled": False}

        bot, channel = self._make_bot_with_channel()
        cog = SchedulerCog(bot)

        await cog.scheduler_loop.coro(cog)

        channel.send.assert_not_called()

    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_bedtime_reminder_disabled(self, mock_now, mock_settings):
        """就寝リマインダーが無効の場合は送信しない"""
        from zoneinfo import ZoneInfo

        mock_now.return_value = datetime(2026, 2, 23, 22, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_settings.get_bedtime_reminder.return_value = {
            "enabled": False,
            "time": "22:30",
            "channel_id": 999,
        }
        mock_settings.get_goal_notification.return_value = {"enabled": False}

        bot, channel = self._make_bot_with_channel()
        cog = SchedulerCog(bot)

        await cog.scheduler_loop.coro(cog)

        channel.send.assert_not_called()

    @patch("cogs.scheduler.get_jst_today")
    @patch("cogs.scheduler.run_sync")
    @patch("cogs.scheduler.get_oura_client")
    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_goal_notification_sent(
        self, mock_now, mock_settings, mock_oura, mock_run_sync, mock_today
    ):
        """歩数が目標に達した場合に通知が送信される"""
        from datetime import date
        from zoneinfo import ZoneInfo

        mock_now.return_value = datetime(2026, 2, 23, 15, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_today.return_value = date(2026, 2, 23)
        mock_settings.get_bedtime_reminder.return_value = {"enabled": False}
        mock_settings.get_goal_notification.return_value = {
            "enabled": True,
            "achieved_today": False,
            "channel_id": 888,
        }
        mock_settings.get_steps_goal.return_value = 10000

        oura_mock = MagicMock()
        mock_oura.return_value = oura_mock
        # 歩数が目標以上
        mock_run_sync.return_value = {"steps": 12000}

        bot, channel = self._make_bot_with_channel()
        cog = SchedulerCog(bot)

        await cog.scheduler_loop.coro(cog)

        channel.send.assert_called_once()
        assert "達成" in channel.send.call_args[0][0]
        mock_settings.mark_goal_achieved.assert_called_once_with(True, "2026-02-23")

    @patch("cogs.scheduler.get_jst_today")
    @patch("cogs.scheduler.run_sync")
    @patch("cogs.scheduler.get_oura_client")
    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_goal_notification_not_sent_below_goal(
        self, mock_now, mock_settings, mock_oura, mock_run_sync, mock_today
    ):
        """歩数が目標未満の場合は通知しない"""
        from datetime import date
        from zoneinfo import ZoneInfo

        mock_now.return_value = datetime(2026, 2, 23, 15, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_today.return_value = date(2026, 2, 23)
        mock_settings.get_bedtime_reminder.return_value = {"enabled": False}
        mock_settings.get_goal_notification.return_value = {
            "enabled": True,
            "achieved_today": False,
            "channel_id": 888,
        }
        mock_settings.get_steps_goal.return_value = 10000

        oura_mock = MagicMock()
        mock_oura.return_value = oura_mock
        # 歩数が目標未満
        mock_run_sync.return_value = {"steps": 5000}

        bot, channel = self._make_bot_with_channel()
        cog = SchedulerCog(bot)

        await cog.scheduler_loop.coro(cog)

        channel.send.assert_not_called()
        mock_settings.mark_goal_achieved.assert_not_called()

    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_goal_notification_already_achieved(self, mock_now, mock_settings):
        """既に目標達成済みの場合は通知しない"""
        from zoneinfo import ZoneInfo

        mock_now.return_value = datetime(2026, 2, 23, 15, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_settings.get_bedtime_reminder.return_value = {"enabled": False}
        mock_settings.get_goal_notification.return_value = {
            "enabled": True,
            "achieved_today": True,  # 既に達成済み
            "channel_id": 888,
        }

        bot, channel = self._make_bot_with_channel()
        cog = SchedulerCog(bot)

        await cog.scheduler_loop.coro(cog)

        channel.send.assert_not_called()

    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_goal_notification_disabled(self, mock_now, mock_settings):
        """目標達成通知が無効の場合は通知しない"""
        from zoneinfo import ZoneInfo

        mock_now.return_value = datetime(2026, 2, 23, 15, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_settings.get_bedtime_reminder.return_value = {"enabled": False}
        mock_settings.get_goal_notification.return_value = {
            "enabled": False,
            "achieved_today": False,
        }

        bot, channel = self._make_bot_with_channel()
        cog = SchedulerCog(bot)

        await cog.scheduler_loop.coro(cog)

        channel.send.assert_not_called()

    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_bedtime_reminder_invalid_time_uses_default(self, mock_now, mock_settings):
        """就寝リマインダーの時刻が不正な場合はデフォルト22:30を使用"""
        from zoneinfo import ZoneInfo

        # 22:30がデフォルトなので、22:30にすればリマインダーが送信される
        mock_now.return_value = datetime(2026, 2, 23, 22, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_settings.get_bedtime_reminder.return_value = {
            "enabled": True,
            "time": "invalid",  # 不正な時刻
            "channel_id": 999,
        }
        mock_settings.get_goal_notification.return_value = {"enabled": False}

        bot, channel = self._make_bot_with_channel()
        cog = SchedulerCog(bot)

        await cog.scheduler_loop.coro(cog)

        # 不正時刻→デフォルト22:30が使われ、現在22:30なので送信される
        channel.send.assert_called_once()

    @patch("cogs.scheduler.settings")
    @patch("cogs.scheduler.get_jst_now")
    async def test_bedtime_reminder_no_channel_id(self, mock_now, mock_settings):
        """channel_idが未設定の場合はリマインダーを送信しない"""
        from zoneinfo import ZoneInfo

        mock_now.return_value = datetime(2026, 2, 23, 22, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
        mock_settings.get_bedtime_reminder.return_value = {
            "enabled": True,
            "time": "22:30",
            "channel_id": None,
        }
        mock_settings.get_goal_notification.return_value = {"enabled": False}

        bot, channel = self._make_bot_with_channel()
        cog = SchedulerCog(bot)

        await cog.scheduler_loop.coro(cog)

        channel.send.assert_not_called()
