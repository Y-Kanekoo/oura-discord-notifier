"""Discord Bot - 会話型インターフェース"""

import os
import re
import sys
import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import date, timedelta, datetime, time
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Optional, List

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
    format_time_from_iso,
)
from settings import SettingsManager
from advice import generate_advice
from chart import generate_score_chart, generate_steps_chart, generate_combined_chart


# ボット設定
intents = discord.Intents.default()
intents.message_content = True  # 自然言語対応に必要

bot = commands.Bot(command_prefix="!", intents=intents)
settings = SettingsManager()

# OuraClient インスタンス（遅延初期化）
_oura_client: Optional[OuraClient] = None


JST = ZoneInfo("Asia/Tokyo")


def get_jst_now() -> datetime:
    """JSTの現在時刻を取得"""
    return datetime.now(JST)


def get_jst_today() -> date:
    """JSTの今日の日付を取得"""
    return get_jst_now().date()


def get_oura_client() -> OuraClient:
    """OuraClient のシングルトン取得"""
    global _oura_client
    if _oura_client is None:
        token = os.environ.get("OURA_ACCESS_TOKEN")
        if not token:
            raise ValueError("OURA_ACCESS_TOKEN が設定されていません")
        _oura_client = OuraClient(token)
    return _oura_client


def parse_date(date_str: str, default_date: Optional[date] = None) -> date:
    """
    様々な形式の日付文字列をパース

    対応形式:
    - 今日, きょう, today
    - 昨日, きのう, yesterday
    - 一昨日, おととい
    - N日前 (例: 3日前)
    - -N (例: -1 = 昨日)
    - YYYY-MM-DD (2026-01-02)
    - YYYY/MM/DD (2026/01/02)
    - MM-DD, MM/DD (01-02, 01/02)
    - M/D, M-D (1/2, 1-2)
    - MMDD (0102)
    - N月D日 (1月2日)
    """
    if not date_str:
        return default_date or get_jst_today()

    s = date_str.strip().lower()
    today = get_jst_today()

    # 日本語の相対日付
    if s in ("今日", "きょう", "today"):
        return today
    if s in ("昨日", "きのう", "yesterday"):
        return today - timedelta(days=1)
    if s in ("一昨日", "おととい"):
        return today - timedelta(days=2)

    # N日前
    m = re.match(r"(\d+)日前", s)
    if m:
        return today - timedelta(days=int(m.group(1)))

    # -N 形式
    m = re.match(r"^-(\d+)$", s)
    if m:
        return today - timedelta(days=int(m.group(1)))

    # N月D日 形式
    m = re.match(r"(\d{1,2})月(\d{1,2})日?", s)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        return date(today.year, month, day)

    # YYYY-MM-DD または YYYY/MM/DD
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # MM-DD, MM/DD, M-D, M/D
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})$", s)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        return date(today.year, month, day)

    # MMDD (4桁)
    m = re.match(r"^(\d{2})(\d{2})$", s)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        return date(today.year, month, day)

    # ISO形式にフォールバック
    return date.fromisoformat(date_str)


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


