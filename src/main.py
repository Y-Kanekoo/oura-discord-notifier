"""Oura Ring to Discord Notifier - Main Entry Point"""

import os
import sys
from datetime import date
from pathlib import Path

# .envファイルの読み込み（存在する場合のみ）
try:
    from dotenv import load_dotenv
    # srcディレクトリの親ディレクトリにある.envを探す
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
except ImportError:
    pass  # dotenvがない場合はスキップ（GitHub Actionsでは不要）

from oura_client import OuraClient
from discord_client import DiscordClient
from formatter import format_daily_report, format_alert_message


def get_env_var(name: str) -> str:
    """環境変数を取得（必須）"""
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable is not set")
        sys.exit(1)
    return value


def send_daily_report(target_date: date | None = None) -> bool:
    """毎日のレポートを送信"""
    # 環境変数から認証情報を取得
    oura_token = get_env_var("OURA_ACCESS_TOKEN")
    discord_webhook = get_env_var("DISCORD_WEBHOOK_URL")

    # クライアントを初期化
    oura = OuraClient(oura_token)
    discord = DiscordClient(discord_webhook)

    try:
        # Ouraからデータを取得
        print(f"Fetching data for {target_date or 'yesterday'}...")
        data = oura.get_all_daily_data(target_date)

        # レポートをフォーマット
        title, sections = format_daily_report(data)

        # Discordに送信
        print("Sending report to Discord...")
        success = discord.send_health_report(title, sections)

        if success:
            print("Report sent successfully!")

            # 警告があれば追加で送信
            alert = format_alert_message(data)
            if alert:
                print("Sending alert message...")
                discord.send_message(alert)
        else:
            print("Failed to send report")

        return success

    except Exception as e:
        print(f"Error: {e}")
        # エラーをDiscordにも通知
        try:
            discord.send_message(f":x: **エラーが発生しました**\n```{str(e)}```")
        except Exception:
            pass
        return False


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Oura Ring to Discord Notifier")
    parser.add_argument(
        "--date",
        type=str,
        help="Target date (YYYY-MM-DD format). Defaults to yesterday.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test message to verify configuration",
    )

    args = parser.parse_args()

    if args.test:
        # テストモード
        discord_webhook = get_env_var("DISCORD_WEBHOOK_URL")
        discord = DiscordClient(discord_webhook)
        success = discord.send_message(":white_check_mark: **テスト成功！** Oura Discord Notifierが正常に動作しています。")
        if success:
            print("Test message sent successfully!")
        else:
            print("Failed to send test message")
        sys.exit(0 if success else 1)

    # 日付を解析
    target_date = None
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Error: Invalid date format: {args.date}")
            print("Use YYYY-MM-DD format (e.g., 2024-01-15)")
            sys.exit(1)

    # レポートを送信
    success = send_daily_report(target_date)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
