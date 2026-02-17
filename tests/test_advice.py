"""advice.py のユニットテスト"""

from advice import generate_advice, get_quick_tip


class TestGenerateAdvice:
    def test_high_readiness(self):
        result = generate_advice(readiness_score=90)
        assert "コンディション絶好調" in result

    def test_good_readiness(self):
        result = generate_advice(readiness_score=75)
        assert "コンディション良好" in result

    def test_tired_readiness(self):
        result = generate_advice(readiness_score=65)
        assert "やや疲れ気味" in result

    def test_low_readiness(self):
        result = generate_advice(readiness_score=50)
        assert "回復を優先" in result

    def test_low_sleep_score(self):
        result = generate_advice(sleep_score=55)
        assert "睡眠が不足" in result

    def test_moderate_sleep_score(self):
        result = generate_advice(sleep_score=65)
        assert "睡眠スコアが低め" in result

    def test_good_sleep_no_advice(self):
        result = generate_advice(sleep_score=80)
        # 良好な睡眠ではアドバイスなし → デフォルトメッセージ
        assert "特に問題なし" in result

    def test_goal_achieved(self):
        result = generate_advice(steps=10000, steps_goal=8000)
        assert "歩数目標達成" in result

    def test_close_to_goal(self):
        result = generate_advice(steps=6000, steps_goal=8000)
        assert "あと少し" in result

    def test_low_steps(self):
        result = generate_advice(steps=2000, steps_goal=8000)
        assert "歩数が少なめ" in result

    def test_high_activity(self):
        result = generate_advice(activity_score=90)
        assert "活動量が十分" in result

    def test_low_activity_and_steps(self):
        result = generate_advice(activity_score=40, steps=2000, steps_goal=8000)
        assert "活動量が少なめ" in result

    def test_no_data(self):
        result = generate_advice()
        assert "特に問題なし" in result

    def test_combined(self):
        result = generate_advice(
            readiness_score=90,
            sleep_score=55,
            steps=10000,
            steps_goal=8000,
        )
        assert "コンディション絶好調" in result
        assert "睡眠が不足" in result
        assert "歩数目標達成" in result


class TestGetQuickTip:
    def test_none(self):
        assert get_quick_tip(None) == "今日も良い一日を！"

    def test_high(self):
        result = get_quick_tip(90)
        assert "絶好調" in result

    def test_good(self):
        result = get_quick_tip(75)
        assert "良好" in result

    def test_tired(self):
        result = get_quick_tip(65)
        assert "疲れ気味" in result

    def test_low(self):
        result = get_quick_tip(50)
        assert "回復優先" in result
