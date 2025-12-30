"""Message Formatter for Discord - 朝・昼・夜の通知対応"""

from datetime import datetime
from typing import Optional


def get_score_emoji(score: int) -> str:
    """スコアに応じた絵文字を返す"""
    if score >= 85:
        return ":green_circle:"
    elif score >= 70:
        return ":yellow_circle:"
    else:
        return ":red_circle:"


def get_score_label(score: int) -> str:
    """スコアに応じたラベルを返す"""
    if score >= 85:
        return "優秀"
    elif score >= 70:
        return "良好"
    elif score >= 60:
        return "まずまず"
    else:
        return "要注意"


def format_duration(seconds: int) -> str:
    """秒を「X時間Y分」形式に変換"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}時間{minutes}分"
    else:
        return f"{minutes}分"


def get_today_policy(readiness_score: int) -> tuple[str, str, int]:
    """今日の方針を決定する"""
    if readiness_score >= 85:
        return (
            ":fire: 攻める",
            "コンディション良好！今日は積極的に動こう",
            0x00FF00,  # 緑
        )
    elif readiness_score >= 70:
        return (
            ":arrows_counterclockwise: 維持",
            "いつも通りのペースで過ごそう",
            0xFFFF00,  # 黄
        )
    else:
        return (
            ":battery: 回復",
            "無理せず休息を優先しよう",
            0xFF0000,  # 赤
        )


# =============================================================================
# 朝通知用フォーマッター
# =============================================================================

def format_time_from_iso(iso_string: str) -> str:
    """ISO形式の時刻から HH:MM 形式を取得"""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except (ValueError, AttributeError):
        return "不明"


def format_sleep_section(sleep_data: Optional[dict], sleep_details: Optional[dict] = None) -> dict:
    """睡眠データをEmbed用セクションに変換"""
    if not sleep_data:
        return {
            "title": ":zzz: 睡眠",
            "description": "データがありません",
            "color": 0x808080,
        }

    score = sleep_data.get("score", 0)
    description = f"**スコア: {score}** {get_score_emoji(score)} ({get_score_label(score)})"
    fields = []

    # 詳細データがある場合は実際の睡眠時間を表示
    if sleep_details:
        # 就寝・起床時刻
        bedtime_start = sleep_details.get("bedtime_start")
        bedtime_end = sleep_details.get("bedtime_end")

        if bedtime_start and bedtime_end:
            start_time = format_time_from_iso(bedtime_start)
            end_time = format_time_from_iso(bedtime_end)
            fields.append({
                "name": ":clock10: 就寝 → 起床",
                "value": f"{start_time} → {end_time}",
                "inline": True,
            })

        total_sleep_duration = sleep_details.get("total_sleep_duration")
        deep_sleep_duration = sleep_details.get("deep_sleep_duration")
        rem_sleep_duration = sleep_details.get("rem_sleep_duration")
        lowest_heart_rate = sleep_details.get("lowest_heart_rate")
        average_hrv = sleep_details.get("average_hrv")

        if total_sleep_duration:
            fields.append({
                "name": ":bed: 総睡眠時間",
                "value": format_duration(total_sleep_duration),
                "inline": True,
            })

        if deep_sleep_duration:
            fields.append({
                "name": ":new_moon: 深い睡眠",
                "value": format_duration(deep_sleep_duration),
                "inline": True,
            })

        if rem_sleep_duration:
            fields.append({
                "name": ":crescent_moon: レム睡眠",
                "value": format_duration(rem_sleep_duration),
                "inline": True,
            })

        if lowest_heart_rate:
            fields.append({
                "name": ":heart: 最低心拍数",
                "value": f"{lowest_heart_rate} bpm",
                "inline": True,
            })

        if average_hrv:
            fields.append({
                "name": ":chart_with_upwards_trend: 平均HRV",
                "value": f"{average_hrv:.0f} ms",
                "inline": True,
            })

    # スコアに応じた色
    if score >= 85:
        color = 0x00FF00
    elif score >= 70:
        color = 0xFFFF00
    else:
        color = 0xFF0000

    return {
        "title": ":zzz: 睡眠",
        "description": description,
        "fields": fields,
        "color": color,
    }


def format_readiness_section(readiness_data: Optional[dict]) -> dict:
    """Readinessデータをembed用セクションに変換"""
    if not readiness_data:
        return {
            "title": ":zap: Readiness（準備度）",
            "description": "データがありません",
            "color": 0x808080,
        }

    score = readiness_data.get("score", 0)
    contributors = readiness_data.get("contributors", {})
    description = f"**スコア: {score}** {get_score_emoji(score)} ({get_score_label(score)})"
    fields = []

    recovery_index = contributors.get("recovery_index")
    if recovery_index:
        fields.append({
            "name": ":heartpulse: 回復度",
            "value": f"スコア: {recovery_index}",
            "inline": True,
        })

    resting_hr = contributors.get("resting_heart_rate")
    if resting_hr:
        fields.append({
            "name": ":heart: 安静時心拍",
            "value": f"スコア: {resting_hr}",
            "inline": True,
        })

    hrv_balance = contributors.get("hrv_balance")
    if hrv_balance:
        fields.append({
            "name": ":chart_with_upwards_trend: HRVバランス",
            "value": f"スコア: {hrv_balance}",
            "inline": True,
        })

    if score >= 85:
        color = 0x00FF00
    elif score >= 70:
        color = 0xFFFF00
    else:
        color = 0xFF0000

    return {
        "title": ":zap: Readiness（準備度）",
        "description": description,
        "fields": fields,
        "color": color,
    }


def format_policy_section(readiness_score: int) -> dict:
    """今日の方針セクションを生成"""
    policy, message, color = get_today_policy(readiness_score)

    return {
        "title": f":dart: 今日の方針: {policy}",
        "description": message,
        "color": color,
    }


def format_morning_report(data: dict) -> tuple[str, list[dict]]:
    """朝通知：睡眠 + Readiness + 今日の方針（活動なし）"""
    date_str = data.get("date", "不明")
    title = f":sunrise: **おはようございます！** ({date_str})"

    readiness = data.get("readiness")
    readiness_score = readiness.get("score", 70) if readiness else 70

    sections = [
        format_sleep_section(data.get("sleep"), data.get("sleep_details")),
        format_readiness_section(readiness),
        format_policy_section(readiness_score),
    ]

    return title, sections


# =============================================================================
# 昼通知用フォーマッター
# =============================================================================

def format_noon_report(
    activity_data: Optional[dict],
    steps_goal: int,
    current_hour: int = 13,
) -> tuple[str, list[dict], bool]:
    """
    昼通知：活動進捗（条件付き）

    Returns:
        tuple: (タイトル, セクション, 送信すべきか)
    """
    if not activity_data:
        return "", [], False

    steps = activity_data.get("steps", 0)

    # 13時時点での目標ペースを計算
    # 活動時間を8:00-23:00（15時間）と仮定
    # 13:00は活動開始から5時間 = 5/15 = 33%
    active_hours = 15  # 8:00-23:00
    hours_since_start = current_hour - 8  # 8時起点
    if hours_since_start < 0:
        hours_since_start = 0

    expected_progress = hours_since_start / active_hours
    expected_steps = int(steps_goal * expected_progress)

    # 目標ペースの70%未満なら通知（30%以上遅れ）
    threshold = expected_steps * 0.7
    should_send = steps < threshold

    if not should_send:
        return "", [], False

    # 進捗率を計算
    progress_percent = (steps / steps_goal * 100) if steps_goal > 0 else 0
    remaining_steps = max(0, steps_goal - steps)

    title = ":walking: **活動リマインダー**"

    # 進捗バーを生成
    bar_length = 10
    filled = int(progress_percent / 10)
    bar = "█" * filled + "░" * (bar_length - filled)

    sections = [
        {
            "title": ":footprints: 歩数の進捗",
            "description": f"**{steps:,} / {steps_goal:,} 歩** ({progress_percent:.0f}%)\n`{bar}`",
            "color": 0xFF9900,  # オレンジ
            "fields": [
                {
                    "name": ":chart_with_downwards_trend: 目標ペース",
                    "value": f"{expected_steps:,} 歩",
                    "inline": True,
                },
                {
                    "name": ":warning: 差分",
                    "value": f"-{expected_steps - steps:,} 歩",
                    "inline": True,
                },
                {
                    "name": ":bulb: 今すぐできること",
                    "value": "10分歩く（約1,000歩）",
                    "inline": False,
                },
            ],
        },
    ]

    return title, sections, should_send


# =============================================================================
# 夜通知用フォーマッター
# =============================================================================

def format_night_report(
    readiness_data: Optional[dict],
    sleep_data: Optional[dict],
    activity_data: Optional[dict] = None,
) -> tuple[str, list[dict]]:
    """
    夜通知：今日の結果 + 減速リマインダー（データ連動）

    Returns:
        tuple: (タイトル, セクションリスト)
    """
    readiness_score = readiness_data.get("score", 70) if readiness_data else 70
    sleep_score = sleep_data.get("score", 70) if sleep_data else 70

    title = ":night_with_stars: **おつかれさまでした！**"

    sections = []

    # 今日の結果セクション
    if activity_data:
        steps = activity_data.get("steps", 0)
        active_calories = activity_data.get("active_calories", 0)
        activity_score = activity_data.get("score", 0)

        sections.append({
            "title": ":bar_chart: 今日の結果",
            "description": f"**活動スコア: {activity_score}** {get_score_emoji(activity_score)}",
            "color": 0x3498DB,  # 青
            "fields": [
                {
                    "name": ":footprints: 歩数",
                    "value": f"{steps:,} 歩",
                    "inline": True,
                },
                {
                    "name": ":fire: アクティブカロリー",
                    "value": f"{active_calories:,} kcal",
                    "inline": True,
                },
                {
                    "name": ":zap: Readiness",
                    "value": f"{readiness_score}",
                    "inline": True,
                },
            ],
        })

    # 減速リマインダーセクション
    if readiness_score < 70 or sleep_score < 70:
        reminder_desc = (
            ":warning: **今日は早めに就寝を推奨**\n"
            f"└ Readiness: {readiness_score} / 昨夜の睡眠: {sleep_score}\n\n"
            ":moon: **今すぐやること**\n"
            "1. スマホ・PCをオフ\n"
            "2. 照明を暗くする\n"
            "3. 目標就寝: **24:00**"
        )
        reminder_color = 0xFF6B6B  # 赤っぽい
    else:
        reminder_desc = (
            ":sparkles: コンディション良好です\n\n"
            ":moon: **減速開始のルーティン**\n"
            "1. スマホ・PCをオフ\n"
            "2. 照明を暗くする\n"
            "3. リラックスタイム"
        )
        reminder_color = 0x9B59B6  # 紫

    sections.append({
        "title": ":bed: 減速開始（就寝90分前）",
        "description": reminder_desc,
        "color": reminder_color,
    })

    return title, sections


# =============================================================================
# 後方互換性のための関数
# =============================================================================

def format_daily_report(data: dict) -> tuple[str, list[dict]]:
    """後方互換性：format_morning_reportのエイリアス"""
    return format_morning_report(data)


def format_alert_message(data: dict) -> Optional[str]:
    """警告メッセージを生成（低スコアの場合のみ）"""
    alerts = []

    sleep = data.get("sleep")
    if sleep and sleep.get("score", 100) < 70:
        alerts.append(f":warning: 睡眠スコアが低めです（{sleep['score']}）。今日は早めに休みましょう。")

    readiness = data.get("readiness")
    if readiness and readiness.get("score", 100) < 65:
        alerts.append(f":warning: Readinessが低めです（{readiness['score']}）。無理せず過ごしましょう。")

    if alerts:
        return "\n".join(alerts)
    return None