def parse_time_str(time_str: str) -> time:
    """HH:MM 形式の文字列を time に変換"""
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str.strip())
    if not m:
        raise ValueError("時刻は HH:MM 形式で指定してください (例: 22:30)")

    hour = int(m.group(1))
    minute = int(m.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("時刻は 00:00〜23:59 の範囲で指定してください")

    return time(hour=hour, minute=minute)


# =============================================================================
# スラッシュコマンド
# =============================================================================

@bot.tree.command(name="sleep", description="睡眠スコアを表示します")
@app_commands.describe(
    date_str="日付（例: 昨日, 1/1, 01-02）または日数（例: 3 = 直近3日間）省略時は昨日"
)
async def sleep_command(interaction: discord.Interaction, date_str: Optional[str] = None):
    """睡眠データを表示（複数日表示対応）"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        # 数字のみの場合は複数日表示
        if date_str and date_str.isdigit():
            days = min(int(date_str), 7)  # 最大7日
            embeds = []
            for i in range(days):
                target_date = get_jst_today() - timedelta(days=i + 1)
                sleep_data = oura.get_sleep(target_date)
                sleep_details = oura.get_sleep_details(target_date)
                if sleep_data:
                    section = format_sleep_section(sleep_data, sleep_details)
                    embeds.append(create_embed_from_section(section))

            if embeds:
                await interaction.followup.send(
                    content=f":zzz: **直近{days}日間の睡眠データ**",
                    embeds=embeds[:10]  # Discord は最大10 embeds
                )
            else:
                await interaction.followup.send(":warning: 睡眠データがありません")
            return

        # 通常の日付指定
        default_date = get_jst_today() - timedelta(days=1)
        target_date = parse_date(date_str, default_date) if date_str else default_date

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
@app_commands.describe(date_str="日付（例: 今日, 昨日, 1/1, 01-02）省略時は今日")
async def readiness_command(interaction: discord.Interaction, date_str: Optional[str] = None):
    """Readinessデータを表示（HRV情報付き）"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        # 日付パース（デフォルトは今日）
        target_date = parse_date(date_str, get_jst_today()) if date_str else get_jst_today()

        readiness_data = oura.get_readiness(target_date)

        if not readiness_data:
            await interaction.followup.send(f":warning: {target_date} のReadinessデータがありません")
            return

        section = format_readiness_section(readiness_data)
        embed = create_embed_from_section(section)

        # 前夜の睡眠詳細から HRV 情報を取得（あれば表示）
        sleep_details = oura.get_sleep_details(target_date)
        if sleep_details:
            average_hrv = sleep_details.get("average_hrv")
            if average_hrv:
                embed.add_field(
                    name=":chart_with_upwards_trend: 平均HRV",
                    value=f"{average_hrv:.0f} ms",
                    inline=True,
                )

        await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(f":x: 日付形式が不正です: {str(e)}")
    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="activity", description="活動データを表示します")
