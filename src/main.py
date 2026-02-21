"""Oura Ring to Discord Notifier - Main Entry Point"""

import logging
import os
import sys
from datetime import timedelta
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# .envファイルの読み込み（存在する場合のみ）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(".envファイルを読み込みました: %s", env_path)
except ImportError:
    pass

from bot_utils import get_jst_now, get_jst_today  # noqa: E402
from discord_client import DiscordClient  # noqa: E402
from formatter import (  # noqa: E402
    format_morning_report,
    format_night_report,
    format_noon_report,
)
from oura_client import OuraClient  # noqa: E402

# デフォルト設定
DEFAULT_STEPS_GOAL = 8000


def get_env_var(name: str, default: str | None = None) -> str:
    """環境変数を取得"""
    value = os.environ.get(name, default)
    if value is None:
        logger.error("環境変数 %s が設定されていません", name)
        sys.exit(1)
    return value


def get_jst_hour() -> int:
    """JSTの現在時刻（時）を取得"""
    return get_jst_now().hour


# =============================================================================
# 朝通知
# =============================================================================

def send_morning_report() -> bool:
    """朝通知：睡眠 + Readiness + 今日の方針"""
    oura_token = get_env_var("OURA_ACCESS_TOKEN")
    discord_webhook = get_env_var("DISCORD_WEBHOOK_URL")

    oura = OuraClient(oura_token)
    discord = DiscordClient(discord_webhook)

    try:
        # 前日の睡眠データと当日のReadinessを取得
        today = get_jst_today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        logger.info("朝通知のデータを取得中: %s", today)

        data = {
            "sleep": oura.get_sleep(today),  # 当日朝までの睡眠
            "sleep_details": oura.get_sleep_details(today),
            "readiness": oura.get_readiness(today),
            "date": today.isoformat(),
        }

        # データがない場合は前日を試す（各項目を個別にチェック）
        if not data["sleep"]:
            data["sleep"] = oura.get_sleep(yesterday)
        if not data["sleep_details"]:
            data["sleep_details"] = oura.get_sleep_details(yesterday)
        if not data["readiness"]:
            data["readiness"] = oura.get_readiness(yesterday)

        # 前日データを取得（比較用）
        logger.info("前日データを取得中（比較用）")
        prev_data = {
            "sleep": oura.get_sleep(yesterday) if data["sleep"] and data["sleep"].get("day") == today.isoformat() else oura.get_sleep(two_days_ago),
            "readiness": oura.get_readiness(yesterday) if data["readiness"] and data["readiness"].get("day") == today.isoformat() else oura.get_readiness(two_days_ago),
        }

        # 週間平均を取得
        logger.info("週間平均を取得中")
        weekly_averages = None
        try:
            weekly_data = oura.get_weekly_data(yesterday)
            if weekly_data and weekly_data.get("averages"):
                weekly_averages = weekly_data["averages"]
        except requests.RequestException as e:
            logger.warning("週間データの取得に失敗: %s", e)

        title, sections = format_morning_report(data, prev_data, weekly_averages)

        logger.info("朝通知をDiscordに送信中")
        success = discord.send_health_report(title, sections)

        if success:
            logger.info("朝通知の送信に成功しました")
        else:
            logger.error("朝通知の送信に失敗しました")

        return success

    except requests.RequestException as e:
        logger.error("朝通知のAPI通信エラー: %s", e)
        try:
            discord.send_message(f":x: **朝通知エラー（通信）**\n```{str(e)}```")
        except requests.RequestException:
            logger.error("朝通知のエラー通知送信にも失敗しました", exc_info=True)
        return False
    except Exception as e:
        logger.error("朝通知で予期しないエラー: %s", e, exc_info=True)
        try:
            discord.send_message(f":x: **朝通知エラー**\n```{str(e)}```")
        except Exception:
            logger.error("朝通知のエラー通知送信に失敗しました", exc_info=True)
        return False


# =============================================================================
# 昼通知
# =============================================================================

