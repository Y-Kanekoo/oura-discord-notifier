"""cogs/general.py のユニットテスト"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

from cogs.general import PATTERNS, GeneralCog


def _match_pattern(text):
    """テキストにマッチするパターンのhandler_typeを返す"""
    for pattern, handler_type in PATTERNS:
        if re.search(pattern, text.lower()):
            return handler_type
    return None


# ---------------------------------------------------------------------------
# PATTERNS 正規表現テスト
# ---------------------------------------------------------------------------


class TestPatternsMatching:
    """PATTERNSの正規表現マッチテスト"""

    # --- 睡眠関連 ---

    def test_sleep_score_question(self):
        """「睡眠スコアは？」が sleep にマッチする"""
        assert _match_pattern("睡眠スコアは？") == "sleep"

    def test_sleep_yesterday(self):
        """「昨日の睡眠」が sleep にマッチする"""
        assert _match_pattern("昨日の睡眠") == "sleep"

    def test_sleep_well(self):
        """「よく眠れた」が sleep にマッチする"""
        assert _match_pattern("よく眠れた") == "sleep"

    def test_sleep_slept_well(self):
        """「よく寝れた」が sleep にマッチする"""
        assert _match_pattern("よく寝れた") == "sleep"

    # --- Readiness関連 ---

    def test_readiness_katakana(self):
        """「レディネスは？」が readiness にマッチする"""
        assert _match_pattern("レディネスは？") == "readiness"

    def test_readiness_condition(self):
        """「調子はどう？」が readiness にマッチする"""
        assert _match_pattern("調子はどう？") == "readiness"

    def test_readiness_health(self):
        """「体調どう？」が readiness にマッチする"""
        assert _match_pattern("体調どう？") == "readiness"

    # --- 歩数関連 ---

    def test_steps_how_many(self):
        """「歩数はどれくらい？」が steps にマッチする"""
        assert _match_pattern("歩数はどれくらい？") == "steps"

    def test_steps_today(self):
        """「今日の歩数」が steps にマッチする"""
        assert _match_pattern("今日の歩数") == "steps"

    # --- 活動関連 ---

    def test_activity_score(self):
        """「活動スコア」が activity にマッチする"""
        assert _match_pattern("活動スコア") == "activity"

    # --- レポート関連 ---

    def test_report_morning(self):
        """「朝レポート送って」が report_morning にマッチする"""
        assert _match_pattern("朝レポート送って") == "report_morning"

    def test_report_noon(self):
        """「昼レポート見せて」が report_noon にマッチする"""
        assert _match_pattern("昼レポート見せて") == "report_noon"

    def test_report_night(self):
        """「夜レポート送って」が report_night にマッチする"""
        assert _match_pattern("夜レポート送って") == "report_night"

    # --- 設定変更 ---

    def test_set_goal(self):
        """「目標を10000歩にして」が set_goal にマッチする"""
        assert _match_pattern("目標を10000歩にして") == "set_goal"

    def test_set_goal_steps_prefix(self):
        """「歩数目標を8000にして」が set_goal にマッチする"""
        assert _match_pattern("歩数目標を8000にして") == "set_goal"

    # --- アドバイス ---

    def test_advice_today(self):
        """「今日どうすればいい？」が advice にマッチする"""
        assert _match_pattern("今日どうすればいい？") == "advice"

    def test_advice_recommend(self):
        """「おすすめ」が advice にマッチする"""
        assert _match_pattern("おすすめ") == "advice"

    # --- ヘルプ ---

    def test_help_katakana(self):
        """「ヘルプ」が help にマッチする"""
        assert _match_pattern("ヘルプ") == "help"

    def test_help_usage(self):
        """「使い方」が help にマッチする"""
        assert _match_pattern("使い方") == "help"

    # --- マッチしないケース ---

    def test_no_match_greeting(self):
        """「こんにちは」はどのパターンにもマッチしない"""
        assert _match_pattern("こんにちは") is None

    def test_no_match_empty(self):
        """空文字列はどのパターンにもマッチしない"""
        assert _match_pattern("") is None


# ---------------------------------------------------------------------------
# GeneralCog 初期化テスト
# ---------------------------------------------------------------------------


class TestGeneralCogInit:
    """GeneralCog の初期化テスト"""

    def test_init(self):
        """GeneralCog を正しく初期化できる"""
        bot = MagicMock(spec=commands.Bot)
        cog = GeneralCog(bot)
        assert cog.bot is bot


# ---------------------------------------------------------------------------
# on_message のロジックテスト
# ---------------------------------------------------------------------------


class TestOnMessage:
    """on_message リスナーのロジックテスト"""

    def _make_bot(self):
        """テスト用のbotモックを作成"""
        bot = MagicMock(spec=commands.Bot)
        bot.user = MagicMock()
        bot.user.id = 12345
        bot.user.mentioned_in = MagicMock(return_value=True)
        return bot

    def _make_message(self, content, *, is_bot=False, mention_id=12345):
        """テスト用のMessageモックを作成"""
        message = AsyncMock(spec=discord.Message)
        message.author = MagicMock()
        message.author.bot = is_bot
        message.content = content
        mention = MagicMock()
        mention.id = mention_id
        message.mentions = [mention]
        message.reply = AsyncMock()
        return message

    async def test_ignore_bot_message(self):
        """ボット自身のメッセージは無視する"""
        bot = self._make_bot()
        cog = GeneralCog(bot)
        message = self._make_message("テスト", is_bot=True)

        await cog.on_message(message)
        message.reply.assert_not_called()

    async def test_empty_mention_replies_greeting(self):
        """メンションのみ（内容なし）の場合は挨拶を返す"""
        bot = self._make_bot()
        cog = GeneralCog(bot)
        message = self._make_message(f"<@{bot.user.id}>", mention_id=bot.user.id)

        await cog.on_message(message)
        message.reply.assert_called_once()
        call_args = message.reply.call_args
        assert "こんにちは" in call_args[0][0]

    async def test_no_mention_ignored(self):
        """ボットがメンションされていない場合は無視"""
        bot = self._make_bot()
        bot.user.mentioned_in = MagicMock(return_value=False)
        cog = GeneralCog(bot)
        message = self._make_message("睡眠スコアは？")

        await cog.on_message(message)
        message.reply.assert_not_called()

    async def test_unrecognized_message_replies_fallback(self):
        """認識できないメッセージにはフォールバック返答する"""
        bot = self._make_bot()
        cog = GeneralCog(bot)
        message = self._make_message(
            f"<@{bot.user.id}> こんにちは", mention_id=bot.user.id
        )

        await cog.on_message(message)
        message.reply.assert_called_once()
        call_args = message.reply.call_args
        assert "理解できませんでした" in call_args[0][0]


# ---------------------------------------------------------------------------
# _dispatch_handler テスト（一部ハンドラーの振る舞い）
# ---------------------------------------------------------------------------


class TestDispatchHandler:
    """_dispatch_handler のモック統合テスト"""

    def _make_message(self):
        """テスト用メッセージモック"""
        message = AsyncMock(spec=discord.Message)
        message.reply = AsyncMock()
        return message

    @patch("cogs.general.get_oura_client")
    @patch("cogs.general.run_sync")
    @patch("cogs.general.get_jst_today")
    async def test_sleep_handler_no_data(self, mock_today, mock_run_sync, mock_oura):
        """sleep ハンドラー: データなしの場合に警告メッセージを返す"""
        from datetime import date

        mock_today.return_value = date(2026, 2, 23)
        mock_run_sync.return_value = None
        mock_oura.return_value = MagicMock()

        bot = MagicMock(spec=commands.Bot)
        cog = GeneralCog(bot)
        message = self._make_message()

        await cog._dispatch_handler(message, "sleep", "睡眠スコアは？", None)
        message.reply.assert_called_once()
        assert "睡眠データがありません" in str(message.reply.call_args)

    @patch("cogs.general.settings")
    @patch("cogs.general.get_oura_client")
    @patch("cogs.general.run_sync")
    @patch("cogs.general.get_jst_today")
    async def test_steps_handler_with_data(
        self, mock_today, mock_run_sync, mock_oura, mock_settings
    ):
        """steps ハンドラー: 歩数データありの場合に正しいメッセージを返す"""
        from datetime import date

        mock_today.return_value = date(2026, 2, 23)
        mock_run_sync.return_value = {"steps": 5000}
        mock_oura.return_value = MagicMock()
        mock_settings.get_steps_goal.return_value = 10000

        bot = MagicMock(spec=commands.Bot)
        cog = GeneralCog(bot)
        message = self._make_message()

        await cog._dispatch_handler(message, "steps", "今日の歩数", None)
        message.reply.assert_called_once()
        reply_text = message.reply.call_args[0][0]
        assert "5,000" in reply_text
        assert "10,000" in reply_text

    @patch("cogs.general.get_oura_client")
    async def test_help_handler(self, mock_oura):
        """help ハンドラー: ヘルプメッセージを返す"""
        mock_oura.return_value = MagicMock()

        bot = MagicMock(spec=commands.Bot)
        cog = GeneralCog(bot)
        message = self._make_message()

        await cog._dispatch_handler(message, "help", "ヘルプ", None)
        message.reply.assert_called_once()
        reply_text = message.reply.call_args[0][0]
        assert "使い方" in reply_text

    @patch("cogs.general.settings")
    @patch("cogs.general.get_oura_client")
    async def test_set_goal_handler_valid(self, mock_oura, mock_settings):
        """set_goal ハンドラー: 有効な目標値で設定が更新される"""
        mock_settings.get_steps_goal.return_value = 8000
        mock_oura.return_value = MagicMock()

        bot = MagicMock(spec=commands.Bot)
        cog = GeneralCog(bot)
        message = self._make_message()

        await cog._dispatch_handler(
            message, "set_goal", "目標を10000歩にして", None
        )
        mock_settings.set_steps_goal.assert_called_once_with(10000)
        message.reply.assert_called_once()
        reply_text = message.reply.call_args[0][0]
        assert "10,000" in reply_text

    @patch("cogs.general.get_oura_client")
    async def test_set_goal_handler_out_of_range(self, mock_oura):
        """set_goal ハンドラー: 範囲外の目標値はエラーメッセージを返す"""
        mock_oura.return_value = MagicMock()

        bot = MagicMock(spec=commands.Bot)
        cog = GeneralCog(bot)
        message = self._make_message()

        await cog._dispatch_handler(
            message, "set_goal", "目標を500歩にして", None
        )
        message.reply.assert_called_once()
        assert "1,000〜100,000" in str(message.reply.call_args)

    @patch("cogs.general.get_oura_client")
    async def test_dispatch_handler_exception(self, mock_oura):
        """ハンドラー内で例外が発生した場合にエラーメッセージを返す"""
        mock_oura.side_effect = Exception("テストエラー")

        bot = MagicMock(spec=commands.Bot)
        cog = GeneralCog(bot)
        message = self._make_message()

        await cog._dispatch_handler(message, "sleep", "睡眠スコアは？", None)
        message.reply.assert_called_once()
        assert "エラーが発生しました" in str(message.reply.call_args)