@app_commands.describe(date_str="日付（例: 今日, 昨日, 1/1, 01-02）省略時は今日")
async def activity_command(interaction: discord.Interaction, date_str: Optional[str] = None):
    """活動データを表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        # 日付パース（デフォルトは今日）
        target_date = parse_date(date_str, get_jst_today()) if date_str else get_jst_today()

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
        activity_data = oura.get_activity(get_jst_today())

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
            data = oura.get_all_daily_data(get_jst_today())
            title, sections = format_morning_report(data)

        elif report_type == "noon":
            activity = oura.get_activity(get_jst_today())
            sleep = oura.get_sleep(get_jst_today())
            sleep_details = oura.get_sleep_details(get_jst_today())
            goal = settings.get_steps_goal()

            title, sections, should_send = format_noon_report(
                activity, goal, sleep_data=sleep, sleep_details=sleep_details
            )
            if not should_send:
                await interaction.followup.send(":white_check_mark: 順調です！特に通知はありません。")
                return

        elif report_type == "night":
            readiness = oura.get_readiness(get_jst_today())
            sleep = oura.get_sleep(get_jst_today())
            activity = oura.get_activity(get_jst_today())
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

    # 就寝リマインダー
    br_enabled = all_settings.get("bedtime_reminder_enabled", False)
    br_time = all_settings.get("bedtime_reminder_time", "22:30")
    br_channel_id = all_settings.get("bedtime_reminder_channel_id")
    embed.add_field(
        name=":crescent_moon: 就寝リマインダー",
        value=(
            f"状態: {'有効' if br_enabled else '無効'}\n"
            f"時刻: {br_time}\n"
            f"チャンネル: {('<#' + str(br_channel_id) + '>') if br_channel_id else '未設定'}"
        ),
        inline=False,
    )

    # 目標達成通知
    gn_enabled = all_settings.get("goal_notification_enabled", False)
    gn_channel_id = all_settings.get("goal_notification_channel_id")
    embed.add_field(
        name=":tada: 目標達成通知",
        value=(
            f"状態: {'有効' if gn_enabled else '無効'}\n"
            f"チャンネル: {('<#' + str(gn_channel_id) + '>') if gn_channel_id else '未設定'}"
        ),
        inline=False,
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
        readiness = oura.get_readiness(get_jst_today())
        sleep = oura.get_sleep(get_jst_today())
        activity = oura.get_activity(get_jst_today())

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


@bot.tree.command(name="week", description="過去7日間のスコアとトレンドを表示します")
@app_commands.describe(date_str="終了日（例: 今日, 昨日, 2024-01-01）。省略時は今日までの7日間")
async def week_command(interaction: discord.Interaction, date_str: Optional[str] = None):
    """週間サマリーと先週比トレンド"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        end_date = parse_date(date_str, get_jst_today()) if date_str else get_jst_today()
        weekly = oura.get_weekly_data(end_date)

        # 先週分も取得（比較用）
        prev_weekly = oura.get_weekly_data(end_date - timedelta(days=7))

        start_date = date.fromisoformat(weekly["start_date"])
        end_date_parsed = date.fromisoformat(weekly["end_date"])

        title = f":calendar: 週間サマリー ({start_date.strftime('%-m/%-d')} ~ {end_date_parsed.strftime('%-m/%-d')})"

        # 日別サマリー
        lines: List[str] = []
        for day in weekly["daily_data"]:
            d = date.fromisoformat(day["date"])
            sleep_score = day.get("sleep_score")
            readiness_score = day.get("readiness_score")
            activity_score = day.get("activity_score")
            steps = day.get("steps")

            parts = []
            if sleep_score is not None:
                parts.append(f"睡眠 {sleep_score}")
            if readiness_score is not None:
                parts.append(f"Readiness {readiness_score}")
            if activity_score is not None:
                parts.append(f"活動 {activity_score}")
            if steps is not None:
                parts.append(f"歩数 {steps:,}")

            if parts:
                lines.append(f"**{d.strftime('%-m/%-d')}**: " + " / ".join(parts))

        averages = weekly.get("averages", {})
        totals = weekly.get("totals", {})

        desc_lines: List[str] = []
        if averages.get("sleep") is not None:
            desc_lines.append(f"睡眠スコア平均: {averages['sleep']:.1f}")
        if averages.get("readiness") is not None:
            desc_lines.append(f"Readiness平均: {averages['readiness']:.1f}")
        if averages.get("activity") is not None:
            desc_lines.append(f"活動スコア平均: {averages['activity']:.1f}")
        if averages.get("steps") is not None:
            desc_lines.append(f"平均歩数: {averages['steps']:.0f} 歩")
        if totals.get("steps") is not None:
            desc_lines.append(f"合計歩数: {totals['steps']:,} 歩")

        embed = discord.Embed(
            title=title,
            description="\n".join(desc_lines) if desc_lines else None,
            color=0x00D4AA,
        )

        if lines:
            embed.add_field(
                name=":spiral_calendar_pad: 日別スコア",
                value="\n".join(lines),
                inline=False,
            )

        # 先週比
        prev_avg = prev_weekly.get("averages", {}) if prev_weekly else {}
        trend_lines: List[str] = []
        for key, label in (
            ("sleep", "睡眠"),
            ("readiness", "Readiness"),
            ("activity", "活動"),
            ("steps", "歩数"),
        ):
            cur = averages.get(key)
            prev = prev_avg.get(key)
            if cur is not None and prev is not None:
                diff = cur - prev
                sign = "+" if diff >= 0 else ""
                unit = "pt" if key != "steps" else "歩"
                trend_lines.append(f"{label}: {cur:.1f} ({sign}{diff:.1f}{unit} vs 先週)") if key != "steps" else trend_lines.append(f"{label}: {cur:.0f} ({sign}{diff:.0f}{unit} vs 先週)")

        if trend_lines:
            embed.add_field(
                name=":chart_with_upwards_trend: 先週との比較",
                value="\n".join(trend_lines),
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(f":x: 日付形式が不正です: {str(e)}")
    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="temperature", description="体温偏差データを表示します")
