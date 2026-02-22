"""cogs/report.py のユニットテスト"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

from cogs.report import ReportCog


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


class TestReportCogInit:
    """ReportCog の初期化テスト"""

    def test_init(self):
        """ReportCog を正しく初期化できる"""
        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        assert cog.bot is bot


# ---------------------------------------------------------------------------
# report_command テスト
# ---------------------------------------------------------------------------


class TestReportCommand:
    """report_command のテスト"""

    @patch("cogs.report.create_embed_from_section")
    @patch("cogs.report.format_morning_report")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_report_morning(
        self, mock_today, mock_oura, mock_run_sync, mock_format, mock_embed
    ):
        """朝レポートが正しく送信される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.return_value = {"sleep": {}, "readiness": {}}
        mock_format.return_value = (
            "朝レポート",
            [{"title": "睡眠", "description": "テスト", "color": 0x00D4AA}],
        )
        mock_embed.return_value = MagicMock(spec=discord.Embed)

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.report_command.callback(cog, interaction, report_type="morning")

        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        assert call_kwargs["content"] == "朝レポート"

    @patch("cogs.report.create_embed_from_section")
    @patch("cogs.report.format_noon_report")
    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_report_noon_with_sections(
        self, mock_today, mock_oura, mock_run_sync, mock_settings, mock_format, mock_embed
    ):
        """昼レポートでshouldSend=Trueの場合にセクションが送信される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [
            {"steps": 3000},  # get_activity
            {"score": 80},     # get_sleep
            {},                 # get_sleep_details
        ]
        mock_settings.get_steps_goal.return_value = 10000
        mock_format.return_value = (
            "昼レポート",
            [{"title": "進捗", "description": "テスト", "color": 0xFFFF00}],
            True,  # should_send
        )
        mock_embed.return_value = MagicMock(spec=discord.Embed)

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.report_command.callback(cog, interaction, report_type="noon")

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        assert call_kwargs["content"] == "昼レポート"

    @patch("cogs.report.format_noon_report")
    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_report_noon_no_send(
        self, mock_today, mock_oura, mock_run_sync, mock_settings, mock_format
    ):
        """昼レポートでshouldSend=Falseの場合は「順調」メッセージを返す"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [
            {"steps": 8000},  # get_activity
            {"score": 90},     # get_sleep
            {},                 # get_sleep_details
        ]
        mock_settings.get_steps_goal.return_value = 10000
        mock_format.return_value = ("昼レポート", [], False)

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.report_command.callback(cog, interaction, report_type="noon")

        interaction.followup.send.assert_called_once()
        assert "順調" in str(interaction.followup.send.call_args)

    @patch("cogs.report.create_embed_from_section")
    @patch("cogs.report.format_night_report")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_report_night(
        self, mock_today, mock_oura, mock_run_sync, mock_format, mock_embed
    ):
        """夜レポートが正しく送信される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [
            {"score": 78},   # get_readiness
            {"score": 80},   # get_sleep
            {"steps": 9000}, # get_activity
        ]
        mock_format.return_value = (
            "夜レポート",
            [{"title": "今日の結果", "description": "テスト", "color": 0x00D4AA}],
        )
        mock_embed.return_value = MagicMock(spec=discord.Embed)

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.report_command.callback(cog, interaction, report_type="night")

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        assert call_kwargs["content"] == "夜レポート"

    @patch("cogs.report.get_oura_client")
    async def test_report_unknown_type(self, mock_oura):
        """不明なレポートタイプの場合にエラーメッセージを返す"""
        mock_oura.return_value = MagicMock()

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.report_command.callback(cog, interaction, report_type="unknown")

        interaction.followup.send.assert_called_once()
        assert "不明なレポートタイプ" in str(interaction.followup.send.call_args)


# ---------------------------------------------------------------------------
# advice_command テスト
# ---------------------------------------------------------------------------


class TestAdviceCommand:
    """advice_command のテスト"""

    @patch("cogs.report.generate_advice")
    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_advice_basic(
        self, mock_today, mock_oura, mock_run_sync, mock_settings, mock_advice
    ):
        """アドバイスコマンドが正しくEmbedを送信する"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [
            {"score": 78},                   # get_readiness
            {"score": 82},                   # get_sleep
            {"score": 85, "steps": 9000},    # get_activity
        ]
        mock_settings.get_steps_goal.return_value = 10000
        mock_advice.return_value = "今日は軽い運動がおすすめです。"

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.advice_command.callback(cog, interaction)

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        embed = call_kwargs["embed"]
        assert "アドバイス" in embed.title
        assert "軽い運動" in embed.description

    @patch("cogs.report.generate_advice")
    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_advice_no_data(
        self, mock_today, mock_oura, mock_run_sync, mock_settings, mock_advice
    ):
        """データなしでもアドバイスが生成される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_run_sync.side_effect = [None, None, None]  # すべてデータなし
        mock_settings.get_steps_goal.return_value = 10000
        mock_advice.return_value = "データが不足しています。"

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.advice_command.callback(cog, interaction)

        # generate_advice が None を受け取って呼ばれる
        mock_advice.assert_called_once_with(
            readiness_score=None,
            sleep_score=None,
            activity_score=None,
            steps=None,
            steps_goal=10000,
        )
        interaction.followup.send.assert_called_once()


# ---------------------------------------------------------------------------
# week_command テスト
# ---------------------------------------------------------------------------


class TestWeekCommand:
    """week_command のテスト"""

    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_week_basic(self, mock_today, mock_oura, mock_run_sync):
        """週間サマリーが正しく送信される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura

        weekly_data = {
            "start_date": "2026-02-17",
            "end_date": "2026-02-23",
            "daily_data": [
                {
                    "date": "2026-02-17",
                    "sleep_score": 80,
                    "readiness_score": 75,
                    "activity_score": 82,
                    "steps": 8500,
                }
            ],
            "averages": {
                "sleep": 80.0,
                "readiness": 75.0,
                "activity": 82.0,
                "steps": 8500.0,
            },
            "totals": {"steps": 59500},
        }
        prev_weekly_data = {
            "start_date": "2026-02-10",
            "end_date": "2026-02-16",
            "daily_data": [],
            "averages": {
                "sleep": 78.0,
                "readiness": 72.0,
                "activity": 80.0,
                "steps": 8000.0,
            },
            "totals": {"steps": 56000},
        }

        mock_run_sync.side_effect = [weekly_data, prev_weekly_data]

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.week_command.callback(cog, interaction, date_str=None)

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        embed = call_kwargs["embed"]
        assert "週間サマリー" in embed.title