def send_noon_report() -> bool:
    """昼通知：活動進捗 + 睡眠サマリー（朝に取れなかった場合の補完）"""
    oura_token = get_env_var("OURA_ACCESS_TOKEN")
    discord_webhook = get_env_var("DISCORD_WEBHOOK_URL")
    steps_goal = int(get_env_var("DAILY_STEPS_GOAL", str(DEFAULT_STEPS_GOAL)))

    oura = OuraClient(oura_token)
    discord = DiscordClient(discord_webhook)

    try:
        today = get_jst_today()
        current_hour = get_jst_hour()

        logger.info("昼通知のデータを取得中: %s %d:00", today, current_hour)

        activity = oura.get_activity(today)
        sleep = oura.get_sleep(today)
        sleep_details = oura.get_sleep_details(today)

        if not activity and not sleep:
            logger.info("活動・睡眠データがまだありません。昼通知をスキップします")
            return True  # データがないのは正常（まだ同期されていない）

        title, sections, should_send = format_noon_report(
            activity,
            steps_goal,
            current_hour,
            sleep,
            sleep_details,
        )

        if not should_send:
            logger.info("昼通知は不要です")
            if activity:
                logger.info("  歩数: %s / 目標ペース: OK", f"{activity.get('steps', 0):,}")
            return True

        logger.info("昼通知をDiscordに送信中")
        success = discord.send_health_report(title, sections)

        if success:
            logger.info("昼通知の送信に成功しました")
        else:
            logger.error("昼通知の送信に失敗しました")

        return success

    except requests.RequestException as e:
        logger.error("昼通知のAPI通信エラー: %s", e)
        try:
            discord.send_message(f":x: **昼通知エラー（通信）**\n```{str(e)}```")
        except requests.RequestException:
            logger.error("昼通知のエラー通知送信にも失敗しました", exc_info=True)
        return False
    except Exception as e:
        logger.error("昼通知で予期しないエラー: %s", e, exc_info=True)
        try:
            discord.send_message(f":x: **昼通知エラー**\n```{str(e)}```")
        except Exception:
            logger.error("昼通知のエラー通知送信に失敗しました", exc_info=True)
        return False


# =============================================================================
# 夜通知
# =============================================================================

def send_night_report() -> bool:
    """夜通知：今日の結果 + 減速リマインダー"""
    oura_token = get_env_var("OURA_ACCESS_TOKEN")
    discord_webhook = get_env_var("DISCORD_WEBHOOK_URL")
    target_wake_time = os.environ.get("TARGET_WAKE_TIME", "07:00")

    oura = OuraClient(oura_token)
    discord = DiscordClient(discord_webhook)

    try:
        today = get_jst_today()
        yesterday = today - timedelta(days=1)

        logger.info("夜通知のデータを取得中: %s", today)

        # 当日のデータを取得
        readiness = oura.get_readiness(today)
        sleep = oura.get_sleep(today)
        activity = oura.get_activity(today)

        # 前日データを取得（比較用）
        logger.info("前日データを取得中（比較用）")
        prev_activity = oura.get_activity(yesterday)

        # 週間平均を取得
        logger.info("週間平均を取得中")
        weekly_averages = None
        try:
            weekly_data = oura.get_weekly_data(yesterday)
            if weekly_data and weekly_data.get("averages"):
                weekly_averages = weekly_data["averages"]
        except requests.RequestException as e:
            logger.warning("週間データの取得に失敗: %s", e)

        title, sections = format_night_report(
            readiness,
            sleep,
            activity,
            prev_activity,
            weekly_averages,
            target_wake_time,
        )

        logger.info("夜通知をDiscordに送信中")
        success = discord.send_health_report(title, sections)

        if success:
            logger.info("夜通知の送信に成功しました")
        else:
            logger.error("夜通知の送信に失敗しました")

        return success

    except requests.RequestException as e:
        logger.error("夜通知のAPI通信エラー: %s", e)
        try:
            discord.send_message(f":x: **夜通知エラー（通信）**\n```{str(e)}```")
        except requests.RequestException:
            logger.error("夜通知のエラー通知送信にも失敗しました", exc_info=True)
    except Exception as e:
        logger.error("夜通知で予期しないエラー: %s", e, exc_info=True)
        try:
            discord.send_message(f":x: **夜通知エラー**\n```{str(e)}```")
        except Exception:
            logger.error("夜通知のエラー通知送信に失敗しました", exc_info=True)
        return False


# =============================================================================
# メイン
# =============================================================================

def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Oura Ring to Discord Notifier")
    parser.add_argument(
        "--type",
        type=str,
        choices=["morning", "noon", "night"],
        default="morning",
        help="Notification type: morning (default), noon, or night",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test message to verify configuration",
    )

    args = parser.parse_args()

    if args.test:
        discord_webhook = get_env_var("DISCORD_WEBHOOK_URL")
        discord = DiscordClient(discord_webhook)
        success = discord.send_message(
            ":white_check_mark: **テスト成功！**\n"
            "Oura Discord Notifierが正常に動作しています。"
        )
        logger.info("テストメッセージ送信: %s", "成功" if success else "失敗")
        sys.exit(0 if success else 1)

    # 通知タイプに応じて実行
    if args.type == "morning":
        success = send_morning_report()
    elif args.type == "noon":
        success = send_noon_report()
    elif args.type == "night":
        success = send_night_report()
    else:
        logger.error("不明な通知タイプ: %s", args.type)
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