@app_commands.describe(date_str="日付（例: 昨日, 1/1, 01-02）省略時は昨日の睡眠に基づく体温")
async def temperature_command(interaction: discord.Interaction, date_str: Optional[str] = None):
    """体温偏差を表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        default_date = get_jst_today() - timedelta(days=1)
        target_date = parse_date(date_str, default_date) if date_str else default_date

        sleep_data = oura.get_sleep(target_date)
        if not sleep_data:
            await interaction.followup.send(f":warning: {target_date} の睡眠データがありません")
            return

        temp_dev = sleep_data.get("temperature_deviation")
        if temp_dev is None:
            temp_dev = sleep_data.get("average_temperature_deviation")

        if temp_dev is None:
            await interaction.followup.send(":warning: 体温偏差データが見つかりませんでした")
            return

        sign = "+" if temp_dev >= 0 else ""
        description = (
            f"平均体温偏差: **{sign}{temp_dev:.2f}°C**\n"
            "(平常時からのズレを示します。+方向はやや高め、-方向はやや低めです)"
        )

        embed = discord.Embed(
            title=":thermometer: 体温偏差",
            description=description,
            color=0xFF7F50 if temp_dev >= 0.5 else (0xFFFF00 if temp_dev >= 0.2 else 0x00D4AA),
        )

        await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(f":x: 日付形式が不正です: {str(e)}")
    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="workout", description="Oura が検出したワークアウトを表示します")
@app_commands.describe(date_str="日付（例: 今日, 昨日, 1/1, 01-02）省略時は今日")
async def workout_command(interaction: discord.Interaction, date_str: Optional[str] = None):
    """ワークアウトデータを表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()
        target_date = parse_date(date_str, get_jst_today()) if date_str else get_jst_today()

        workouts = oura.get_workout(target_date)
        if not workouts:
            await interaction.followup.send(f":warning: {target_date} のワークアウトデータがありません")
            return

        title = f":runner: {target_date.strftime('%-m/%-d')} のワークアウト"

        lines: List[str] = []
        for w in workouts[:10]:  # 念のため10件まで
            w_type = w.get("label") or w.get("type") or "Workout"
            start = w.get("start_datetime") or w.get("start_time")
            end = w.get("end_datetime") or w.get("end_time")
            duration = w.get("duration")  # 秒
            calories = w.get("calories") or w.get("active_calories")
            avg_hr = w.get("average_heart_rate")

            parts = [f"**{w_type}**"]
            if start:
                parts.append(format_time_from_iso(start))
            if end:
                parts.append("→ " + format_time_from_iso(end))

            detail_parts = []
            if duration:
                detail_parts.append(format_duration(duration))
            if calories:
                detail_parts.append(f"{calories} kcal")
            if avg_hr:
                detail_parts.append(f"平均 {avg_hr} bpm")

            line = " ".join(parts)
            if detail_parts:
                line += "\n  " + " / ".join(detail_parts)

            lines.append(line)

        embed = discord.Embed(
            title=title,
            description="\n\n".join(lines),
            color=0x3498DB,
        )

        await interaction.followup.send(embed=embed)

    except ValueError as e:
        await interaction.followup.send(f":x: 日付形式が不正です: {str(e)}")
    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="bedtime_reminder", description="就寝リマインダーの設定を変更します")
@app_commands.describe(
    enabled="リマインダーを有効にするかどうか",
    time_str="就寝リマインダーの時刻 (HH:MM)。省略時は現在の設定を維持",
    channel="通知を送信するチャンネル。省略時はこのチャンネル",
)
async def bedtime_reminder_command(
    interaction: discord.Interaction,
    enabled: bool,
    time_str: Optional[str] = None,
    channel: Optional[discord.TextChannel] = None,
):
    """就寝リマインダー設定"""
    try:
        channel_id = (channel or interaction.channel).id if interaction.channel else (channel.id if channel else None)
        if channel_id is None:
            await interaction.response.send_message(":x: チャンネルを特定できませんでした")
            return

        # 時刻のバリデーション
        if time_str:
            try:
                parse_time_str(time_str)
            except ValueError as e:
                await interaction.response.send_message(f":x: {str(e)}")
                return

        settings.set_bedtime_reminder(enabled=enabled, time=time_str, channel_id=channel_id)

        status = "有効" if enabled else "無効"
        time_disp = time_str or settings.get_bedtime_reminder().get("time")

        await interaction.response.send_message(
            f":white_check_mark: 就寝リマインダーを{status}にしました\n"
            f"時刻: **{time_disp}**\n"
            f"チャンネル: <#{channel_id}>"
        )

    except Exception as e:
        await interaction.response.send_message(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="goal_notification", description="歩数目標達成時の通知を設定します")
