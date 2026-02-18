"""グラフ生成モジュール - matplotlib を使用"""

import io
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import List

config_dir = Path(__file__).parent.parent / "data" / ".matplotlib"
try:
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(config_dir))
except OSError:
    pass

import matplotlib  # noqa: E402

matplotlib.use('Agg')  # GUIバックエンドを使用しない
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def _get_japanese_font_families() -> list[str]:
    """OSに応じた日本語フォントファミリーのリストを返す"""
    system = platform.system()
    if system == "Darwin":
        return ["Hiragino Sans", "Hiragino Kaku Gothic ProN", "sans-serif"]
    elif system == "Linux":
        return ["Noto Sans CJK JP", "IPAGothic", "sans-serif"]
    elif system == "Windows":
        return ["Yu Gothic", "MS Gothic", "Meiryo", "sans-serif"]
    return ["sans-serif"]


# 日本語フォント設定（クロスプラットフォーム対応）
plt.rcParams['font.family'] = _get_japanese_font_families()
plt.rcParams['axes.unicode_minus'] = False


def generate_score_chart(
    daily_data: List[dict],
    title: str = "スコア推移",
    show_sleep: bool = True,
    show_readiness: bool = True,
    show_activity: bool = True,
) -> io.BytesIO:
    """
    スコア推移グラフを生成

    Args:
        daily_data: 日別データのリスト（date, sleep_score, readiness_score, activity_score）
        title: グラフタイトル
        show_sleep: 睡眠スコアを表示するか
        show_readiness: Readinessスコアを表示するか
        show_activity: 活動スコアを表示するか

    Returns:
        PNG画像のバイトストリーム
    """
    # データの準備
    dates = []
    sleep_scores = []
    readiness_scores = []
    activity_scores = []

    for day in daily_data:
        d = datetime.fromisoformat(day["date"])
        dates.append(d)
        sleep_scores.append(day.get("sleep_score"))
        readiness_scores.append(day.get("readiness_score"))
        activity_scores.append(day.get("activity_score"))

    # グラフ作成
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor('#2C2F33')  # Discordダークテーマに合わせる
    ax.set_facecolor('#2C2F33')

    # 各スコアをプロット
    if show_sleep:
        valid_dates = [d for d, s in zip(dates, sleep_scores) if s is not None]
        valid_scores = [s for s in sleep_scores if s is not None]
        if valid_scores:
            ax.plot(valid_dates, valid_scores, 'o-', color='#9B59B6', label='睡眠', linewidth=2, markersize=4)

    if show_readiness:
        valid_dates = [d for d, s in zip(dates, readiness_scores) if s is not None]
        valid_scores = [s for s in readiness_scores if s is not None]
        if valid_scores:
            ax.plot(valid_dates, valid_scores, 's-', color='#3498DB', label='Readiness', linewidth=2, markersize=4)

    if show_activity:
        valid_dates = [d for d, s in zip(dates, activity_scores) if s is not None]
        valid_scores = [s for s in activity_scores if s is not None]
        if valid_scores:
            ax.plot(valid_dates, valid_scores, '^-', color='#2ECC71', label='活動', linewidth=2, markersize=4)

    # 基準線
    ax.axhline(y=85, color='#27AE60', linestyle='--', alpha=0.5, linewidth=1)
    ax.axhline(y=70, color='#F39C12', linestyle='--', alpha=0.5, linewidth=1)

    # 軸の設定
    ax.set_ylim(40, 100)
    ax.set_ylabel('スコア', color='white', fontsize=12)
    ax.set_xlabel('日付', color='white', fontsize=12)
    ax.set_title(title, color='white', fontsize=14, fontweight='bold')

    # 目盛りの設定
    ax.tick_params(colors='white')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%-m/%-d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
    plt.xticks(rotation=45)

    # グリッド
    ax.grid(True, alpha=0.3, color='white')

    # 凡例
    ax.legend(loc='upper left', facecolor='#23272A', edgecolor='white', labelcolor='white')

    # 枠線の色
    for spine in ax.spines.values():
        spine.set_color('white')

    plt.tight_layout()

    # バイトストリームに保存
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)

    return buf


