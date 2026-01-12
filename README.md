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
- **睡眠効率**を自動計算して表示（総睡眠時間÷ベッドにいた時間）
- **前日比較**機能（↑↓→ の絵文字で変化を視覚化）
- **週間トレンド**表示（週平均との比較）
- Readiness（準備度）に応じた「今日の方針」を提案
- **目標就寝時刻**を自動計算（起床時刻から逆算）
- 歩数が目標ペースより30%以上遅れている場合のみ昼通知
- スコアに応じた色分け表示（緑/黄/赤）
- Discord Bot機能（スラッシュコマンド、自然言語、週/月サマリー、グラフ、リマインダー）

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

#### 方法A: GitHub Web UI

1. リポジトリページを開く
2. **Settings** タブをクリック
3. 左メニュー: **Secrets and variables** → **Actions**
4. **New repository secret** ボタンをクリック
5. 以下を追加:

| Secret名 | 値 |
|----------|-----|
| `OURA_ACCESS_TOKEN` | Ouraのアクセストークン |
| `DISCORD_WEBHOOK_URL` | DiscordのWebhook URL |

#### 方法B: GitHub CLI

```bash
# Secretを設定
gh secret set OURA_ACCESS_TOKEN --body "トークンの値"
gh secret set DISCORD_WEBHOOK_URL --body "Webhook URL"

# Secretの一覧を確認（値は見えない）
gh secret list
```

#### オプション設定

Variables に追加（任意）:

| Variable名 | 値 | デフォルト |
|------------|-----|----------|
| `DAILY_STEPS_GOAL` | 1日の歩数目標 | 8000 |
| `TARGET_WAKE_TIME` | 目標起床時刻（HH:MM形式） | 07:00 |

`TARGET_WAKE_TIME` は夜通知の「目標就寝時刻」計算に使用されます。

## 使い方

### GitHub Actionsで自動実行（推奨）

プッシュ後、毎日自動実行されます:
- 09:00 JST - 朝通知
- 13:00 JST - 昼通知（条件付き）
- 23:30 JST - 夜通知

手動実行する場合：

#### GitHub Web UI
1. Actions タブを開く
2. 「Oura Discord Notifier」を選択
3. 「Run workflow」をクリック
4. 通知タイプ（morning/noon/night）を選択

#### GitHub CLI
```bash
# 通知を手動実行
gh workflow run notify.yml -f type=morning  # 朝通知
gh workflow run notify.yml -f type=noon     # 昼通知
gh workflow run notify.yml -f type=night    # 夜通知

# 実行履歴を確認
gh run list --limit 5

# 特定の実行のログを見る
gh run view <RUN_ID> --log

# 失敗したログだけ見る
gh run view <RUN_ID> --log-failed
```

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
# 送信エラーの詳細を見たい場合は DISCORD_WEBHOOK_DEBUG=1 を設定

# 実行
cd src
python main.py --type morning  # 朝通知
python main.py --type noon     # 昼通知
python main.py --type night    # 夜通知

# テストメッセージを送信
python main.py --test
```

### Discord Botとして利用

1. Discord Developer PortalでBotを作成し、`DISCORD_BOT_TOKEN` を `.env` に設定
2. Bot設定で「Message Content Intent」を有効化（自然言語対応に必要）
3. Botを起動

```bash
python src/bot.py
```

Botの設定（歩数目標やリマインダー）は `data/settings.json` に保存されます。

## 通知サンプル

### 朝通知
```
:sunrise: おはようございます！ (2024-12-31)

:zzz: 睡眠 (12/31)
スコア: 85 :green_circle: (優秀) :arrow_up: (+3)
:chart_with_upwards_trend: 週平均より高め（平均: 82）
├ 就寝 → 起床: 00:30 → 07:45
├ 総睡眠時間: 7時間15分
├ 深い睡眠: 1時間30分
├ レム睡眠: 1時間45分
├ 平均HRV: 45 ms
└ 睡眠効率: 92% :star:

:zap: Readiness（準備度）
スコア: 78 :yellow_circle: (良好) :arrow_right: (+1)
:left_right_arrow: 週平均並み（平均: 77）

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
活動スコア: 75 :yellow_circle: :arrow_up: (+5)
:chart_with_upwards_trend: 週平均より高め（平均: 70）
├ 歩数: 8,234 歩
├ アクティブカロリー: 450 kcal
└ Readiness: 78

:bed: 減速開始（就寝90分前）
:sparkles: コンディション良好です

:crescent_moon: 減速開始のルーティン
1. スマホ・PCをオフ
2. 照明を暗くする
3. 目標就寝: 00:00（7.5時間睡眠）
```

## 注意事項

- Ouraのデータはアプリ経由でクラウドに同期されます。朝起きてすぐアプリを開かないと、9時の通知に最新データが反映されない場合があります。
- その場合、昼通知で睡眠データが補完されます。

## トラブルシューティング

### 401 Unauthorized エラー（Oura API）

**症状**: `Error: 401 Client Error: Unauthorized for url: https://api.ouraring.com/...`

**原因と対処法**:

| 原因 | 対処法 |
|------|--------|
| トークンが無効/Revoke済み | [Oura Cloud](https://cloud.ouraring.com/personal-access-tokens)で新しいトークンを発行 |
| GitHub Secretsの設定ミス | トークンをコピーし直してSecretsを更新 |
| Membershipが無効 | Gen3/Ring4はアクティブなOura Membershipが必要 |

**トークンの動作確認**:
```bash
# ローカルでAPIテスト
curl -s "https://api.ouraring.com/v2/usercollection/personal_info" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Discord送信失敗

**症状**: `Failed to send morning/noon/night report`

**原因と対処法**:

| 原因 | 対処法 |
|------|--------|
| Webhook URLが無効 | Discordで新しいWebhookを作成 |
| GitHub Secretsの設定ミス | URLをコピーし直してSecretsを更新 |

**Webhookの動作確認**:
```bash
# ローカルでWebhookテスト
curl -X POST "YOUR_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "テスト"}'
```

### GitHub Secretsの更新方法

```bash
# CLIで更新（推奨）
gh secret set OURA_ACCESS_TOKEN --body "新しいトークン"
gh secret set DISCORD_WEBHOOK_URL --body "新しいWebhook URL"

# または Web UI から
# Settings > Secrets and variables > Actions > 該当のSecretを編集
```

### Oura APIの制限事項

| 項目 | 内容 |
|------|------|
| Personal Access Token有効期限 | なし（期限切れにならない） |
| レート制限 | 5分間に5,000リクエスト |
| Membership要件 | Gen3/Ring4はアクティブなMembershipが必要 |
| 廃止予定 | Personal Access Tokenは2025年末に廃止予定 |

## アーキテクチャ

```
┌──────────────────┐
│   GitHub         │
│  ┌────────────┐  │
│  │ Secrets    │  │  ← トークン/Webhook URLを暗号化保存
│  │ (暗号化)    │  │
│  └────────────┘  │
│        ↓         │
│  ┌────────────┐  │
│  │ Actions    │  │  ← 定期実行（09:00, 13:00, 23:30 JST）
│  │ Runner     │  │
│  └────────────┘  │
└────────┬─────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌────────┐  ┌─────────┐
│ Oura   │  │ Discord │
│ API    │  │ Webhook │
└────────┘  └─────────┘
```

**ローカルPCは不要** - 全てGitHubのクラウド上で実行されます。

## ライセンス

MIT