@app_commands.describe(
    enabled="目標達成時の通知を有効にするかどうか",
    channel="通知を送信するチャンネル。省略時はこのチャンネル",
)
async def goal_notification_command(
    interaction: discord.Interaction,
    enabled: bool,
    channel: Optional[discord.TextChannel] = None,
):
    """目標達成通知の設定"""
    try:
        channel_id = (channel or interaction.channel).id if interaction.channel else (channel.id if channel else None)
        if channel_id is None:
            await interaction.response.send_message(":x: チャンネルを特定できませんでした")
            return

        settings.set_goal_notification(enabled=enabled, channel_id=channel_id)
        if not enabled:
            settings.mark_goal_achieved(False)

        status = "有効" if enabled else "無効"

        await interaction.response.send_message(
            f":white_check_mark: 目標達成通知を{status}にしました\n"
            f"チャンネル: <#{channel_id}>"
        )

    except Exception as e:
        await interaction.response.send_message(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="month", description="過去30日間のサマリーを表示します")
@app_commands.describe(days="集計日数（デフォルト: 30日）")
async def month_command(interaction: discord.Interaction, days: Optional[int] = 30):
    """月間サマリーを表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        # 日数制限
        days = max(7, min(days, 90))

        monthly = oura.get_monthly_data(days=days)
        stats = monthly.get("stats", {})
        totals = monthly.get("totals", {})

        start_date = date.fromisoformat(monthly["start_date"])
        end_date = date.fromisoformat(monthly["end_date"])

        title = f":calendar: {days}日間サマリー ({start_date.strftime('%-m/%-d')} ~ {end_date.strftime('%-m/%-d')})"

        embed = discord.Embed(
            title=title,
            color=0x00D4AA,
        )

        # 睡眠統計
        sleep_stats = stats.get("sleep", {})
        if sleep_stats.get("avg") is not None:
            embed.add_field(
                name=":zzz: 睡眠スコア",
                value=(
                    f"平均: **{sleep_stats['avg']:.1f}**\n"
                    f"最高: {sleep_stats['max']} / 最低: {sleep_stats['min']}\n"
                    f"データ: {sleep_stats['count']}日"
                ),
                inline=True,
            )

        # Readiness統計
        readiness_stats = stats.get("readiness", {})
        if readiness_stats.get("avg") is not None:
            embed.add_field(
                name=":zap: Readiness",
                value=(
                    f"平均: **{readiness_stats['avg']:.1f}**\n"
                    f"最高: {readiness_stats['max']} / 最低: {readiness_stats['min']}\n"
                    f"データ: {readiness_stats['count']}日"
                ),
                inline=True,
            )

        # 活動統計
        activity_stats = stats.get("activity", {})
        if activity_stats.get("avg") is not None:
            embed.add_field(
                name=":running: 活動スコア",
                value=(
                    f"平均: **{activity_stats['avg']:.1f}**\n"
                    f"最高: {activity_stats['max']} / 最低: {activity_stats['min']}\n"
                    f"データ: {activity_stats['count']}日"
                ),
                inline=True,
            )

        # 歩数統計
        steps_stats = stats.get("steps", {})
        if steps_stats.get("avg") is not None:
            goal = settings.get_steps_goal()
            goal_achieved = sum(1 for d in monthly["daily_data"] if d.get("steps") and d["steps"] >= goal)
            embed.add_field(
                name=":footprints: 歩数",
                value=(
                    f"平均: **{steps_stats['avg']:,.0f}** 歩/日\n"
                    f"合計: {totals.get('steps', 0):,} 歩\n"
                    f"目標達成: {goal_achieved}/{steps_stats['count']}日"
                ),
                inline=True,
            )

        embed.set_footer(text="グラフを見るには /graph コマンドを使用")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")


@bot.tree.command(name="graph", description="データの推移グラフを表示します")
@app_commands.describe(
    graph_type="グラフの種類",
    days="集計日数（デフォルト: 14日）",
)
@app_commands.choices(graph_type=[
    app_commands.Choice(name="スコア推移（睡眠・Readiness・活動）", value="scores"),
    app_commands.Choice(name="歩数推移", value="steps"),
    app_commands.Choice(name="総合（スコア＋歩数）", value="combined"),
])
async def graph_command(
    interaction: discord.Interaction,
    graph_type: str = "combined",
    days: Optional[int] = 14,
):
    """グラフを表示"""
    await interaction.response.defer()

    try:
        oura = get_oura_client()

        # 日数制限
        days = max(7, min(days, 90))

        monthly = oura.get_monthly_data(days=days)
        daily_data = monthly.get("daily_data", [])

        if not daily_data:
            await interaction.followup.send(":warning: データがありません")
            return

        goal = settings.get_steps_goal()

        start_date = date.fromisoformat(monthly["start_date"])
        end_date = date.fromisoformat(monthly["end_date"])
        title = f"{start_date.strftime('%-m/%-d')} ~ {end_date.strftime('%-m/%-d')} ({days}日間)"

        # グラフ生成
        if graph_type == "scores":
            buf = generate_score_chart(daily_data, title=f"スコア推移 - {title}")
        elif graph_type == "steps":
            buf = generate_steps_chart(daily_data, goal=goal, title=f"歩数推移 - {title}")
        else:  # combined
            buf = generate_combined_chart(daily_data, goal=goal, title=f"月間サマリー - {title}")

        # Discordに送信
        file = discord.File(buf, filename="chart.png")
        await interaction.followup.send(file=file)

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


# =============================================================================
# バックグラウンドタスク（リマインダー・目標達成通知）
# =============================================================================

@tasks.loop(minutes=1)
async def scheduler_loop():
    """就寝リマインダーと目標達成通知を定期チェック"""
    now = get_jst_now()
    today_str = now.date().isoformat()

    # 日付が変わったらフラグをリセット
    try:
        settings.reset_daily_flags(today_str)
    except Exception:
        # 設定ファイルの問題があっても他の処理は続ける
        pass

    # 就寝リマインダー
    try:
        br = settings.get_bedtime_reminder()
        if br.get("enabled"):
            target_time_str = br.get("time", "22:30")
            try:
                target_time = parse_time_str(target_time_str)
            except ValueError:
                target_time = time(hour=22, minute=30)

            if now.hour == target_time.hour and now.minute == target_time.minute:
                channel_id = br.get("channel_id")
                if channel_id:
                    channel = bot.get_channel(int(channel_id))
                    if channel:
                        try:
                            await channel.send(
                                ":crescent_moon: そろそろ就寝時間です。\n"
                                "画面から目を離して、ゆっくり休みましょう。"
                            )
                        except Exception:
                            pass
    except Exception:
        pass

    # 目標達成通知
    try:
        goal_info = settings.get_goal_notification()
        if goal_info.get("enabled") and not goal_info.get("achieved_today"):
            oura = get_oura_client()
            activity = oura.get_activity(get_jst_today())
            if activity:
                steps = activity.get("steps", 0)
                goal = settings.get_steps_goal()
                if goal and steps >= goal:
                    channel_id = goal_info.get("channel_id")
                    if channel_id:
                        channel = bot.get_channel(int(channel_id))
                        if channel:
                            try:
                                await channel.send(
                                    f":tada: 今日の歩数目標を達成しました！\n**{steps:,} / {goal:,} 歩** おつかれさまです！"
                                )
                            except Exception:
                                pass
                    # 達成フラグを更新
                    try:
                        settings.mark_goal_achieved(True, today_str)
                    except Exception:
                        pass
    except Exception:
        pass


# =============================================================================
# イベントハンドラ
# =============================================================================

@bot.event
async def on_ready():
    """Bot起動時"""
    print(f"Bot起動完了: {bot.user}")

    # バックグラウンドタスク開始
    if not scheduler_loop.is_running():
        scheduler_loop.start()

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
