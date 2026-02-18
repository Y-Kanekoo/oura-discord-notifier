"""formatter.py のユニットテスト"""

from formatter import (
    calculate_target_bedtime,
    format_comparison,
    format_duration,
    format_morning_report,
    format_night_report,
    format_noon_report,
    format_readiness_section,
    format_sleep_section,
    format_time_from_iso,
    format_weekly_trend,
    get_comparison_emoji,
    get_score_emoji,
    get_score_label,
    get_today_policy,
)


class TestGetScoreEmoji:
    def test_high_score(self):
        assert get_score_emoji(85) == ":green_circle:"
        assert get_score_emoji(100) == ":green_circle:"

    def test_medium_score(self):
        assert get_score_emoji(70) == ":yellow_circle:"
        assert get_score_emoji(84) == ":yellow_circle:"

    def test_low_score(self):
        assert get_score_emoji(69) == ":red_circle:"
        assert get_score_emoji(0) == ":red_circle:"


class TestGetScoreLabel:
    def test_excellent(self):
        assert get_score_label(85) == "優秀"
        assert get_score_label(100) == "優秀"

    def test_good(self):
        assert get_score_label(70) == "良好"
        assert get_score_label(84) == "良好"

    def test_fair(self):
        assert get_score_label(60) == "まずまず"
        assert get_score_label(69) == "まずまず"

    def test_warning(self):
        assert get_score_label(59) == "要注意"
        assert get_score_label(0) == "要注意"


class TestGetComparisonEmoji:
    def test_up(self):
        assert get_comparison_emoji(80, 70) == ":arrow_up:"

    def test_down(self):
        assert get_comparison_emoji(70, 80) == ":arrow_down:"

    def test_stable(self):
        assert get_comparison_emoji(80, 78) == ":arrow_right:"

    def test_threshold_boundary(self):
        # diff=3 はしきい値ちょうど → 安定
        assert get_comparison_emoji(73, 70) == ":arrow_right:"
        # diff=4 はしきい値超え → 上昇
        assert get_comparison_emoji(74, 70) == ":arrow_up:"


class TestFormatComparison:
    def test_with_previous(self):
        result = format_comparison(80, 75)
        assert "+5" in result

    def test_with_negative_diff(self):
        result = format_comparison(70, 80)
        assert "-10" in result

    def test_none_previous(self):
        assert format_comparison(80, None) == ""


class TestFormatWeeklyTrend:
    def test_above_average(self):
        result = format_weekly_trend(90, 80.0)
        assert "週平均より高め" in result
        assert "80" in result

    def test_below_average(self):
        result = format_weekly_trend(70, 80.0)
        assert "週平均より低め" in result

    def test_around_average(self):
        result = format_weekly_trend(80, 78.0)
        assert "週平均並み" in result

    def test_none_average(self):
        assert format_weekly_trend(80, None) == ""


class TestFormatDuration:
    def test_hours_and_minutes(self):
        assert format_duration(3600) == "1時間0分"
        assert format_duration(5400) == "1時間30分"
        assert format_duration(7200) == "2時間0分"

    def test_minutes_only(self):
        assert format_duration(1800) == "30分"
        assert format_duration(0) == "0分"
        assert format_duration(60) == "1分"


class TestFormatTimeFromIso:
    def test_with_timezone(self):
        result = format_time_from_iso("2026-02-17T07:00:00+09:00")
        assert result == "07:00"

    def test_utc(self):
        # UTC 22:00 = JST 07:00
        result = format_time_from_iso("2026-02-16T22:00:00Z")
        assert result == "07:00"

    def test_invalid(self):
        assert format_time_from_iso("invalid") == "不明"

    def test_none_like(self):
        assert format_time_from_iso("") == "不明"


class TestCalculateTargetBedtime:
    def test_default(self):
        # 07:00起床 - 7.5時間睡眠 - 30分入眠 = 23:00
        assert calculate_target_bedtime("07:00") == "23:00"

    def test_early_wake(self):
        # 06:00起床 - 7.5時間睡眠 - 30分入眠 = 22:00
        assert calculate_target_bedtime("06:00") == "22:00"

    def test_custom_sleep_hours(self):
        # 07:00起床 - 8時間睡眠 - 30分入眠 = 22:30
        assert calculate_target_bedtime("07:00", sleep_hours=8.0) == "22:30"

    def test_invalid_time(self):
        assert calculate_target_bedtime("invalid") == "23:00"


class TestGetTodayPolicy:
    def test_high_readiness(self):
        policy, message, color = get_today_policy(90)
        assert "攻める" in policy

    def test_medium_readiness(self):
        policy, message, color = get_today_policy(75)
        assert "維持" in policy

    def test_low_readiness(self):
        policy, message, color = get_today_policy(60)
        assert "回復" in policy


class TestFormatSleepSection:
    def test_with_data(self, sample_sleep_data, sample_sleep_details):
        section = format_sleep_section(sample_sleep_data, sample_sleep_details)
        assert "睡眠" in section["title"]
        assert "82" in section["description"]
        assert len(section.get("fields", [])) > 0

    def test_without_data(self):
        section = format_sleep_section(None)
        assert "データがありません" in section["description"]

    def test_with_comparison(self, sample_sleep_data, sample_sleep_details):
        prev = {"score": 75}
        section = format_sleep_section(sample_sleep_data, sample_sleep_details, prev)
        # 前日比較が含まれる
        assert "+" in section["description"] or "arrow" in section["description"]


class TestFormatReadinessSection:
    def test_with_data(self, sample_readiness_data):
        section = format_readiness_section(sample_readiness_data)
        assert "Readiness" in section["title"]
        assert "78" in section["description"]

    def test_without_data(self):
        section = format_readiness_section(None)
        assert "データがありません" in section["description"]


class TestFormatMorningReport:
    def test_basic(self, sample_sleep_data, sample_sleep_details, sample_readiness_data):
        data = {
            "sleep": sample_sleep_data,
            "sleep_details": sample_sleep_details,
            "readiness": sample_readiness_data,
            "date": "2026-02-17",
        }
        title, sections = format_morning_report(data)
        assert "おはよう" in title
        assert len(sections) == 3  # 睡眠 + Readiness + 方針


class TestFormatNoonReport:
    def test_behind_pace(self, sample_sleep_data, sample_sleep_details):
        activity = {"steps": 1000, "score": 30}
        title, sections, should_send = format_noon_report(
            activity, 8000, 13, sample_sleep_data, sample_sleep_details
        )
        assert should_send is True

    def test_on_pace(self):
        activity = {"steps": 5000, "score": 70}
        title, sections, should_send = format_noon_report(activity, 8000, 13)
        assert should_send is False

    def test_no_data(self):
        title, sections, should_send = format_noon_report(None, 8000, 13)
        assert should_send is False


class TestFormatNightReport:
    def test_basic(self, sample_readiness_data, sample_sleep_data, sample_activity_data):
        title, sections = format_night_report(
            sample_readiness_data, sample_sleep_data, sample_activity_data
        )
        assert "おつかれ" in title
        assert len(sections) >= 1

    def test_low_scores_early_bedtime(self):
        readiness = {"score": 60}
        sleep = {"score": 60}
        title, sections = format_night_report(readiness, sleep)
        # 低スコア時は早めの就寝推奨
        descriptions = " ".join(s.get("description", "") for s in sections)
        assert "早め" in descriptions
