"""Oura Ring to Discord Notifier - Main Entry Point"""

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# .envファイルの読み込み（存在する場合のみ）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
except ImportError:
    pass

from oura_client import OuraClient
from discord_client import DiscordClient
from formatter import (
    format_morning_report,
    format_noon_report,
    format_night_report,
)

# タイムゾーン
JST = ZoneInfo("Asia/Tokyo")

# デフォルト設定
DEFAULT_STEPS_GOAL = 8000


def get_env_var(name: str, default: str | None = None) -> str:
    """環境変数を取得"""
    value = os.environ.get(name, default)
    if value is None:
        print(f"Error: {name} environment variable is not set")
        sys.exit(1)
    return value


def get_jst_today() -> date:
    """JSTの今日の日付を取得"""
    return datetime.now(JST).date()


def get_jst_hour() -> int:
    """JSTの現在時刻（時）を取得"""
    return datetime.now(JST).hour


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

        print(f"Fetching morning data for {today}...")

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
        print("Fetching previous day data for comparison...")
        prev_data = {
            "sleep": oura.get_sleep(yesterday) if data["sleep"] and data["sleep"].get("day") == today.isoformat() else oura.get_sleep(two_days_ago),
            "readiness": oura.get_readiness(yesterday) if data["readiness"] and data["readiness"].get("day") == today.isoformat() else oura.get_readiness(two_days_ago),
        }

        # 週間平均を取得
        print("Fetching weekly averages...")
        weekly_averages = None
        try:
            weekly_data = oura.get_weekly_data(yesterday)
            if weekly_data and weekly_data.get("averages"):
                weekly_averages = weekly_data["averages"]
        except Exception as e:
            print(f"Warning: Could not fetch weekly data: {e}")

        title, sections = format_morning_report(data, prev_data, weekly_averages)

        print("Sending morning report to Discord...")
        success = discord.send_health_report(title, sections)

        if success:
            print("Morning report sent successfully!")
        else:
            print("Failed to send morning report")

        return success

    except Exception as e:
        print(f"Error: {e}")
        try:
            discord.send_message(f":x: **朝通知エラー**\n```{str(e)}```")
        except Exception:
            pass
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

        print(f"Fetching noon data for {today} at {current_hour}:00...")

        activity = oura.get_activity(today)
        sleep = oura.get_sleep(today)
        sleep_details = oura.get_sleep_details(today)

        if not activity and not sleep:
            print("No activity or sleep data available yet. Skipping noon notification.")
            return True  # データがないのは正常（まだ同期されていない）

        title, sections, should_send = format_noon_report(
            activity,
            steps_goal,
            current_hour,
            sleep,
            sleep_details,
        )

        if not should_send:
            print(f"No noon notification needed.")
            if activity:
                print(f"  Steps: {activity.get('steps', 0):,} / Goal pace: OK")
            return True

        print("Sending noon report to Discord...")
        success = discord.send_health_report(title, sections)

        if success:
            print("Noon report sent successfully!")
        else:
            print("Failed to send noon report")

        return success

    except Exception as e:
        print(f"Error: {e}")
        return False


# =============================================================================
# 夜通知
# =============================================================================

def send_night_report() -> bool:
    """夜通知：今日の結果 + 減速リマインダー"""
    oura_token = get_env_var("OURA_ACCESS_TOKEN")
    discord_webhook = get_env_var("DISCORD_WEBHOOK_URL")

    oura = OuraClient(oura_token)
    discord = DiscordClient(discord_webhook)

    try:
        today = get_jst_today()

        print(f"Fetching night data for {today}...")

        # 当日のデータを取得
        readiness = oura.get_readiness(today)
        sleep = oura.get_sleep(today)
        activity = oura.get_activity(today)

        title, sections = format_night_report(readiness, sleep, activity)

        print("Sending night report to Discord...")
        success = discord.send_health_report(title, sections)

        if success:
            print("Night report sent successfully!")
        else:
            print("Failed to send night report")

        return success

    except Exception as e:
        print(f"Error: {e}")
        try:
            discord.send_message(f":x: **夜通知エラー**\n```{str(e)}```")
        except Exception:
            pass
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
        print("Test message sent!" if success else "Failed to send test message")
        sys.exit(0 if success else 1)

    # 通知タイプに応じて実行
    if args.type == "morning":
        success = send_morning_report()
    elif args.type == "noon":
        success = send_noon_report()
    elif args.type == "night":
        success = send_night_report()
    else:
        print(f"Unknown notification type: {args.type}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
