"""ヘルプ・自然言語対応"""

import re

import discord
from discord.ext import commands

from advice import generate_advice
from bot_utils import (
    create_embed_from_section,
    get_jst_today,
    get_oura_client,
    settings,
)
from formatter import (
    format_morning_report,
    format_night_report,
    format_noon_report,
    format_readiness_section,
    format_sleep_section,
    get_score_emoji,
)

# パターン定義
PATTERNS = [
    # 睡眠関連
    (r"(睡眠|スリープ|ねむ|眠り|寝).*(スコア|点|どう|は[？?])", "sleep"),
    (r"(昨日|きのう|前日).*(睡眠|寝)", "sleep"),
    (r"よく(眠|寝)れた", "sleep"),

    # Readiness関連
    (r"(レディネス|readiness|準備|準備度|コンディション)", "readiness"),
    (r"(調子|体調).*(どう|は[？?])", "readiness"),

    # 歩数・活動関連
    (r"(歩数|ほすう|あるい|歩い).*(何歩|どれくらい|どう|は[？?])", "steps"),
    (r"(今日|きょう)の?(歩数|あるい)", "steps"),
    (r"(活動|アクティビティ)", "activity"),

    # レポート要求
    (r"(朝|モーニング).*(レポート|報告|通知|送)", "report_morning"),
    (r"(昼|ランチ|noon).*(レポート|報告|通知|送)", "report_noon"),
    (r"(夜|ナイト|night).*(レポート|報告|通知|送)", "report_night"),
    (r"レポート.*(送|見せ|教え)", "report_morning"),

    # 設定変更
    (r"(歩数|ステップ).*目標.*(\d+)", "set_goal"),
    (r"目標.*(\d+).*(歩|ステップ)", "set_goal"),

    # アドバイス
    (r"(今日|きょう).*(どう|アドバイス|何).*(すれば|したら|いい)", "advice"),
    (r"(おすすめ|オススメ|推奨|アドバイス)", "advice"),
    (r"どうすればいい", "advice"),

    # ヘルプ
    (r"(ヘルプ|help|使い方|できること)", "help"),
]


