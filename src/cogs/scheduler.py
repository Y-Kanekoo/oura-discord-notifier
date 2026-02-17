"""バックグラウンドタスク（リマインダー・目標達成通知）"""

import logging
from datetime import time
from discord.ext import commands, tasks

from bot_utils import (
    get_oura_client,
    get_jst_now,
    get_jst_today,
    parse_time_str,
    settings,
)


logger = logging.getLogger(__name__)


class SchedulerCog(commands.Cog):
    """バックグラウンドタスク"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        """Cog読み込み時にスケジューラーを開始"""
        self.scheduler_loop.start()

    async def cog_unload(self):
        """Cog解放時にスケジューラーを停止"""
        self.scheduler_loop.cancel()

    @tasks.loop(minutes=1)
    async def scheduler_loop(self):
        """就寝リマインダーと目標達成通知を定期チェック"""
        now = get_jst_now()
        today_str = now.date().isoformat()

        # 日付が変わったらフラグをリセット
        try:
            settings.reset_daily_flags(today_str)
        except Exception:
            logger.warning("日次フラグのリセットに失敗しました", exc_info=True)

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
                        channel = self.bot.get_channel(int(channel_id))
                        if channel:
                            try:
                                await channel.send(
                                    ":crescent_moon: そろそろ就寝時間です。\n"
                                    "画面から目を離して、ゆっくり休みましょう。"
                                )
                            except Exception:
                                logger.warning("就寝リマインダーの送信に失敗しました", exc_info=True)
        except Exception:
            logger.warning("就寝リマインダー処理中にエラーが発生しました", exc_info=True)

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
                            channel = self.bot.get_channel(int(channel_id))
                            if channel:
                                try:
                                    await channel.send(
                                        f":tada: 今日の歩数目標を達成しました！\n**{steps:,} / {goal:,} 歩** おつかれさまです！"
                                    )
                                except Exception:
                                    logger.warning("目標達成通知の送信に失敗しました", exc_info=True)
                        # 達成フラグを更新
                        try:
                            settings.mark_goal_achieved(True, today_str)
                        except Exception:
                            logger.warning("目標達成フラグの更新に失敗しました", exc_info=True)
        except Exception:
            logger.warning("目標達成通知処理中にエラーが発生しました", exc_info=True)

    @scheduler_loop.before_loop
    async def before_scheduler_loop(self):
        """Bot起動を待ってからスケジューラーを開始"""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
