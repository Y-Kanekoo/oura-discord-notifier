"""レポート・分析コマンド"""

from datetime import date, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from advice import generate_advice
from bot_utils import (
    create_embed_from_section,
    get_jst_today,
    get_oura_client,
    parse_date,
    run_sync,
    settings,
)
from chart import generate_combined_chart, generate_score_chart, generate_steps_chart
from formatter import (
    format_morning_report,
    format_night_report,
    format_noon_report,
)


class ReportCog(commands.Cog):
    """レポート・分析コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="report", description="レポートを送信します")
    @app_commands.describe(report_type="レポートの種類")
    @app_commands.choices(report_type=[
        app_commands.Choice(name="朝レポート（睡眠+Readiness）", value="morning"),
        app_commands.Choice(name="昼レポート（活動進捗）", value="noon"),
        app_commands.Choice(name="夜レポート（今日の結果）", value="night"),
    ])
    async def report_command(self, interaction: discord.Interaction, report_type: str = "morning"):
        """レポートを送信"""
        await interaction.response.defer()

        try:
            oura = get_oura_client()

            if report_type == "morning":
                data = await run_sync(oura.get_all_daily_data, get_jst_today())
                title, sections = format_morning_report(data)

            elif report_type == "noon":
                activity = await run_sync(oura.get_activity, get_jst_today())
                sleep = await run_sync(oura.get_sleep, get_jst_today())
                sleep_details = await run_sync(oura.get_sleep_details, get_jst_today())
                goal = settings.get_steps_goal()

                title, sections, should_send = format_noon_report(
                    activity, goal, sleep_data=sleep, sleep_details=sleep_details
                )
                if not should_send:
                    await interaction.followup.send(":white_check_mark: 順調です！特に通知はありません。")
                    return

            elif report_type == "night":
                readiness = await run_sync(oura.get_readiness, get_jst_today())
                sleep = await run_sync(oura.get_sleep, get_jst_today())
                activity = await run_sync(oura.get_activity, get_jst_today())
                title, sections = format_night_report(readiness, sleep, activity)

            else:
                await interaction.followup.send(":x: 不明なレポートタイプです")
                return

            # 各セクションをEmbedとして送信
            embeds = [create_embed_from_section(section) for section in sections]
            await interaction.followup.send(content=title, embeds=embeds)

        except Exception as e:
            await interaction.followup.send(f":x: エラーが発生しました: {str(e)}")

    @app_commands.command(name="advice", description="今日のアドバイスを取得します")
    async def advice_command(self, interaction: discord.Interaction):
        """アドバイスを表示"""
        await interaction.response.defer()

        try:
            oura = get_oura_client()

            # 今日のデータを取得
            readiness = await run_sync(oura.get_readiness, get_jst_today())
            sleep = await run_sync(oura.get_sleep, get_jst_today())
            activity = await run_sync(oura.get_activity, get_jst_today())

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

    @app_commands.command(name="week", description="過去7日間のスコアとトレンドを表示します")
    @app_commands.describe(date_str="終了日（例: 今日, 昨日, 2024-01-01）。省略時は今日までの7日間")
    async def week_command(self, interaction: discord.Interaction, date_str: Optional[str] = None):
        """週間サマリーと先週比トレンド"""
        await interaction.response.defer()

        try:
            oura = get_oura_client()

            end_date = parse_date(date_str, get_jst_today()) if date_str else get_jst_today()
            weekly = await run_sync(oura.get_weekly_data, end_date)

            # 先週分も取得（比較用）
            prev_weekly = await run_sync(oura.get_weekly_data, end_date - timedelta(days=7))

            start_date = date.fromisoformat(weekly["start_date"])
            end_date_parsed = date.fromisoformat(weekly["end_date"])

            title = f":calendar: 週間サマリー ({start_date.strftime('%-m/%-d')} ~ {end_date_parsed.strftime('%-m/%-d')})"

            # 日別サマリー
            lines: list[str] = []
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

            desc_lines: list[str] = []
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
            trend_lines: list[str] = []
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

    @app_commands.command(name="month", description="過去30日間のサマリーを表示します")
    @app_commands.describe(days="集計日数（デフォルト: 30日）")
    async def month_command(self, interaction: discord.Interaction, days: Optional[int] = 30):
        """月間サマリーを表示"""
        await interaction.response.defer()

        try:
            oura = get_oura_client()

            # 日数制限
            days = max(7, min(days, 90))

            monthly = await run_sync(oura.get_monthly_data, days=days)
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

    @app_commands.command(name="graph", description="データの推移グラフを表示します")
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
        self,
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

            monthly = await run_sync(oura.get_monthly_data, days=days)
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


async def setup(bot: commands.Bot):
    await bot.add_cog(ReportCog(bot))