class GeneralCog(commands.Cog):
    """ヘルプ・自然言語対応"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="help", description="使い方を表示します")
    async def help_command(self, interaction: discord.Interaction):
        """ヘルプを表示"""
        embed = discord.Embed(
            title=":book: Oura Bot ヘルプ",
            description="Oura Ring のデータを Discord で確認できます。",
            color=0x5865F2,
        )

        embed.add_field(
            name=":zzz: データ照会",
            value=(
                "`/sleep` - 睡眠スコア（複数日も可: `/sleep 3`）\n"
                "`/readiness` - Readiness（HRV付き）\n"
                "`/activity` - 活動データ\n"
                "`/steps` - 今日の歩数\n"
                "`/temperature` - 体温偏差\n"
                "`/workout` - ワークアウト履歴"
            ),
            inline=True,
        )

        embed.add_field(
            name=":chart_with_upwards_trend: レポート",
            value=(
                "`/report morning` - 朝レポート\n"
                "`/report noon` - 昼レポート\n"
                "`/report night` - 夜レポート\n"
                "`/week` - 週間サマリー＆先週比\n"
                "`/month` - 月間サマリー\n"
                "`/graph` - グラフ表示"
            ),
            inline=True,
        )

        embed.add_field(
            name=":gear: 設定・その他",
            value=(
                "`/goal <歩数>` - 目標変更\n"
                "`/settings` - 設定確認\n"
                "`/bedtime_reminder` - 就寝リマインダー設定\n"
                "`/goal_notification` - 目標達成通知設定\n"
                "`/advice` - アドバイス"
            ),
            inline=True,
        )

        embed.add_field(
            name=":speech_balloon: 自然言語",
            value=(
                "ボットにメンションして話しかけることもできます。\n"
                "例: `@OuraBot 睡眠スコアは？`"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """メッセージ受信時"""
        # ボット自身のメッセージは無視
        if message.author.bot:
            return

        # ボットがメンションされた場合のみ反応
        if self.bot.user and self.bot.user.mentioned_in(message):
            # メンション部分を除去
            content = message.content
            for mention in message.mentions:
                content = content.replace(f"<@{mention.id}>", "")
                content = content.replace(f"<@!{mention.id}>", "")
            content = content.strip()

            if content:
                await self._handle_natural_language(message, content)
            else:
                await message.reply(
                    ":wave: こんにちは！Oura Bot です。\n"
                    "「睡眠スコアは？」のように話しかけてください。\n"
                    "`/help` でコマンド一覧を確認できます。"
                )

    async def _handle_natural_language(self, message: discord.Message, content: str):
        """自然言語メッセージを処理"""
        content_lower = content.lower()

        for pattern, handler_type in PATTERNS:
            match = re.search(pattern, content_lower)
            if match:
                await self._dispatch_handler(message, handler_type, content, match)
                return

        # マッチしない場合
        await message.reply(
            ":thinking: すみません、理解できませんでした。\n"
            "`/help` でコマンド一覧を確認できます。\n\n"
            "例: 「睡眠スコアは？」「今日の歩数」「アドバイスちょうだい」"
        )

    async def _dispatch_handler(self, message: discord.Message, handler_type: str, content: str, match):
        """ハンドラータイプに応じて処理を振り分け"""
        try:
            oura = get_oura_client()

            if handler_type == "sleep":
                sleep_data = oura.get_sleep(get_jst_today())
                sleep_details = oura.get_sleep_details(get_jst_today())
                if not sleep_data:
                    await message.reply(":warning: 睡眠データがありません")
                    return
                section = format_sleep_section(sleep_data, sleep_details)
                embed = create_embed_from_section(section)
                await message.reply(embed=embed)

            elif handler_type == "readiness":
                readiness_data = oura.get_readiness(get_jst_today())
                if not readiness_data:
                    await message.reply(":warning: Readinessデータがありません")
                    return
                section = format_readiness_section(readiness_data)
                embed = create_embed_from_section(section)
                await message.reply(embed=embed)

            elif handler_type == "steps":
                activity = oura.get_activity(get_jst_today())
                if not activity:
                    await message.reply(":warning: 今日の活動データがまだありません")
                    return
                steps = activity.get("steps", 0)
                goal = settings.get_steps_goal()
                progress = (steps / goal * 100) if goal > 0 else 0
                await message.reply(
                    f":footprints: 今日の歩数: **{steps:,}** / {goal:,} 歩 ({progress:.0f}%)"
                )

            elif handler_type == "activity":
                activity = oura.get_activity(get_jst_today())
                if not activity:
                    await message.reply(":warning: 今日の活動データがまだありません")
                    return
                score = activity.get("score", 0)
                steps = activity.get("steps", 0)
                await message.reply(
                    f":running: 活動スコア: **{score}** {get_score_emoji(score)}\n"
                    f":footprints: 歩数: {steps:,} 歩"
                )

            elif handler_type == "report_morning":
                data = oura.get_all_daily_data(get_jst_today())
                title, sections = format_morning_report(data)
                embeds = [create_embed_from_section(s) for s in sections]
                await message.reply(content=title, embeds=embeds)

            elif handler_type == "report_noon":
                activity = oura.get_activity(get_jst_today())
                sleep = oura.get_sleep(get_jst_today())
                sleep_details = oura.get_sleep_details(get_jst_today())
                goal = settings.get_steps_goal()
                title, sections, should_send = format_noon_report(
                    activity, goal, sleep_data=sleep, sleep_details=sleep_details
                )
                if not should_send:
                    await message.reply(":white_check_mark: 順調です！")
                    return
                embeds = [create_embed_from_section(s) for s in sections]
                await message.reply(content=title, embeds=embeds)

            elif handler_type == "report_night":
                readiness = oura.get_readiness(get_jst_today())
                sleep = oura.get_sleep(get_jst_today())
                activity = oura.get_activity(get_jst_today())
                title, sections = format_night_report(readiness, sleep, activity)
                embeds = [create_embed_from_section(s) for s in sections]
                await message.reply(content=title, embeds=embeds)

            elif handler_type == "set_goal":
                # 数字を抽出
                numbers = re.findall(r"\d+", content)
                if numbers:
                    new_goal = int(numbers[-1])
                    if 1000 <= new_goal <= 100000:
                        old_goal = settings.get_steps_goal()
                        settings.set_steps_goal(new_goal)
                        await message.reply(
                            f":white_check_mark: 歩数目標を変更しました！\n"
                            f"**{old_goal:,}** → **{new_goal:,}** 歩"
                        )
                    else:
                        await message.reply(":x: 1,000〜100,000の範囲で指定してください")
                else:
                    await message.reply(":x: 目標歩数を数字で指定してください")

            elif handler_type == "advice":
                readiness = oura.get_readiness(get_jst_today())
                sleep = oura.get_sleep(get_jst_today())
                activity = oura.get_activity(get_jst_today())

                advice_text = generate_advice(
                    readiness_score=readiness.get("score") if readiness else None,
                    sleep_score=sleep.get("score") if sleep else None,
                    activity_score=activity.get("score") if activity else None,
                    steps=activity.get("steps") if activity else None,
                    steps_goal=settings.get_steps_goal(),
                )

                embed = discord.Embed(
                    title=":bulb: 今日のアドバイス",
                    description=advice_text,
                    color=0x00D4AA,
                )
                await message.reply(embed=embed)

            elif handler_type == "help":
                await message.reply(
                    ":book: **使い方**\n\n"
                    "**データ照会**\n"
                    "• 睡眠スコアは？\n"
                    "• 今日の歩数\n"
                    "• コンディションどう？\n\n"
                    "**レポート**\n"
                    "• 朝レポート送って\n"
                    "• 夜レポート見せて\n\n"
                    "**設定**\n"
                    "• 目標を10000歩にして\n\n"
                    "**アドバイス**\n"
                    "• 今日どうすればいい？\n\n"
                    "スラッシュコマンドも使えます: `/help`"
                )

        except Exception as e:
            await message.reply(f":x: エラーが発生しました: {str(e)}")


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCog(bot))
