"""chart.py のユニットテスト"""

import io
import platform

from chart import (
    _get_japanese_font_families,
    generate_combined_chart,
    generate_score_chart,
    generate_steps_chart,
)


class TestGetJapaneseFontFamilies:
    def test_returns_list(self):
        """フォントファミリーのリストを返す"""
        result = _get_japanese_font_families()
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "sans-serif" in result

    def test_platform_specific(self):
        """現在のプラットフォームに応じたフォントが含まれる"""
        result = _get_japanese_font_families()
        system = platform.system()
        if system == "Darwin":
            assert "Hiragino Sans" in result
        elif system == "Linux":
            assert "Noto Sans CJK JP" in result
        elif system == "Windows":
            assert "Yu Gothic" in result


class TestGenerateScoreChart:
    def _make_data(self, days=7):
        return [
            {
                "date": f"2026-02-{10 + i:02d}",
                "sleep_score": 80 + i,
                "readiness_score": 75 + i,
                "activity_score": 70 + i,
            }
            for i in range(days)
        ]

    def test_returns_bytesio(self):
        """BytesIOオブジェクトを返す"""
        data = self._make_data()
        result = generate_score_chart(data)
        assert isinstance(result, io.BytesIO)

    def test_png_header(self):
        """PNG形式の画像を返す"""
        data = self._make_data()
        result = generate_score_chart(data)
        header = result.read(8)
        assert header[:4] == b'\x89PNG'

    def test_empty_data(self):
        """空データでもエラーにならない"""
        result = generate_score_chart([])
        assert isinstance(result, io.BytesIO)

    def test_partial_data(self):
        """一部スコアがNoneでもエラーにならない"""
        data = [
            {"date": "2026-02-10", "sleep_score": 80, "readiness_score": None, "activity_score": None},
            {"date": "2026-02-11", "sleep_score": None, "readiness_score": 75, "activity_score": 85},
        ]
        result = generate_score_chart(data)
        assert isinstance(result, io.BytesIO)

    def test_show_flags(self):
        """表示フラグを切り替えてもエラーにならない"""
        data = self._make_data(3)
        result = generate_score_chart(data, show_sleep=False, show_readiness=False, show_activity=True)
        assert isinstance(result, io.BytesIO)


class TestGenerateStepsChart:
    def _make_data(self, days=7):
        return [
            {"date": f"2026-02-{10 + i:02d}", "steps": 5000 + i * 1000}
            for i in range(days)
        ]

    def test_returns_bytesio(self):
        """BytesIOオブジェクトを返す"""
        data = self._make_data()
        result = generate_steps_chart(data)
        assert isinstance(result, io.BytesIO)

    def test_empty_data(self):
        """空データでもエラーにならない"""
        result = generate_steps_chart([])
        assert isinstance(result, io.BytesIO)

    def test_custom_goal(self):
        """カスタム目標でもエラーにならない"""
        data = self._make_data(3)
        result = generate_steps_chart(data, goal=12000)
        assert isinstance(result, io.BytesIO)


class TestGenerateCombinedChart:
    def _make_data(self, days=7):
        return [
            {
                "date": f"2026-02-{10 + i:02d}",
                "sleep_score": 80 + i,
                "readiness_score": 75 + i,
                "steps": 6000 + i * 800,
            }
            for i in range(days)
        ]

    def test_returns_bytesio(self):
        """BytesIOオブジェクトを返す"""
        data = self._make_data()
        result = generate_combined_chart(data)
        assert isinstance(result, io.BytesIO)

    def test_empty_data(self):
        """空データでもエラーにならない"""
        result = generate_combined_chart([])
        assert isinstance(result, io.BytesIO)
