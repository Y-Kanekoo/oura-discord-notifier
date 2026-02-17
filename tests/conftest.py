"""テスト共通フィクスチャ"""

import sys
from pathlib import Path

# src/ をPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest


@pytest.fixture
def sample_sleep_data():
    """サンプル睡眠データ"""
    return {
        "score": 82,
        "day": "2026-02-17",
        "contributors": {
            "deep_sleep": 80,
            "efficiency": 85,
            "latency": 90,
            "rem_sleep": 78,
            "restfulness": 75,
            "timing": 88,
            "total_sleep": 82,
        },
    }


@pytest.fixture
def sample_sleep_details():
    """サンプル睡眠詳細データ"""
    return {
        "bedtime_start": "2026-02-16T23:30:00+09:00",
        "bedtime_end": "2026-02-17T07:00:00+09:00",
        "total_sleep_duration": 25200,  # 7時間
        "deep_sleep_duration": 5400,  # 1.5時間
        "rem_sleep_duration": 7200,  # 2時間
        "light_sleep_duration": 12600,  # 3.5時間
        "lowest_heart_rate": 52,
        "average_hrv": 45.3,
        "time_in_bed": 27000,  # 7.5時間
        "type": "long_sleep",
        "day": "2026-02-17",
    }


@pytest.fixture
def sample_readiness_data():
    """サンプルReadinessデータ"""
    return {
        "score": 78,
        "day": "2026-02-17",
        "contributors": {
            "recovery_index": 80,
            "resting_heart_rate": 75,
            "hrv_balance": 82,
        },
    }


@pytest.fixture
def sample_activity_data():
    """サンプル活動データ"""
    return {
        "score": 85,
        "day": "2026-02-17",
        "steps": 9500,
        "active_calories": 350,
        "total_calories": 2200,
    }
