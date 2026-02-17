"""設定管理コマンド"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from bot_utils import parse_time_str, settings


class SettingsCog(commands.Cog):
    """設定管理コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="goal", description="歩数目標を変更します")
    @app_commands.describe(value="新しい歩数目標")
    async def goal_command(self, interaction: discord.Interaction, value: int):
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

    @app_commands.command(name="settings", description="現在の設定を表示します")
    async def settings_command(self, interaction: discord.Interaction):
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

    @app_commands.command(name="bedtime_reminder", description="就寝リマインダーの設定を変更します")
    @app_commands.describe(
        enabled="リマインダーを有効にするかどうか",
        time_str="就寝リマインダーの時刻 (HH:MM)。省略時は現在の設定を維持",
        channel="通知を送信するチャンネル。省略時はこのチャンネル",
    )
    async def bedtime_reminder_command(
        self,
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

    @app_commands.command(name="goal_notification", description="歩数目標達成時の通知を設定します")
    @app_commands.describe(
        enabled="目標達成時の通知を有効にするかどうか",
        channel="通知を送信するチャンネル。省略時はこのチャンネル",
    )
    async def goal_notification_command(
        self,
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


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
