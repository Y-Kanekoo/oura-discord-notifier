"""bot_utils.py のユニットテスト"""

from datetime import date, time
from unittest.mock import patch

from bot_utils import parse_date, parse_time_str


class TestParseDate:
    @patch("bot_utils.get_jst_today", return_value=date(2026, 2, 18))
    def test_today_keywords(self, mock_today):
        assert parse_date("今日") == date(2026, 2, 18)
        assert parse_date("きょう") == date(2026, 2, 18)
        assert parse_date("today") == date(2026, 2, 18)

    @patch("bot_utils.get_jst_today", return_value=date(2026, 2, 18))
    def test_yesterday_keywords(self, mock_today):
        assert parse_date("昨日") == date(2026, 2, 17)
        assert parse_date("きのう") == date(2026, 2, 17)
        assert parse_date("yesterday") == date(2026, 2, 17)

    @patch("bot_utils.get_jst_today", return_value=date(2026, 2, 18))
    def test_day_before_yesterday(self, mock_today):
        assert parse_date("一昨日") == date(2026, 2, 16)
        assert parse_date("おととい") == date(2026, 2, 16)

    @patch("bot_utils.get_jst_today", return_value=date(2026, 2, 18))
    def test_n_days_ago(self, mock_today):
        assert parse_date("3日前") == date(2026, 2, 15)

    @patch("bot_utils.get_jst_today", return_value=date(2026, 2, 18))
    def test_minus_n(self, mock_today):
        assert parse_date("-1") == date(2026, 2, 17)
        assert parse_date("-7") == date(2026, 2, 11)

    @patch("bot_utils.get_jst_today", return_value=date(2026, 2, 18))
    def test_month_day_japanese(self, mock_today):
        assert parse_date("1月2日") == date(2026, 1, 2)
        assert parse_date("12月31日") == date(2026, 12, 31)

    def test_iso_format(self):
        assert parse_date("2026-02-17") == date(2026, 2, 17)
        assert parse_date("2026/02/17") == date(2026, 2, 17)

    @patch("bot_utils.get_jst_today", return_value=date(2026, 2, 18))
    def test_mm_dd(self, mock_today):
        assert parse_date("2/17") == date(2026, 2, 17)
        assert parse_date("02-17") == date(2026, 2, 17)

    @patch("bot_utils.get_jst_today", return_value=date(2026, 2, 18))
    def test_mmdd(self, mock_today):
        assert parse_date("0217") == date(2026, 2, 17)

    def test_empty_with_default(self):
        default = date(2026, 1, 1)
        assert parse_date("", default) == default
        assert parse_date(None, default) == default


class TestParseTimeStr:
    def test_valid_time(self):
        assert parse_time_str("22:30") == time(22, 30)
        assert parse_time_str("0:00") == time(0, 0)
        assert parse_time_str("23:59") == time(23, 59)

    def test_invalid_format(self):
        import pytest
        with pytest.raises(ValueError, match="HH:MM"):
            parse_time_str("abc")
        with pytest.raises(ValueError):
            parse_time_str("25:00")

    def test_out_of_range(self):
        import pytest
        with pytest.raises(ValueError, match="00:00〜23:59"):
            parse_time_str("24:00")
