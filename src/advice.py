"""アドバイス生成モジュール - データに基づく推奨行動"""

from typing import Optional


def generate_advice(
    readiness_score: Optional[int] = None,
    sleep_score: Optional[int] = None,
    activity_score: Optional[int] = None,
    steps: Optional[int] = None,
    steps_goal: int = 8000,
) -> str:
    """
    健康データに基づいてアドバイスを生成

    Args:
        readiness_score: Readinessスコア (0-100)
        sleep_score: 睡眠スコア (0-100)
        activity_score: 活動スコア (0-100)
        steps: 現在の歩数
        steps_goal: 歩数目標

    Returns:
        str: Discordメッセージ用のアドバイステキスト
    """
    advice_parts = []

    # Readiness ベースのアドバイス（最重要）
    if readiness_score is not None:
        if readiness_score >= 85:
            advice_parts.append(
                ":fire: **コンディション絶好調！**\n"
                "今日は積極的に活動しても大丈夫です。\n"
                "運動や重要なタスクに最適な日。"
            )
        elif readiness_score >= 70:
            advice_parts.append(
                ":thumbsup: **コンディション良好**\n"
                "いつも通りのペースで過ごしましょう。\n"
                "適度な活動とバランスの取れた一日を。"
            )
        elif readiness_score >= 60:
            advice_parts.append(
                ":warning: **やや疲れ気味**\n"
                "今日は無理せず、適度に休息を取りましょう。\n"
                "激しい運動は避けて。"
            )
        else:
            advice_parts.append(
                ":battery: **回復を優先しましょう**\n"
                "今日は休息日にすることをお勧めします。\n"
                "早めの就寝と水分補給を心がけて。"
            )

    # 睡眠スコアベースのアドバイス
    if sleep_score is not None:
        if sleep_score < 60:
            advice_parts.append(
                ":zzz: **睡眠が不足しています**\n"
                "今夜は早めに就寝しましょう（目標: 22:30）\n"
                "カフェインは14時以降控えめに。"
            )
        elif sleep_score < 70:
            advice_parts.append(
                ":bed: **睡眠スコアが低めです**\n"
                "今夜は普段より30分早く寝ることを推奨。\n"
                "就寝前のスマホ使用を控えましょう。"
            )

    # 歩数ベースのアドバイス
    if steps is not None and steps_goal > 0:
        progress = steps / steps_goal
        remaining = steps_goal - steps

        if progress >= 1.0:
            advice_parts.append(
                f":star2: **歩数目標達成！**\n"
                f"素晴らしい！{steps:,} 歩歩きました。\n"
                f"この調子を維持しましょう。"
            )
        elif progress >= 0.7:
            advice_parts.append(
                f":walking: **歩数目標まであと少し**\n"
                f"あと {remaining:,} 歩で達成！\n"
                f"夕方の散歩で達成できそうです。"
            )
        elif progress < 0.3:
            advice_parts.append(
                f":footprints: **歩数が少なめです**\n"
                f"現在 {steps:,} 歩 / 目標 {steps_goal:,} 歩\n"
                f"階段を使う・一駅歩くなど工夫を。"
            )

    # 活動スコアベースのアドバイス
    if activity_score is not None:
        if activity_score >= 85:
            advice_parts.append(
                ":muscle: **活動量が十分です**\n"
                "今日の運動は順調！休息も大切に。"
            )
        elif activity_score < 50 and (steps is None or (steps_goal > 0 and steps / steps_goal < 0.5)):
            advice_parts.append(
                ":couch_and_lamp: **活動量が少なめ**\n"
                "デスクワークが多い日？\n"
                "1時間に1回は立ち上がりましょう。"
            )

    # アドバイスがない場合のデフォルト
    if not advice_parts:
        advice_parts.append(
            ":sparkles: **特に問題なし**\n"
            "今日も健康的に過ごしていますね！\n"
            "この調子で良いバランスを維持しましょう。"
        )

    return "\n\n".join(advice_parts)


def get_quick_tip(readiness_score: Optional[int] = None) -> str:
    """簡易アドバイス（一言）を生成"""
    if readiness_score is None:
        return "今日も良い一日を！"

    if readiness_score >= 85:
        return "絶好調！今日は攻めの一日に。"
    elif readiness_score >= 70:
        return "良好です。バランスの取れた一日を。"
    elif readiness_score >= 60:
        return "少し疲れ気味。無理せずに。"
    else:
        return "回復優先。早めに休みましょう。"