# ---------------------------------------------------------------------------
# month_command テスト
# ---------------------------------------------------------------------------


class TestMonthCommand:
    """month_command のテスト"""

    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_month_basic(self, mock_today, mock_oura, mock_run_sync, mock_settings):
        """月間サマリーが正しく送信される"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_settings.get_steps_goal.return_value = 10000

        monthly_data = {
            "start_date": "2026-01-25",
            "end_date": "2026-02-23",
            "daily_data": [
                {"date": "2026-02-20", "steps": 12000},
                {"date": "2026-02-21", "steps": 8000},
            ],
            "stats": {
                "sleep": {"avg": 80.5, "max": 90, "min": 65, "count": 28},
                "readiness": {"avg": 75.0, "max": 85, "min": 60, "count": 28},
                "activity": {"avg": 82.0, "max": 95, "min": 70, "count": 28},
                "steps": {"avg": 9500.0, "max": 15000, "min": 3000, "count": 28},
            },
            "totals": {"steps": 266000},
        }
        mock_run_sync.return_value = monthly_data

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.month_command.callback(cog, interaction, days=30)

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        embed = call_kwargs["embed"]
        assert "30日間サマリー" in embed.title

    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_month_days_clamped_min(
        self, mock_today, mock_oura, mock_run_sync, mock_settings
    ):
        """days が最小値（7）にクランプされる"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_settings.get_steps_goal.return_value = 10000

        monthly_data = {
            "start_date": "2026-02-16",
            "end_date": "2026-02-23",
            "daily_data": [],
            "stats": {},
            "totals": {},
        }
        mock_run_sync.return_value = monthly_data

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        # days=3 は最小7にクランプされる
        await cog.month_command.callback(cog, interaction, days=3)

        # run_sync が呼ばれた（クランプ後の値で実行）
        interaction.followup.send.assert_called_once()

    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_month_days_clamped_max(
        self, mock_today, mock_oura, mock_run_sync, mock_settings
    ):
        """days が最大値（90）にクランプされる"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_settings.get_steps_goal.return_value = 10000

        monthly_data = {
            "start_date": "2025-11-25",
            "end_date": "2026-02-23",
            "daily_data": [],
            "stats": {},
            "totals": {},
        }
        mock_run_sync.return_value = monthly_data

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        # days=200 は最大90にクランプされる
        await cog.month_command.callback(cog, interaction, days=200)

        interaction.followup.send.assert_called_once()


# ---------------------------------------------------------------------------
# graph_command テスト
# ---------------------------------------------------------------------------


class TestGraphCommand:
    """graph_command のテスト"""

    @patch("cogs.report.generate_combined_chart")
    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_graph_combined(
        self, mock_today, mock_oura, mock_run_sync, mock_settings, mock_chart
    ):
        """combined グラフタイプが正しく生成される"""
        import io

        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_settings.get_steps_goal.return_value = 10000

        monthly_data = {
            "start_date": "2026-02-09",
            "end_date": "2026-02-23",
            "daily_data": [{"date": "2026-02-20", "steps": 10000}],
            "stats": {},
            "totals": {},
        }
        mock_run_sync.return_value = monthly_data
        mock_chart.return_value = io.BytesIO(b"fake_image_data")

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.graph_command.callback(
            cog, interaction, graph_type="combined", days=14
        )

        mock_chart.assert_called_once()
        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args[1]
        assert "file" in call_kwargs

    @patch("cogs.report.generate_score_chart")
    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_graph_scores(
        self, mock_today, mock_oura, mock_run_sync, mock_settings, mock_chart
    ):
        """scores グラフタイプが正しく生成される"""
        import io

        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_settings.get_steps_goal.return_value = 10000

        monthly_data = {
            "start_date": "2026-02-09",
            "end_date": "2026-02-23",
            "daily_data": [{"date": "2026-02-20", "sleep_score": 80}],
            "stats": {},
            "totals": {},
        }
        mock_run_sync.return_value = monthly_data
        mock_chart.return_value = io.BytesIO(b"fake_image_data")

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.graph_command.callback(
            cog, interaction, graph_type="scores", days=14
        )

        mock_chart.assert_called_once()
        interaction.followup.send.assert_called_once()

    @patch("cogs.report.generate_steps_chart")
    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_graph_steps(
        self, mock_today, mock_oura, mock_run_sync, mock_settings, mock_chart
    ):
        """steps グラフタイプが正しく生成される"""
        import io

        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_settings.get_steps_goal.return_value = 10000

        monthly_data = {
            "start_date": "2026-02-09",
            "end_date": "2026-02-23",
            "daily_data": [{"date": "2026-02-20", "steps": 9000}],
            "stats": {},
            "totals": {},
        }
        mock_run_sync.return_value = monthly_data
        mock_chart.return_value = io.BytesIO(b"fake_image_data")

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.graph_command.callback(
            cog, interaction, graph_type="steps", days=14
        )

        mock_chart.assert_called_once()
        interaction.followup.send.assert_called_once()

    @patch("cogs.report.settings")
    @patch("cogs.report.run_sync")
    @patch("cogs.report.get_oura_client")
    @patch("cogs.report.get_jst_today")
    async def test_graph_no_data(
        self, mock_today, mock_oura, mock_run_sync, mock_settings
    ):
        """データなしの場合に警告メッセージを返す"""
        mock_today.return_value = date(2026, 2, 23)
        oura = MagicMock()
        mock_oura.return_value = oura
        mock_settings.get_steps_goal.return_value = 10000

        monthly_data = {
            "start_date": "2026-02-09",
            "end_date": "2026-02-23",
            "daily_data": [],  # データなし
            "stats": {},
            "totals": {},
        }
        mock_run_sync.return_value = monthly_data

        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        await cog.graph_command.callback(
            cog, interaction, graph_type="combined", days=14
        )

        assert "データがありません" in str(interaction.followup.send.call_args)

    async def test_graph_exception(self):
        """graph_command で例外が発生した場合にエラーメッセージを返す"""
        bot = MagicMock(spec=commands.Bot)
        cog = ReportCog(bot)
        interaction = _make_interaction()

        with patch("cogs.report.get_oura_client", side_effect=Exception("テストエラー")):
            await cog.graph_command.callback(
                cog, interaction, graph_type="combined", days=14
            )

        assert "エラーが発生しました" in str(interaction.followup.send.call_args)
