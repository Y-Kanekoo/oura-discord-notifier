"""Message Formatter for Discord"""

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


def format_sleep_section(sleep_data: Optional[dict]) -> dict:
    """睡眠データをEmbed用セクションに変換"""
    if not sleep_data:
        return {
            "title": ":zzz: 睡眠",
            "description": "データがありません",
            "color": 0x808080,
        }

    score = sleep_data.get("score", 0)
    contributors = sleep_data.get("contributors", {})

    # 睡眠時間を計算（秒 → 時間:分）
    total_sleep = contributors.get("total_sleep", 0)
    deep_sleep = contributors.get("deep_sleep", 0)
    rem_sleep = contributors.get("rem_sleep", 0)

    description = f"**スコア: {score}** {get_score_emoji(score)} ({get_score_label(score)})"

    fields = []

    if total_sleep:
        fields.append({
            "name": ":bed: 総睡眠時間",
            "value": f"スコア: {total_sleep}",
            "inline": True,
        })

    if deep_sleep:
        fields.append({
            "name": ":new_moon: 深い睡眠",
            "value": f"スコア: {deep_sleep}",
            "inline": True,
        })

    if rem_sleep:
        fields.append({
            "name": ":crescent_moon: レム睡眠",
            "value": f"スコア: {rem_sleep}",
            "inline": True,
        })

    # スコアに応じた色
    if score >= 85:
        color = 0x00FF00  # 緑
    elif score >= 70:
        color = 0xFFFF00  # 黄
    else:
        color = 0xFF0000  # 赤

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

    # スコアに応じた色
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


def format_activity_section(activity_data: Optional[dict]) -> dict:
    """活動データをembed用セクションに変換"""
    if not activity_data:
        return {
            "title": ":runner: 活動",
            "description": "データがありません",
            "color": 0x808080,
        }

    score = activity_data.get("score", 0)
    steps = activity_data.get("steps", 0)
    active_calories = activity_data.get("active_calories", 0)
    total_calories = activity_data.get("total_calories", 0)

    description = f"**スコア: {score}** {get_score_emoji(score)} ({get_score_label(score)})"

    fields = [
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
            "name": ":hamburger: 総消費カロリー",
            "value": f"{total_calories:,} kcal",
            "inline": True,
        },
    ]

    # スコアに応じた色
    if score >= 85:
        color = 0x00FF00
    elif score >= 70:
        color = 0xFFFF00
    else:
        color = 0xFF0000

    return {
        "title": ":runner: 活動",
        "description": description,
        "fields": fields,
        "color": color,
    }


def format_daily_report(data: dict) -> tuple[str, list[dict]]:
    """1日分のレポートをフォーマット"""
    date_str = data.get("date", "不明")

    title = f":sunrise: **おはようございます！** ({date_str})"

    sections = [
        format_sleep_section(data.get("sleep")),
        format_readiness_section(data.get("readiness")),
        format_activity_section(data.get("activity")),
    ]

    return title, sections


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
