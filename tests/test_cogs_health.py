"""cogs/health.py のユニットテスト"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

from cogs.health import HealthCog


def _make_interaction():
    """テスト用 Interaction モックを作成"""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


# ---------------------------------------------------------------------------
# 初期化テスト
# ---------------------------------------------------------------------------


class TestHealthCogInit:
    """HealthCog の初期化テスト"""

    def test_init(self):
        """HealthCog を正しく初期化できる"""
        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        assert cog.bot is bot


# ---------------------------------------------------------------------------
# sleep_command テスト
# ---------------------------------------------------------------------------


class TestSleepCommand:
    """sleep_command のテスト"""

    @patch("cogs.health.create_embed_from_section")
    @patch("cogs.health.format_sleep_section")
    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_sleep_default_date(
        self, mock_today, mock_oura, mock_run_sync, mock_format, mock_embed
    ):
        """日付未指定時はデフォルト日付（昨日）で睡眠データを取得する"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [
            {"score": 82, "day": "2026-02-22"},  # get_sleep
            {"total_sleep_duration": 25200},       # get_sleep_details
        ]
        mock_format.return_value = {"title": "睡眠", "description": "テスト"}
        mock_embed.return_value = MagicMock(spec=discord.Embed)

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.sleep_command.callback(cog, interaction, date_str=None)

        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()

    @patch("cogs.health.create_embed_from_section")
    @patch("cogs.health.format_sleep_section")
    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_sleep_multi_day(
        self, mock_today, mock_oura, mock_run_sync, mock_format, mock_embed
    ):
        """数字入力で複数日取得パスに入る"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura

        # get_sleep_range, get_sleep_details_range の結果
        sleep_map = {
            "2026-02-22": {"score": 80, "day": "2026-02-22"},
            "2026-02-21": {"score": 75, "day": "2026-02-21"},
            "2026-02-20": {"score": 85, "day": "2026-02-20"},
        }
        details_map = {
            "2026-02-22": {"total_sleep_duration": 25200},
            "2026-02-21": {"total_sleep_duration": 24000},
            "2026-02-20": {"total_sleep_duration": 26000},
        }
        mock_run_sync.side_effect = [sleep_map, details_map]
        mock_format.return_value = {"title": "睡眠", "description": "テスト"}
        mock_embed.return_value = MagicMock(spec=discord.Embed)

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.sleep_command.callback(cog, interaction, date_str="3")

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        assert "直近3日間" in call_kwargs.get("content", "")

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_sleep_no_data(self, mock_today, mock_oura, mock_run_sync):
        """睡眠データなしの場合に警告メッセージを返す"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [None, None]  # get_sleep, get_sleep_details

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.sleep_command.callback(cog, interaction, date_str=None)

        interaction.followup.send.assert_called_once()
        assert "睡眠データがありません" in str(interaction.followup.send.call_args)


# ---------------------------------------------------------------------------
# readiness_command テスト
# ---------------------------------------------------------------------------