def generate_steps_chart(
    daily_data: List[dict],
    goal: int = 8000,
    title: str = "歩数推移",
) -> io.BytesIO:
    """
    歩数推移グラフを生成

    Args:
        daily_data: 日別データのリスト（date, steps）
        goal: 歩数目標
        title: グラフタイトル

    Returns:
        PNG画像のバイトストリーム
    """
    # データの準備
    dates = []
    steps_list = []

    for day in daily_data:
        d = datetime.fromisoformat(day["date"])
        dates.append(d)
        steps_list.append(day.get("steps"))

    # グラフ作成
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor('#2C2F33')
    ax.set_facecolor('#2C2F33')

    # 有効なデータのみ抽出
    valid_dates = [d for d, s in zip(dates, steps_list) if s is not None]
    valid_steps = [s for s in steps_list if s is not None]

    if valid_steps:
        # 目標達成/未達成で色分け
        colors = ['#2ECC71' if s >= goal else '#E74C3C' for s in valid_steps]
        ax.bar(valid_dates, valid_steps, color=colors, alpha=0.8, width=0.8)

        # 目標ライン
        ax.axhline(y=goal, color='#F39C12', linestyle='--', linewidth=2, label=f'目標: {goal:,}歩')

    # 軸の設定
    max_steps = max(valid_steps) if valid_steps else goal
    ax.set_ylim(0, max(max_steps * 1.1, goal * 1.2))
    ax.set_ylabel('歩数', color='white', fontsize=12)
    ax.set_xlabel('日付', color='white', fontsize=12)
    ax.set_title(title, color='white', fontsize=14, fontweight='bold')

    # 目盛りの設定
    ax.tick_params(colors='white')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%-m/%-d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
    plt.xticks(rotation=45)

    # Y軸のフォーマット（カンマ区切り）
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

    # グリッド
    ax.grid(True, alpha=0.3, color='white', axis='y')

    # 凡例
    ax.legend(loc='upper right', facecolor='#23272A', edgecolor='white', labelcolor='white')

    # 枠線の色
    for spine in ax.spines.values():
        spine.set_color('white')

    plt.tight_layout()

    # バイトストリームに保存
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)

    return buf


def generate_combined_chart(
    daily_data: List[dict],
    goal: int = 8000,
    title: str = "月間サマリー",
) -> io.BytesIO:
    """
    スコアと歩数を組み合わせたグラフを生成

    Args:
        daily_data: 日別データのリスト
        goal: 歩数目標
        title: グラフタイトル

    Returns:
        PNG画像のバイトストリーム
    """
    # データの準備
    dates = []
    sleep_scores = []
    readiness_scores = []
    steps_list = []

    for day in daily_data:
        d = datetime.fromisoformat(day["date"])
        dates.append(d)
        sleep_scores.append(day.get("sleep_score"))
        readiness_scores.append(day.get("readiness_score"))
        steps_list.append(day.get("steps"))

    # グラフ作成（2行構成）
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[1, 1])
    fig.patch.set_facecolor('#2C2F33')

    # === 上段: スコア推移 ===
    ax1.set_facecolor('#2C2F33')

    # 睡眠スコア
    valid_dates = [d for d, s in zip(dates, sleep_scores) if s is not None]
    valid_scores = [s for s in sleep_scores if s is not None]
    if valid_scores:
        ax1.plot(valid_dates, valid_scores, 'o-', color='#9B59B6', label='睡眠', linewidth=2, markersize=3)

    # Readinessスコア
    valid_dates = [d for d, s in zip(dates, readiness_scores) if s is not None]
    valid_scores = [s for s in readiness_scores if s is not None]
    if valid_scores:
        ax1.plot(valid_dates, valid_scores, 's-', color='#3498DB', label='Readiness', linewidth=2, markersize=3)

    ax1.axhline(y=85, color='#27AE60', linestyle='--', alpha=0.5, linewidth=1)
    ax1.axhline(y=70, color='#F39C12', linestyle='--', alpha=0.5, linewidth=1)
    ax1.set_ylim(40, 100)
    ax1.set_ylabel('スコア', color='white', fontsize=10)
    ax1.set_title(title, color='white', fontsize=14, fontweight='bold')
    ax1.tick_params(colors='white')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%-m/%-d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 8)))
    ax1.grid(True, alpha=0.3, color='white')
    ax1.legend(loc='upper left', facecolor='#23272A', edgecolor='white', labelcolor='white', fontsize=9)
    for spine in ax1.spines.values():
        spine.set_color('white')

    # === 下段: 歩数推移 ===
    ax2.set_facecolor('#2C2F33')

    valid_dates = [d for d, s in zip(dates, steps_list) if s is not None]
    valid_steps = [s for s in steps_list if s is not None]

    if valid_steps:
        colors = ['#2ECC71' if s >= goal else '#E74C3C' for s in valid_steps]
        ax2.bar(valid_dates, valid_steps, color=colors, alpha=0.8, width=0.8)
        ax2.axhline(y=goal, color='#F39C12', linestyle='--', linewidth=2, label=f'目標: {goal:,}歩')

    max_steps = max(valid_steps) if valid_steps else goal
    ax2.set_ylim(0, max(max_steps * 1.1, goal * 1.2))
    ax2.set_ylabel('歩数', color='white', fontsize=10)
    ax2.set_xlabel('日付', color='white', fontsize=10)
    ax2.tick_params(colors='white')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%-m/%-d'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 8)))
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    ax2.grid(True, alpha=0.3, color='white', axis='y')
    ax2.legend(loc='upper right', facecolor='#23272A', edgecolor='white', labelcolor='white', fontsize=9)
    for spine in ax2.spines.values():
        spine.set_color('white')

    plt.xticks(rotation=45)
    plt.tight_layout()

    # バイトストリームに保存
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)

    return buf
