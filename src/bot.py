"""Discord Bot - 会話型インターフェース（エントリーポイント）"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands

# .envファイルの読み込み
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


logger = logging.getLogger(__name__)

# Cog一覧
COG_EXTENSIONS = [
    "cogs.health",
    "cogs.report",
    "cogs.settings_cog",
    "cogs.general",
    "cogs.scheduler",
]


def create_bot() -> commands.Bot:
    """Botインスタンスを作成"""
    intents = discord.Intents.default()
    intents.message_content = True  # 自然言語対応に必要
    return commands.Bot(command_prefix="!", intents=intents)


bot = create_bot()


@bot.event
async def on_ready():
    """Bot起動時"""
    logger.info("Bot起動完了: %s", bot.user)

    # スラッシュコマンドを同期
    try:
        synced = await bot.tree.sync()
        logger.info("スラッシュコマンド %d 個を同期しました", len(synced))
    except Exception as e:
        logger.error("コマンド同期エラー: %s", e)


async def load_extensions():
    """全Cogを読み込み（失敗時はBot起動を中断）"""
    failed = []
    for ext in COG_EXTENSIONS:
        try:
            await bot.load_extension(ext)
            logger.info("Cog '%s' を読み込みました", ext)
        except Exception:
            logger.error("Cog '%s' の読み込みに失敗しました", ext, exc_info=True)
            failed.append(ext)
    if failed:
        raise RuntimeError(f"必須Cogの読み込みに失敗しました: {', '.join(failed)}")


def main():
    """Botを起動"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("エラー: DISCORD_BOT_TOKEN が設定されていません")
        print("Discord Developer Portal でボットトークンを取得し、")
        print(".env ファイルに DISCORD_BOT_TOKEN=xxx を設定してください")
        sys.exit(1)

    async def runner():
        async with bot:
            await load_extensions()
            await bot.start(token)

    print("Discord Bot を起動中...")
    asyncio.run(runner())


if __name__ == "__main__":
    main()
