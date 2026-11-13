# Oura Ring Discord Notifier

Oura Ring 4のデータをDiscordに毎日通知するアプリケーションです。

## 機能

### GitHub Actions 定期通知（メイン機能）

GitHub Actionsのcronスケジュールにより、1日3回の通知を自動送信します。

| 通知 | 時刻 (JST) | 内容 |
|------|-----------|------|
| 朝通知 | 07:30 | 睡眠スコア、Readiness、今日の方針 |
| 昼通知 | 13:00 | 睡眠サマリー（朝に取れなかった場合の補完）、活動リマインダー（ペース遅れ時のみ） |
| 夜通知 | 23:30 | 今日の結果、減速リマインダー |

**通知の特徴**:

- 睡眠スコア、詳細（就寝・起床時刻、深い睡眠、レム睡眠、HRVなど）を表示
- **睡眠効率**を自動計算して表示（総睡眠時間÷ベッドにいた時間）
- **前日比較**機能（↑↓→ の絵文字で変化を視覚化）
- **週間トレンド**表示（週平均との比較）
- Readiness（準備度）に応じた「今日の方針」を提案
- **目標就寝時刻**を自動計算（起床時刻から逆算）
- 歩数が目標ペースより30%以上遅れている場合のみ昼通知
- スコアに応じた色分け表示（緑/黄/赤）

### Discord Bot（対話型機能）

常駐型のDiscord Botとして起動し、対話的にOuraデータを確認できます。

- スラッシュコマンドによるデータ取得
- 自然言語での問い合わせ対応
- 週間/月間サマリーの表示
- グラフによるデータ可視化
- リマインダー設定

## セットアップ

### 1. Oura OAuth2 アプリを登録

