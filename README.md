# Oura Ring Discord Notifier

Oura Ring 4のデータをDiscordに毎日通知するアプリケーションです。

## 機能

- 毎朝7:00（JST）に前日の健康データをDiscordに送信
- 睡眠スコア、Readiness（準備度）、活動データを表示
- スコアが低い場合は警告メッセージを送信

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

## 使い方

### GitHub Actionsで自動実行（推奨）

プッシュ後、毎朝7:00 JSTに自動実行されます。

手動実行する場合：
1. Actions タブを開く
2. 「Send Daily Oura Report」を選択
3. 「Run workflow」をクリック

### ローカルで実行

```bash
# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
export OURA_ACCESS_TOKEN="your_token"
export DISCORD_WEBHOOK_URL="your_webhook_url"

# 実行
cd src
python main.py

# 特定の日付のデータを送信
python main.py --date 2024-01-15

# テストメッセージを送信
python main.py --test
```

## 通知サンプル

```
:sunrise: おはようございます！ (2024-01-15)

:zzz: 睡眠
スコア: 85 :green_circle: (優秀)
├ 総睡眠時間: スコア 90
├ 深い睡眠: スコア 85
└ レム睡眠: スコア 80

:zap: Readiness（準備度）
スコア: 78 :yellow_circle: (良好)
├ 回復度: スコア 82
└ 安静時心拍: スコア 75

:runner: 活動
スコア: 72 :yellow_circle: (良好)
├ 歩数: 8,234 歩
├ アクティブカロリー: 450 kcal
└ 総消費カロリー: 2,150 kcal
```

## ライセンス

MIT
