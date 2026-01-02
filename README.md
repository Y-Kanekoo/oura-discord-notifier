# Oura Ring Discord Notifier

Oura Ring 4のデータをDiscordに毎日通知するアプリケーションです。

## 機能

### 3種類の通知

| 通知 | 時刻 (JST) | 内容 |
|------|-----------|------|
| 朝通知 | 09:00 | 睡眠スコア、Readiness、今日の方針 |
| 昼通知 | 13:00 | 睡眠サマリー（朝に取れなかった場合の補完）、活動リマインダー（ペース遅れ時のみ） |
| 夜通知 | 23:30 | 今日の結果、減速リマインダー |

### 特徴

- 睡眠スコア、詳細（就寝・起床時刻、深い睡眠、レム睡眠、HRVなど）を表示
- Readiness（準備度）に応じた「今日の方針」を提案
- 歩数が目標ペースより30%以上遅れている場合のみ昼通知
- スコアに応じた色分け表示（緑/黄/赤）

## セットアップ

### 1. Oura Personal Access Tokenを取得

1. [Oura Cloud](https://cloud.ouraring.com/personal-access-tokens) にアクセス
2. 「Create New Personal Access Token」をクリック
3. トークンをコピーして保存

### 2. Discord Webhookを作成

1. Discordサーバーの設定を開く
2. 「連携サービス」→「ウェブフック」を選択
3. 「新しいウェブフック」を作成
4. Webhook URLをコピー

### 3. GitHub Secretsを設定

リポジトリの Settings > Secrets and variables > Actions で以下を追加:

| Secret名 | 値 |
|----------|-----|
| `OURA_ACCESS_TOKEN` | Ouraのアクセストークン |
| `DISCORD_WEBHOOK_URL` | DiscordのWebhook URL |

オプションで Variables に追加:

| Variable名 | 値 | デフォルト |
|------------|-----|----------|
| `DAILY_STEPS_GOAL` | 1日の歩数目標 | 8000 |

## 使い方

### GitHub Actionsで自動実行（推奨）

プッシュ後、毎日自動実行されます:
- 09:00 JST - 朝通知
- 13:00 JST - 昼通知（条件付き）
- 23:30 JST - 夜通知

手動実行する場合：
1. Actions タブを開く
2. 「Oura Discord Notifier」を選択
3. 「Run workflow」をクリック
4. 通知タイプ（morning/noon/night）を選択

### ローカルで実行

```bash
# 仮想環境を作成
python3 -m venv .venv
source .venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定（.envファイルを作成）
cp .env.example .env
# .env を編集してトークンを設定

# 実行
cd src
python main.py --type morning  # 朝通知
python main.py --type noon     # 昼通知
python main.py --type night    # 夜通知

# テストメッセージを送信
python main.py --test
```

## 通知サンプル

### 朝通知
```
:sunrise: おはようございます！ (2024-12-31)

:zzz: 睡眠 (12/31)
スコア: 85 :green_circle: (優秀)
├ 就寝 → 起床: 00:30 → 07:45
├ 総睡眠時間: 7時間15分
├ 深い睡眠: 1時間30分
├ レム睡眠: 1時間45分
└ 平均HRV: 45 ms

:zap: Readiness（準備度）
スコア: 78 :yellow_circle: (良好)

:dart: 今日の方針: :arrows_counterclockwise: 維持
いつも通りのペースで過ごそう
```

### 昼通知（睡眠補完 + 活動リマインダー）
```
:walking: 昼のチェックイン

:zzz: 今朝の睡眠 (12/31)
スコア: 82 :yellow_circle: / 7時間15分
:clock10: 00:30 → 08:15

:footprints: 歩数の進捗
2,100 / 8,000 歩 (26%)
██░░░░░░░░
├ 目標ペース: 2,667 歩
├ 差分: -567 歩
└ 今すぐできること: 10分歩く（約1,000歩）
```

### 夜通知
```
:night_with_stars: おつかれさまでした！

:bar_chart: 今日の結果
活動スコア: 75 :yellow_circle:
├ 歩数: 8,234 歩
├ アクティブカロリー: 450 kcal
└ Readiness: 78

:bed: 減速開始（就寝90分前）
:sparkles: コンディション良好です
1. スマホ・PCをオフ
2. 照明を暗くする
3. リラックスタイム
```

## 注意事項

- Ouraのデータはアプリ経由でクラウドに同期されます。朝起きてすぐアプリを開かないと、9時の通知に最新データが反映されない場合があります。
- その場合、昼通知で睡眠データが補完されます。

## ライセンス

MIT
