"""ヘルスデータ照会コマンド"""

from datetime import timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot_utils import (
    create_embed_from_section,
    get_jst_today,
    get_oura_client,
    parse_date,
    settings,
)
from formatter import (
    format_duration,
    format_readiness_section,
    format_sleep_section,
    format_time_from_iso,
    get_score_emoji,
    get_score_label,
)


class HealthCog(commands.Cog):
    """ヘルスデータ照会コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sleep", description="睡眠スコアを表示します")
    @app_commands.describe(
        date_str="日付（例: 昨日, 1/1, 01-02）または日数（例: 3 = 直近3日間）省略時は昨日"
    )
    async def sleep_command(self, interaction: discord.Interaction, date_str: Optional[str] = None):
        """睡眠データを表示（複数日表示対応）"""
        await interaction.response.defer()

        try:
            oura = get_oura_client()

            # 数字のみの場合は複数日表示（一括取得で API 呼び出しを削減）
            if date_str and date_str.isdigit():
                days = min(int(date_str), 7)  # 最大7日
                end_date = get_jst_today() - timedelta(days=1)
                start_date = get_jst_today() - timedelta(days=days)
                sleep_map = oura.get_sleep_range(start_date, end_date)
                details_map = oura.get_sleep_details_range(start_date, end_date)

                embeds = []
                for i in range(days):
                    target_date = get_jst_today() - timedelta(days=i + 1)
                    date_key = target_date.isoformat()
                    sleep_data = sleep_map.get(date_key)
                    sleep_details = details_map.get(date_key)
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

    @app_commands.command(name="readiness", description="Readiness（準備度）スコアを表示します")
    @app_commands.describe(date_str="日付（例: 今日, 昨日, 1/1, 01-02）省略時は今日")
    async def readiness_command(self, interaction: discord.Interaction, date_str: Optional[str] = None):
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

    @app_commands.command(name="activity", description="活動データを表示します")
    @app_commands.describe(date_str="日付（例: 今日, 昨日, 1/1, 01-02）省略時は今日")
    async def activity_command(self, interaction: discord.Interaction, date_str: Optional[str] = None):
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

    @app_commands.command(name="steps", description="今日の歩数を表示します")
    async def steps_command(self, interaction: discord.Interaction):
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

    @app_commands.command(name="temperature", description="体温偏差データを表示します")
    @app_commands.describe(date_str="日付（例: 昨日, 1/1, 01-02）省略時は昨日の睡眠に基づく体温")
    async def temperature_command(self, interaction: discord.Interaction, date_str: Optional[str] = None):
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

    @app_commands.command(name="workout", description="Oura が検出したワークアウトを表示します")
    @app_commands.describe(date_str="日付（例: 今日, 昨日, 1/1, 01-02）省略時は今日")
    async def workout_command(self, interaction: discord.Interaction, date_str: Optional[str] = None):
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

            lines = []
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


async def setup(bot: commands.Bot):
    await bot.add_cog(HealthCog(bot))
