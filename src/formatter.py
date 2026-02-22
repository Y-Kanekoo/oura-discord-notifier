"""Message Formatter for Discord - 朝・昼・夜の通知対応"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


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


def get_comparison_emoji(current: int, previous: int, threshold: int = 3) -> str:
    """前日比較の絵文字を返す"""
    diff = current - previous
    if diff > threshold:
        return ":arrow_up:"
    elif diff < -threshold:
        return ":arrow_down:"
    else:
        return ":arrow_right:"


def format_comparison(current: int, previous: Optional[int], label: str = "") -> str:
    """前日比較の文字列を生成"""
    if previous is None:
        return ""
    diff = current - previous
    emoji = get_comparison_emoji(current, previous)
    sign = "+" if diff > 0 else ""
    return f" {emoji} ({sign}{diff})"


def format_weekly_trend(current: int, weekly_avg: Optional[float]) -> str:
    """週間平均との比較文字列を生成"""
    if weekly_avg is None:
        return ""
    diff = current - weekly_avg
    if diff > 5:
        trend = ":chart_with_upwards_trend: 週平均より高め"
    elif diff < -5:
        trend = ":chart_with_downwards_trend: 週平均より低め"
    else:
        trend = ":left_right_arrow: 週平均並み"
    return f"\n{trend}（平均: {weekly_avg:.0f}）"


def calculate_target_bedtime(
    target_wake_time: str = "07:00",
    sleep_hours: float = 7.5,
    wind_down_minutes: int = 30,
) -> str:
    """
    目標就寝時刻を計算

    Args:
        target_wake_time: 目標起床時刻（HH:MM形式）
        sleep_hours: 目標睡眠時間（時間）
        wind_down_minutes: 入眠までの時間（分）

    Returns:
        目標就寝時刻（HH:MM形式）
    """
    try:
        wake_hour, wake_min = map(int, target_wake_time.split(":"))
        total_minutes = wake_hour * 60 + wake_min

        # 睡眠時間と入眠時間を引く
        sleep_minutes = int(sleep_hours * 60)
        bedtime_minutes = total_minutes - sleep_minutes - wind_down_minutes

        # 24時間を超える場合は前日として計算
        if bedtime_minutes < 0:
            bedtime_minutes += 24 * 60

        bed_hour = bedtime_minutes // 60
        bed_min = bedtime_minutes % 60

        return f"{bed_hour:02d}:{bed_min:02d}"
    except (ValueError, AttributeError):
        return "23:00"


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
        if dt.tzinfo is None:
            return dt.strftime("%H:%M")
        return dt.astimezone(JST).strftime("%H:%M")
    except (ValueError, AttributeError):
        return "不明"


def format_sleep_section(
    sleep_data: Optional[dict],
    sleep_details: Optional[dict] = None,
    prev_sleep: Optional[dict] = None,
    weekly_avg_sleep: Optional[float] = None,
) -> dict:
    """睡眠データをEmbed用セクションに変換"""
    if not sleep_data:
        return {
            "title": ":zzz: 睡眠",
            "description": "データがありません",
            "color": 0x808080,
        }

    score = sleep_data.get("score", 0)
    prev_score = prev_sleep.get("score") if prev_sleep else None
    sleep_date = sleep_data.get("day", "")
    date_label = ""
    if sleep_date:
        try:
            dt = datetime.fromisoformat(sleep_date)
            date_label = f" ({dt.month}/{dt.day})"
        except (ValueError, AttributeError):
            pass

    # 前日比較を追加
    comparison = format_comparison(score, prev_score) if prev_score is not None else ""
    description = f"**スコア: {score}** {get_score_emoji(score)} ({get_score_label(score)}){comparison}"

    # 週間トレンドを追加
    if weekly_avg_sleep is not None:
        description += format_weekly_trend(score, weekly_avg_sleep)
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

        light_sleep_duration = sleep_details.get("light_sleep_duration")
        if light_sleep_duration:
            fields.append({
                "name": ":last_quarter_moon: 浅い睡眠",
                "value": format_duration(light_sleep_duration),
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

        # 睡眠効率を計算
        time_in_bed = sleep_details.get("time_in_bed")
        if total_sleep_duration and time_in_bed and time_in_bed > 0:
            efficiency = (total_sleep_duration / time_in_bed) * 100
            efficiency_emoji = ":star:" if efficiency >= 85 else ":ok:" if efficiency >= 75 else ":warning:"
            fields.append({
                "name": f"{efficiency_emoji} 睡眠効率",
                "value": f"{efficiency:.0f}%",
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
        "title": f":zzz: 睡眠{date_label}",
        "description": description,
        "fields": fields,
        "color": color,
    }


def format_readiness_section(
    readiness_data: Optional[dict],
    prev_readiness: Optional[dict] = None,
    weekly_avg_readiness: Optional[float] = None,
) -> dict:
    """Readinessデータをembed用セクションに変換"""
    if not readiness_data:
        return {
            "title": ":zap: Readiness（準備度）",
            "description": "データがありません",
            "color": 0x808080,
        }

    score = readiness_data.get("score", 0)
    prev_score = prev_readiness.get("score") if prev_readiness else None
    contributors = readiness_data.get("contributors", {})

    # 前日比較を追加
    comparison = format_comparison(score, prev_score) if prev_score is not None else ""
    description = f"**スコア: {score}** {get_score_emoji(score)} ({get_score_label(score)}){comparison}"

    # 週間トレンドを追加
    if weekly_avg_readiness is not None:
        description += format_weekly_trend(score, weekly_avg_readiness)
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


def format_morning_report(
    data: dict,
    prev_data: Optional[dict] = None,
    weekly_averages: Optional[dict] = None,
) -> tuple[str, list[dict]]:
    """朝通知：睡眠 + Readiness + 今日の方針（活動なし）"""
    date_str = data.get("date", "不明")
    title = f":sunrise: **おはようございます！** ({date_str})"

    readiness = data.get("readiness")
    readiness_score = readiness.get("score", 70) if readiness else 70

    # 前日データを取得
    prev_sleep = prev_data.get("sleep") if prev_data else None
    prev_readiness = prev_data.get("readiness") if prev_data else None

    # 週間平均を取得
    weekly_avg_sleep = weekly_averages.get("sleep") if weekly_averages else None
    weekly_avg_readiness = weekly_averages.get("readiness") if weekly_averages else None

    sections = [
        format_sleep_section(
            data.get("sleep"),
            data.get("sleep_details"),
            prev_sleep,
            weekly_avg_sleep,
        ),
        format_readiness_section(
            readiness,
            prev_readiness,
            weekly_avg_readiness,
        ),
        format_policy_section(readiness_score),
    ]

    return title, sections


# =============================================================================
# 昼通知用フォーマッター
# =============================================================================

def format_date_jp(date_str: str) -> str:
    """日付文字列を日本語形式に変換（例: 2024-12-31 → 12/31）"""
    try:
        dt = datetime.fromisoformat(date_str)
        return f"{dt.month}/{dt.day}"
    except (ValueError, AttributeError):
        return date_str


def format_sleep_summary_section(sleep_data: Optional[dict], sleep_details: Optional[dict] = None) -> Optional[dict]:
    """睡眠サマリー（昼通知用の簡易版）"""
    if not sleep_data:
        return None

    score = sleep_data.get("score", 0)
    sleep_date = sleep_data.get("day", "")
    date_str = f" ({format_date_jp(sleep_date)})" if sleep_date else ""

    # 睡眠時間を取得
    sleep_time_str = ""
    time_range = ""
    if sleep_details:
        total_sleep = sleep_details.get("total_sleep_duration")
        if total_sleep:
            sleep_time_str = f" / {format_duration(total_sleep)}"

        bedtime_start = sleep_details.get("bedtime_start")
        bedtime_end = sleep_details.get("bedtime_end")
        if bedtime_start and bedtime_end:
            start_time = format_time_from_iso(bedtime_start)
            end_time = format_time_from_iso(bedtime_end)
            time_range = f"\n:clock10: {start_time} → {end_time}"

    description = f"**スコア: {score}** {get_score_emoji(score)}{sleep_time_str}"
    if time_range:
        description += time_range

    if score >= 85:
        color = 0x00FF00
    elif score >= 70:
        color = 0xFFFF00
    else:
        color = 0xFF0000

    return {
        "title": f":zzz: 今朝の睡眠{date_str}",
        "description": description,
        "color": color,
    }


def format_noon_report(
    activity_data: Optional[dict],
    steps_goal: int,
    current_hour: int = 13,
    sleep_data: Optional[dict] = None,
    sleep_details: Optional[dict] = None,
) -> tuple[str, list[dict], bool]:
    """
    昼通知：活動進捗 + 睡眠サマリー（条件付き）

    Returns:
        tuple: (タイトル, セクション, 送信すべきか)
    """
    sections = []
    should_send = False

    # 睡眠データがあれば追加（朝に取れなかった場合の補完）
    sleep_section = format_sleep_summary_section(sleep_data, sleep_details)
    if sleep_section:
        sections.append(sleep_section)
        should_send = True  # 睡眠データがあれば通知

    # 活動データのチェック
    if activity_data:
        steps = activity_data.get("steps", 0)

        # 13時時点での目標ペースを計算
        # 活動時間を8:00-23:00（15時間）と仮定
        # 13:00は活動開始から5時間 = 5/15 = 33%
        active_hours = 15  # 8:00-23:00
        hours_since_start = current_hour - 8  # 8時起点
        if hours_since_start < 0:
            hours_since_start = 0
        elif hours_since_start > active_hours:
            hours_since_start = active_hours

        expected_progress = hours_since_start / active_hours
        expected_steps = int(steps_goal * expected_progress)

        # 目標ペースの70%未満なら通知（30%以上遅れ）
        threshold = expected_steps * 0.7
        activity_behind = steps < threshold

        if activity_behind:
            should_send = True

            # 進捗率を計算
            progress_percent = (steps / steps_goal * 100) if steps_goal > 0 else 0

            # 進捗バーを生成
            bar_length = 10
            filled = int(progress_percent / 10)
            bar = "█" * filled + "░" * (bar_length - filled)

            sections.append({
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
            })

    if not should_send:
        return "", [], False

    # タイトルを決定
    if sleep_section and len(sections) == 1:
        title = ":sun_with_face: **昼のチェックイン**"
    else:
        title = ":walking: **昼のチェックイン**"

    return title, sections, should_send


# =============================================================================
# 夜通知用フォーマッター
# =============================================================================

def format_night_report(
    readiness_data: Optional[dict],
    sleep_data: Optional[dict],
    activity_data: Optional[dict] = None,
    prev_activity: Optional[dict] = None,
    weekly_averages: Optional[dict] = None,
    target_wake_time: str = "07:00",
) -> tuple[str, list[dict]]:
    """
    夜通知：今日の結果 + 減速リマインダー（データ連動）

    Args:
        target_wake_time: 目標起床時刻（HH:MM形式）

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

        # 前日比較
        prev_activity_score = prev_activity.get("score") if prev_activity else None
        comparison = format_comparison(activity_score, prev_activity_score) if prev_activity_score else ""

        # 週間トレンド
        weekly_avg_activity = weekly_averages.get("activity") if weekly_averages else None
        trend = ""
        if weekly_avg_activity is not None:
            trend = format_weekly_trend(activity_score, weekly_avg_activity)

        sections.append({
            "title": ":bar_chart: 今日の結果",
            "description": f"**活動スコア: {activity_score}** {get_score_emoji(activity_score)}{comparison}{trend}",
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

    # 目標就寝時刻を計算
    target_bedtime = calculate_target_bedtime(target_wake_time, sleep_hours=7.5)

    # 減速リマインダーセクション
    if readiness_score < 70 or sleep_score < 70:
        # 疲れている時は早めに（+30分早く）
        early_bedtime = calculate_target_bedtime(target_wake_time, sleep_hours=8.0)
        reminder_desc = (
            ":warning: **今日は早めに就寝を推奨**\n"
            f"Readiness: {readiness_score} / 昨夜の睡眠: {sleep_score}\n\n"
            "**:crescent_moon: 今すぐやること**\n"
            ":one: スマホ・PCをオフ\n"
            ":two: 照明を暗くする\n"
            f":three: 目標就寝: **{early_bedtime}**（8時間睡眠）"
        )
        reminder_color = 0xFF6B6B  # 赤っぽい
    else:
        reminder_desc = (
            ":sparkles: コンディション良好です\n\n"
            "**:crescent_moon: 減速開始のルーティン**\n"
            ":one: スマホ・PCをオフ\n"
            ":two: 照明を暗くする\n"
            f":three: 目標就寝: **{target_bedtime}**（7.5時間睡眠）"
        )
        reminder_color = 0x9B59B6  # 紫

    sections.append({
        "title": ":bed: 減速開始（就寝90分前）",
        "description": reminder_desc,
        "color": reminder_color,
    })

    return title, sections


