"""Bot共通ユーティリティ"""

import os
import re
import discord
from datetime import date, timedelta, time
from zoneinfo import ZoneInfo
from typing import Optional

from oura_client import OuraClient
from settings import SettingsManager


JST = ZoneInfo("Asia/Tokyo")

# 共有インスタンス
settings = SettingsManager()

# OuraClient インスタンス（遅延初期化）
_oura_client: Optional[OuraClient] = None


def get_jst_now():
    """JSTの現在時刻を取得"""
    from datetime import datetime
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
