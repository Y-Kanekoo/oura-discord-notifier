"""Discord Bot - 会話型インターフェース"""

import os
import re
import sys
import discord
from discord import app_commands
from discord.ext import commands
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

# .envファイルの読み込み
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# 既存モジュールを再利用
from oura_client import OuraClient
from formatter import (
    format_sleep_section,
    format_readiness_section,
    format_morning_report,
    format_noon_report,
    format_night_report,
    get_score_emoji,
    get_score_label,
    format_duration,
)
from settings import SettingsManager
from advice import generate_advice


# ボット設定
intents = discord.Intents.default()
intents.message_content = True  # 自然言語対応に必要

bot = commands.Bot(command_prefix="!", intents=intents)
settings = SettingsManager()

# OuraClient インスタンス（遅延初期化）
_oura_client: Optional[OuraClient] = None


def get_oura_client() -> OuraClient:
    """OuraClient のシングルトン取得"""
    global _oura_client
    if _oura_client is None:
        token = os.environ.get("OURA_ACCESS_TOKEN")
        if not token:
            raise ValueError("OURA_ACCESS_TOKEN が設定されていません")
        _oura_client = OuraClient(token)
    return _oura_client


def create_embed_from_section(section: dict) -> discord.Embed:
    """フォーマッターのセクションからEmbedを作成"""
    embed = discord.Embed(
        title=section.get("title", ""),
        description=section.get("description", ""),
        color=section.get("color", 0x00D4AA),
    )

    for field in section.get("fields", []):
        embed.add_field(
            name=field.get("name", ""),
            value=field.get("value", ""),
            inline=field.get("inline", True),
        )

    return embed


# =============================================================================
# スラッシュコマンド
# =============================================================================

@bot.tree.command(name="sleep", description="睡眠スコアを表示します")
@app_commands.describe(date_str="日付（YYYY-MM-DD形式、省略時は昨日）")
async def sleep_command(interaction: discord.Interaction, date_str: Optional[str] = None):
    """睡眠データを表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        # 日付パース
        if date_str:
            target_date = date.fromisoformat(date_str)
        else:
            target_date = date.today() - timedelta(days=1)

        sleep_data = oura.get_sleep(target_date)
        sleep_details = oura.get_sleep_details(target_date)

        if not sleep_data:
            await interaction.followup.send(f":warning: {target_date} の睡眠データがありません")
            return

        section = format_sleep_section(sleep_data, sleep_details)
        embed = create_embed_from_section(section)

        await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(f":x: 日付形式が不正です: {str(e)}")
    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="readiness", description="Readiness（準備度）スコアを表示します")
@app_commands.describe(date_str="日付（YYYY-MM-DD形式、省略時は今日）")
async def readiness_command(interaction: discord.Interaction, date_str: Optional[str] = None):
    """Readinessデータを表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        if date_str:
            target_date = date.fromisoformat(date_str)
        else:
            target_date = date.today()

        readiness_data = oura.get_readiness(target_date)

        if not readiness_data:
            await interaction.followup.send(f":warning: {target_date} のReadinessデータがありません")
            return

        section = format_readiness_section(readiness_data)
        embed = create_embed_from_section(section)

        await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(f":x: 日付形式が不正です: {str(e)}")
    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="activity", description="活動データを表示します")
@app_commands.describe(date_str="日付（YYYY-MM-DD形式、省略時は今日）")
async def activity_command(interaction: discord.Interaction, date_str: Optional[str] = None):
    """活動データを表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        if date_str:
            target_date = date.fromisoformat(date_str)
        else:
            target_date = date.today()

        activity_data = oura.get_activity(target_date)

        if not activity_data:
            await interaction.followup.send(f":warning: {target_date} の活動データがありません")
            return

        score = activity_data.get("score", 0)
        steps = activity_data.get("steps", 0)
        active_calories = activity_data.get("active_calories", 0)
        total_calories = activity_data.get("total_calories", 0)

        embed = discord.Embed(
            title=":running: 活動データ",
            description=f"**スコア: {score}** {get_score_emoji(score)} ({get_score_label(score)})",
            color=0x00FF00 if score >= 85 else (0xFFFF00 if score >= 70 else 0xFF0000),
        )

        embed.add_field(name=":footprints: 歩数", value=f"{steps:,} 歩", inline=True)
        embed.add_field(name=":fire: アクティブCal", value=f"{active_calories:,} kcal", inline=True)
        embed.add_field(name=":zap: 総カロリー", value=f"{total_calories:,} kcal", inline=True)

        await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(f":x: 日付形式が不正です: {str(e)}")
    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="steps", description="今日の歩数を表示します")
async def steps_command(interaction: discord.Interaction):
    """歩数を表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()
        activity_data = oura.get_activity(date.today())

        if not activity_data:
            await interaction.followup.send(":warning: 今日の活動データがまだありません")
            return

        steps = activity_data.get("steps", 0)
        goal = settings.get_steps_goal()
        progress = (steps / goal * 100) if goal > 0 else 0

        # 進捗バー
        bar_length = 10
        filled = int(progress / 10)
        bar = "█" * min(filled, bar_length) + "░" * max(0, bar_length - filled)

        embed = discord.Embed(
            title=":footprints: 今日の歩数",
            description=f"**{steps:,} / {goal:,} 歩** ({progress:.0f}%)\n`{bar}`",
            color=0x00FF00 if progress >= 100 else (0xFFFF00 if progress >= 70 else 0xFF9900),
        )

        if progress < 100:
            remaining = goal - steps
            embed.add_field(name=":dart: あと", value=f"{remaining:,} 歩", inline=True)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="report", description="レポートを送信します")