class TestReadinessCommand:
    """readiness_command のテスト"""

    @patch("cogs.health.create_embed_from_section")
    @patch("cogs.health.format_readiness_section")
    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_readiness_with_hrv(
        self, mock_today, mock_oura, mock_run_sync, mock_format, mock_embed
    ):
        """HRVデータありの場合にHRVフィールドが追加される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [
            {"score": 78, "day": "2026-02-23"},  # get_readiness
            {"average_hrv": 45.3},                 # get_sleep_details
        ]
        mock_format.return_value = {"title": "Readiness", "description": "テスト"}
        embed_mock = MagicMock(spec=discord.Embed)
        mock_embed.return_value = embed_mock

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.readiness_command.callback(cog, interaction, date_str=None)

        # HRVフィールドが追加されている
        embed_mock.add_field.assert_called_once()
        call_kwargs = embed_mock.add_field.call_args[1]
        assert "HRV" in call_kwargs["name"]

    @patch("cogs.health.create_embed_from_section")
    @patch("cogs.health.format_readiness_section")
    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_readiness_without_hrv(
        self, mock_today, mock_oura, mock_run_sync, mock_format, mock_embed
    ):
        """HRVデータなしの場合にHRVフィールドは追加されない"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [
            {"score": 78, "day": "2026-02-23"},  # get_readiness
            None,                                   # get_sleep_details（なし）
        ]
        mock_format.return_value = {"title": "Readiness", "description": "テスト"}
        embed_mock = MagicMock(spec=discord.Embed)
        mock_embed.return_value = embed_mock

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.readiness_command.callback(cog, interaction, date_str=None)

        # HRVフィールドは追加されない
        embed_mock.add_field.assert_not_called()

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_readiness_no_data(self, mock_today, mock_oura, mock_run_sync):
        """Readinessデータなしの場合に警告を返す"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [None]  # get_readiness

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.readiness_command.callback(cog, interaction, date_str=None)

        assert "Readinessデータがありません" in str(interaction.followup.send.call_args)


# ---------------------------------------------------------------------------
# activity_command テスト
# ---------------------------------------------------------------------------


class TestActivityCommand:
    """activity_command のテスト"""

    @patch("cogs.health.get_score_label")
    @patch("cogs.health.get_score_emoji")
    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_activity_basic(
        self, mock_today, mock_oura, mock_run_sync, mock_emoji, mock_label
    ):
        """活動データが正しくEmbedとして送信される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = {
            "score": 85,
            "steps": 9500,
            "active_calories": 350,
            "total_calories": 2200,
        }
        mock_emoji.return_value = ":green_circle:"
        mock_label.return_value = "優秀"

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.activity_command.callback(cog, interaction, date_str=None)

        interaction.followup.send.assert_called_once()
        # Embedオブジェクトが渡されている
        call_kwargs = interaction.followup.send.call_args[1]
        assert "embed" in call_kwargs

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_activity_no_data(self, mock_today, mock_oura, mock_run_sync):
        """活動データなしの場合に警告を返す"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = None

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.activity_command.callback(cog, interaction, date_str=None)

        assert "活動データがありません" in str(interaction.followup.send.call_args)


# ---------------------------------------------------------------------------
# steps_command テスト
# ---------------------------------------------------------------------------


class TestStepsCommand:
    """steps_command のテスト"""

    @patch("cogs.health.settings")
    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_steps_progress_bar(
        self, mock_today, mock_oura, mock_run_sync, mock_settings
    ):
        """歩数進捗バーが正しく計算される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = {"steps": 7000}
        mock_settings.get_steps_goal.return_value = 10000

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.steps_command.callback(cog, interaction)

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        embed = call_kwargs["embed"]
        # Embed の description に進捗率が含まれる
        assert "70%" in embed.description
        assert "7,000" in embed.description

    @patch("cogs.health.settings")
    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_steps_goal_achieved(
        self, mock_today, mock_oura, mock_run_sync, mock_settings
    ):
        """目標達成時に「あと」フィールドが表示されない"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = {"steps": 12000}
        mock_settings.get_steps_goal.return_value = 10000

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.steps_command.callback(cog, interaction)

        call_kwargs = interaction.followup.send.call_args[1]
        embed = call_kwargs["embed"]
        # progress >= 100 なので add_field は呼ばれない
        assert embed.fields == []

    @patch("cogs.health.settings")
    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_steps_zero_goal(
        self, mock_today, mock_oura, mock_run_sync, mock_settings
    ):
        """目標が0の場合に進捗率が0%になる"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = {"steps": 5000}
        mock_settings.get_steps_goal.return_value = 0

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.steps_command.callback(cog, interaction)

        call_kwargs = interaction.followup.send.call_args[1]
        embed = call_kwargs["embed"]
        assert "0%" in embed.description

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_steps_no_data(self, mock_today, mock_oura, mock_run_sync):
        """歩数データなしの場合に警告を返す"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = None

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.steps_command.callback(cog, interaction)

        assert "活動データがまだありません" in str(interaction.followup.send.call_args)


# ---------------------------------------------------------------------------
# temperature_command テスト
# ---------------------------------------------------------------------------


class TestTemperatureCommand:
    """temperature_command のテスト"""

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_temperature_with_deviation(self, mock_today, mock_oura, mock_run_sync):
        """temperature_deviation がある場合に正しく表示される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = {"temperature_deviation": 0.35}

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.temperature_command.callback(cog, interaction, date_str=None)

        call_kwargs = interaction.followup.send.call_args[1]
        embed = call_kwargs["embed"]
        assert "+0.35" in embed.description

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_temperature_fallback_to_average(self, mock_today, mock_oura, mock_run_sync):
        """temperature_deviation がない場合に average_temperature_deviation にフォールバック"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = {"average_temperature_deviation": -0.12}

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.temperature_command.callback(cog, interaction, date_str=None)

        call_kwargs = interaction.followup.send.call_args[1]
        embed = call_kwargs["embed"]
        assert "-0.12" in embed.description

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_temperature_no_deviation(self, mock_today, mock_oura, mock_run_sync):
        """体温偏差データが見つからない場合に警告を返す"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        # 偏差キーがどちらも含まれていない
        mock_run_sync.return_value = {"score": 82}

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.temperature_command.callback(cog, interaction, date_str=None)

        assert "体温偏差データが見つかりません" in str(interaction.followup.send.call_args)

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_temperature_no_sleep_data(self, mock_today, mock_oura, mock_run_sync):
        """睡眠データ自体がない場合に警告を返す"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = None

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.temperature_command.callback(cog, interaction, date_str=None)

        assert "睡眠データがありません" in str(interaction.followup.send.call_args)


# ---------------------------------------------------------------------------
# workout_command テスト
# ---------------------------------------------------------------------------


class TestWorkoutCommand:
    """workout_command のテスト"""

    @patch("cogs.health.format_duration")
    @patch("cogs.health.format_time_from_iso")
    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_workout_basic(
        self, mock_today, mock_oura, mock_run_sync, mock_time_fmt, mock_dur_fmt
    ):
        """ワークアウトデータが正しくEmbedとして送信される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = [
            {
                "label": "ランニング",
                "start_datetime": "2026-02-23T08:00:00+09:00",
                "end_datetime": "2026-02-23T09:00:00+09:00",
                "duration": 3600,
                "calories": 400,
                "average_heart_rate": 140,
            }
        ]
        mock_time_fmt.return_value = "08:00"
        mock_dur_fmt.return_value = "1時間0分"

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.workout_command.callback(cog, interaction, date_str=None)

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        assert "embed" in call_kwargs

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_workout_no_data(self, mock_today, mock_oura, mock_run_sync):
        """ワークアウトデータなしの場合に警告を返す"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = None

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.workout_command.callback(cog, interaction, date_str=None)

        assert "ワークアウトデータがありません" in str(interaction.followup.send.call_args)

    @patch("cogs.health.run_sync")
    @patch("cogs.health.get_oura_client")
    @patch("cogs.health.get_jst_today")
    async def test_workout_exception(self, mock_today, mock_oura, mock_run_sync):
        """ワークアウトコマンドで例外が発生した場合にエラーメッセージを返す"""
        mock_today.return_value = date(2026, 2, 23)
        mock_oura.side_effect = Exception("API接続エラー")

        bot = MagicMock(spec=commands.Bot)
        cog = HealthCog(bot)
        interaction = _make_interaction()

        await cog.workout_command.callback(cog, interaction, date_str=None)

        assert "エラーが発生しました" in str(interaction.followup.send.call_args)