1. [Oura Cloud の My Applications](https://cloud.ouraring.com/oauth/applications) でシングルユーザー用アプリを登録します。アプリ作成と認可は利用者が行います。[公式認証仕様](https://cloud.ouraring.com/docs/authentication)も参照してください。
2. 名前は `Oura Discord Notifier`、説明は `個人利用で Oura の睡眠・準備・活動・心拍・ワークアウトを読み Discord に通知するシングルユーザーアプリ` にします。
3. Redirect URI に **`http://localhost:8765/callback`** を正確に登録します。スコープは **`daily personal heartrate workout`** だけを選びます。`email`、`tag`、`session`、`spo2` は不要です。
4. GitHub CLI をインストールして対象リポジトリへ `gh auth login` でログインします。GitHub Secrets の更新用に、対象リポジトリ `Y-Kanekoo/oura-discord-notifier` の **Secrets: Read and write** 権限を持つ fine-grained PAT を用意します。
5. ローカルで次を実行し、Client ID、Client Secret、GitHub Secrets 更新用 PAT を非表示入力します。認可 URL は Client ID を伏せて表示され、実際の URL がブラウザで開きます。callback は `127.0.0.1` と `::1` のポート 8765 で受けます。

```bash
python3 scripts/oura_oauth_setup.py
```

スクリプトは PKCE (S256) で code を交換し、`OURA_CLIENT_ID`、`OURA_CLIENT_SECRET`、`OURA_REFRESH_TOKEN`、`OURA_ACCESS_TOKEN`、`OURA_ACCESS_TOKEN_EXPIRES_AT` を GitHub Secrets に保存します。macOS では Keychain（service: `oura-discord-notifier`）にも保存します。

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
| `OURA_CLIENT_ID` / `OURA_CLIENT_SECRET` | Oura アプリの認証情報 |
| `OURA_REFRESH_TOKEN` | 単回使用の refresh token |
| `OURA_ACCESS_TOKEN` / `OURA_ACCESS_TOKEN_EXPIRES_AT` | 取得済み access token と失効時刻（Unix 秒）。PAT フォールバックも可能 |
| `SECRETS_WRITE_TOKEN` | 対象リポジトリの Secrets: Read and write 権限付き fine-grained PAT（任意） |
| `DISCORD_WEBHOOK_URL` | DiscordのWebhook URL |

#### 方法B: GitHub CLI

Oura の Secret は上のセットアップスクリプトが標準入力経由で設定します。Discord の Webhook URL は GitHub Web UI から登録してください。値をコマンド引数に置かないでください。

OAuth 三方が揃っている場合、期限内の access token を使い、失効・未設定・API の 401 時だけ refresh します。Oura の refresh token は単回使用のため、更新後の refresh/access token と有効期限を保存します。GitHub Actions では `SECRETS_WRITE_TOKEN` がある場合だけ `gh secret set` を使います。標準の `GITHUB_TOKEN` には Secrets 更新権限がありません。`SECRETS_WRITE_TOKEN` が未設定、または保存に失敗した場合もその実行は続けますが、**次回 refresh 後は再認可が必要**です。三方が揃わない場合だけ `OURA_ACCESS_TOKEN` をフォールバックに使います。

#### オプション設定

Variables に追加（任意）:

| Variable名 | 値 | デフォルト |
|------------|-----|----------|
| `DAILY_STEPS_GOAL` | 1日の歩数目標 | 8000 |
| `TARGET_WAKE_TIME` | 目標起床時刻（HH:MM形式） | 07:00 |

`TARGET_WAKE_TIME` は夜通知の「目標就寝時刻」計算に使用されます。

## 使い方

### GitHub Actionsで自動実行（推奨）

GitHub Actionsにより毎日自動実行されます:
- 07:30 JST - 朝通知
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
# macOS は Keychain に保存された値を利用可能。他の環境では .env を編集

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

**設定ファイルの役割分担**:

| ファイル | 役割 | 内容 |
|----------|------|------|
| `.env` | 認証情報・シークレット | `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET`, `OURA_REFRESH_TOKEN`, `DISCORD_BOT_TOKEN` など |
| `data/settings.json` | Botの動的設定 | 歩数目標、リマインダー、ユーザーごとの設定など |

`.env` はGitにコミットせず、各環境で個別に管理してください。`data/settings.json` はBotの実行中にコマンドで変更でき、自動的に保存されます。

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

### 診断ログの情報制限（Issue #35）

定期通知 CLI（朝・昼・夜・`--test`）と共有 HTTP client は、診断を
provider・操作・固定エラー分類・HTTP status・試行回数に限定します。
例外原文、例外チェーン、traceback、HTTP 本文、URL、headers、payload、歩数などの
健康値を診断へ出しません。requests の低層接続 DEBUG ログも抑制します。
通常の健康レポートには意図した健康データを従来どおり含め、payload を伏せ字にしません。

朝・昼・夜の失敗通知は固定テンプレートと安全な診断のみです。追加通知は最大1呼出で、
内部の既存 retry を含めても既定最大3試行。追加通知の False・例外で再帰せず、元の
レポート失敗（False／CLI exit 1）を維持します。204 のみ送信成功、既存の retry/backoff、
chunk 分割、週平均・ストレスの optional fallback、昼の正常 skip は変更しません。
再試行による受領済みメッセージの重複可能性や実到達保証はこの変更では解決しません。

対象は定期 CLI と共有 client の診断です。別 entrypoint の `bot.py`／対話型 cogs の
例外応答・logging は残る監査対象で、全リポジトリの秘匿化を保証するものではありません。
`docs/review-report.md` の過去レビューは当時の記録であり、本修正の検証結果ではありません。

テストでは合成 sentinel と HTTP stub のみを使い、予期しない socket/DNS を拒否します。
実 Oura データ・実 Discord 到達・資格情報は未検証です。依存・Secrets・workflow・時刻は
変更せず、main マージで即時通知は行いません。次の既存 schedule から適用されます。

### 通知が定刻に届かない（GitHub Actionsが動いていない）

**症状**: cronで通知が来ない、Actionsタブに最近の実行履歴がない

**原因**: GitHub は**60日間コミットがないリポジトリのスケジュールワークフローを自動的に無効化**します（[公式ドキュメント](https://docs.github.com/ja/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule)）。

**対処法**:

1. リポジトリの **Actions** タブを開く
2. `Oura Discord Notifier` ワークフローを選択
3. "This scheduled workflow has been disabled" バナーが出ていれば **Enable workflow** をクリック
4. 何らかのコミットを push して再有効化を維持（ダミーでも可）

`workflow_dispatch` での手動実行は無効化中でも可能なので、まずは手動実行で動作確認すると切り分けやすいです。

### 401 Unauthorized エラー（Oura API）

**症状**: `provider=notification operation=morning error=http status=401`

**原因と対処法**:

| 原因 | 対処法 |
|------|--------|
| refresh token が無効・失効済み | `python3 scripts/oura_oauth_setup.py` で再認可 |
| GitHub Secrets の設定ミス | セットアップスクリプトで再保存 |
| Membershipが無効 | Gen3/Ring4はアクティブなOura Membershipが必要 |

動作確認には GitHub Actions の手動実行を使い、ログに認証情報を表示しないでください。

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
python3 scripts/oura_oauth_setup.py

# または Web UI から
# Settings > Secrets and variables > Actions > 該当のSecretを編集
```

### Oura APIの制限事項

| 項目 | 内容 |
|------|------|
| OAuth access token有効期限 | トークン応答の `expires_in` に従う |
| レート制限 | 5分間に5,000リクエスト |
| Membership要件 | Gen3/Ring4はアクティブなMembershipが必要 |
| refresh token | 単回使用。更新後の値を保存する |

## アーキテクチャ

### 定期通知フロー（GitHub Actions）

```
┌──────────────────┐
│   GitHub         │
│  ┌────────────┐  │
│  │ Secrets    │  │  ← トークン/Webhook URLを暗号化保存
│  │ (暗号化)    │  │
│  └────────────┘  │
│        ↓         │
│  ┌────────────┐  │
│  │ Actions    │  │  ← cron定期実行（07:30, 13:00, 23:30 JST）
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

### Bot実行フロー（discord.py）

```
┌──────────────────┐
│  ローカルPC /     │
│  常駐サーバー      │
│  ┌────────────┐  │
│  │ bot.py     │  │  ← discord.py で常駐起動
│  │ (discord.py)│  │
│  └────────────┘  │
└────────┬─────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌────────┐  ┌───────────┐
│ Oura   │  │ Discord   │
│ API    │  │ Channel   │  ← スラッシュコマンド / 自然言語で対話
└────────┘  └───────────┘
```

**常駐プロセスが必要** - ローカルPCまたはサーバーでbot.pyを起動し続ける必要があります。

## ライセンス

MIT