@app_commands.describe(report_type="レポートの種類")
@app_commands.choices(report_type=[
    app_commands.Choice(name="朝レポート（睡眠+Readiness）", value="morning"),
    app_commands.Choice(name="昼レポート（活動進捗）", value="noon"),
    app_commands.Choice(name="夜レポート（今日の結果）", value="night"),
])
async def report_command(interaction: discord.Interaction, report_type: str = "morning"):
    """レポートを送信"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        if report_type == "morning":
            data = oura.get_all_daily_data()
            title, sections = format_morning_report(data)

        elif report_type == "noon":
            activity = oura.get_activity(date.today())
            sleep = oura.get_sleep()
            sleep_details = oura.get_sleep_details()
            goal = settings.get_steps_goal()

            title, sections, should_send = format_noon_report(
                activity, goal, sleep_data=sleep, sleep_details=sleep_details
            )
            if not should_send:
                await interaction.followup.send(":white_check_mark: 順調です！特に通知はありません。")
                return

        elif report_type == "night":
            readiness = oura.get_readiness(date.today())
            sleep = oura.get_sleep()
            activity = oura.get_activity(date.today())
            title, sections = format_night_report(readiness, sleep, activity)

        else:
            await interaction.followup.send(":x: 不明なレポートタイプです")
            return

        # 各セクションをEmbedとして送信
        embeds = [create_embed_from_section(section) for section in sections]
        await interaction.followup.send(content=title, embeds=embeds)

    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="goal", description="歩数目標を変更します")
@app_commands.describe(value="新しい歩数目標")
async def goal_command(interaction: discord.Interaction, value: int):
    """歩数目標を変更"""
    if value < 1000 or value > 100000:
        await interaction.response.send_message(
            ":x: 歩数目標は 1,000 〜 100,000 の範囲で設定してください"
        )
        return

    old_goal = settings.get_steps_goal()
    settings.set_steps_goal(value)

    await interaction.response.send_message(
        f":white_check_mark: 歩数目標を変更しました\n"
        f"**{old_goal:,}** → **{value:,}** 歩"
    )


@bot.tree.command(name="settings", description="現在の設定を表示します")
async def settings_command(interaction: discord.Interaction):
    """設定を表示"""
    all_settings = settings.get_all()

    embed = discord.Embed(
        title=":gear: 現在の設定",
        color=0x5865F2,
    )

    embed.add_field(
        name=":footprints: 歩数目標",
        value=f"{all_settings.get('steps_goal', 8000):,} 歩",
        inline=True,
    )

    updated_at = all_settings.get("updated_at")
    if updated_at:
        embed.set_footer(text=f"最終更新: {updated_at}")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="advice", description="今日のアドバイスを取得します")
async def advice_command(interaction: discord.Interaction):
    """アドバイスを表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        # 今日のデータを取得
        readiness = oura.get_readiness(date.today())
        sleep = oura.get_sleep()
        activity = oura.get_activity(date.today())

        readiness_score = readiness.get("score") if readiness else None
        sleep_score = sleep.get("score") if sleep else None
        activity_score = activity.get("score") if activity else None
        steps = activity.get("steps") if activity else None
        goal = settings.get_steps_goal()

        advice_text = generate_advice(
            readiness_score=readiness_score,
            sleep_score=sleep_score,
            activity_score=activity_score,
            steps=steps,
            steps_goal=goal,
        )

        embed = discord.Embed(
            title=":bulb: 今日のアドバイス",
            description=advice_text,
            color=0x00D4AA,
        )

        # データサマリー
        if readiness_score or sleep_score or steps:
            summary = []
            if readiness_score:
                summary.append(f"Readiness: {readiness_score}")
            if sleep_score:
                summary.append(f"睡眠: {sleep_score}")
            if steps:
                summary.append(f"歩数: {steps:,}")
            embed.set_footer(text=" | ".join(summary))

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="help", description="使い方を表示します")
async def help_command(interaction: discord.Interaction):
    """ヘルプを表示"""
    embed = discord.Embed(
        title=":book: Oura Bot ヘルプ",
        description="Oura Ring のデータを Discord で確認できます。",
        color=0x5865F2,
    )

    embed.add_field(
        name=":zzz: データ照会",
        value=(
            "`/sleep` - 睡眠スコア\n"
            "`/readiness` - Readiness\n"
            "`/activity` - 活動データ\n"
            "`/steps` - 今日の歩数"
        ),
        inline=True,
    )

    embed.add_field(
        name=":chart_with_upwards_trend: レポート",
        value=(
            "`/report morning` - 朝レポート\n"
            "`/report noon` - 昼レポート\n"
            "`/report night` - 夜レポート"
        ),
        inline=True,
    )

    embed.add_field(
        name=":gear: 設定・その他",
        value=(
            "`/goal <歩数>` - 目標変更\n"
            "`/settings` - 設定確認\n"
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


# =============================================================================
# 自然言語対応
# =============================================================================

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


async def handle_natural_language(message: discord.Message, content: str):
    """自然言語メッセージを処理"""
    content_lower = content.lower()

    for pattern, handler_type in PATTERNS:
        match = re.search(pattern, content_lower)
        if match:
            await dispatch_handler(message, handler_type, content, match)
            return

    # マッチしない場合
    await message.reply(
        ":thinking: すみません、理解できませんでした。\n"
        "`/help` でコマンド一覧を確認できます。\n\n"
        "例: 「睡眠スコアは？」「今日の歩数」「アドバイスちょうだい」"
    )


async def dispatch_handler(message: discord.Message, handler_type: str, content: str, match):
    """ハンドラータイプに応じて処理を振り分け"""
    try:
        oura = get_oura_client()

        if handler_type == "sleep":
            sleep_data = oura.get_sleep()
            sleep_details = oura.get_sleep_details()
            if not sleep_data:
                await message.reply(":warning: 睡眠データがありません")
                return
            section = format_sleep_section(sleep_data, sleep_details)
            embed = create_embed_from_section(section)
            await message.reply(embed=embed)

        elif handler_type == "readiness":
            readiness_data = oura.get_readiness(date.today())
            if not readiness_data:
                await message.reply(":warning: Readinessデータがありません")
                return
            section = format_readiness_section(readiness_data)
            embed = create_embed_from_section(section)
            await message.reply(embed=embed)

        elif handler_type == "steps":
            activity = oura.get_activity(date.today())
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
            activity = oura.get_activity(date.today())
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
            data = oura.get_all_daily_data()
            title, sections = format_morning_report(data)
            embeds = [create_embed_from_section(s) for s in sections]
            await message.reply(content=title, embeds=embeds)

        elif handler_type == "report_noon":
            activity = oura.get_activity(date.today())
            sleep = oura.get_sleep()
            sleep_details = oura.get_sleep_details()
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
            readiness = oura.get_readiness(date.today())
            sleep = oura.get_sleep()
            activity = oura.get_activity(date.today())
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
            readiness = oura.get_readiness(date.today())
            sleep = oura.get_sleep()
            activity = oura.get_activity(date.today())

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


# =============================================================================
# イベントハンドラ
# =============================================================================

@bot.event
async def on_ready():
    """Bot起動時"""
    print(f"Bot起動完了: {bot.user}")

    # スラッシュコマンドを同期
    try:
        synced = await bot.tree.sync()
        print(f"スラッシュコマンド {len(synced)} 個を同期しました")
    except Exception as e:
        print(f"コマンド同期エラー: {e}")


@bot.event
async def on_message(message: discord.Message):
    """メッセージ受信時"""
    # ボット自身のメッセージは無視
    if message.author.bot:
        return

    # ボットがメンションされた場合のみ反応
    if bot.user and bot.user.mentioned_in(message):
        # メンション部分を除去
        content = message.content
        for mention in message.mentions:
            content = content.replace(f"<@{mention.id}>", "")
            content = content.replace(f"<@!{mention.id}>", "")
        content = content.strip()

        if content:
            await handle_natural_language(message, content)
        else:
            await message.reply(
                ":wave: こんにちは！Oura Bot です。\n"
                "「睡眠スコアは？」のように話しかけてください。\n"
                "`/help` でコマンド一覧を確認できます。"
            )

    # 他のコマンド処理を続行
    await bot.process_commands(message)


# =============================================================================
# エントリーポイント
# =============================================================================

def main():
    """Botを起動"""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("エラー: DISCORD_BOT_TOKEN が設定されていません")
        print("Discord Developer Portal でボットトークンを取得し、")
        print(".env ファイルに DISCORD_BOT_TOKEN=xxx を設定してください")
        sys.exit(1)

    print("Discord Bot を起動中...")
    bot.run(token)


if __name__ == "__main__":
    main()
