---
schema_version: 1
generated_at: 2026-02-21T00:00:00+09:00
commit_hash: b4f13bf62dde1c4941f4a3f20ebb14d690375f32
file_count: 22
stack: Python 3.11+, discord.py, requests, matplotlib, ruff, pytest
stage: ベータ
total_issues: 12
critical: 0
high: 0
medium: 6
low: 6
---

# プロジェクトレビューレポート

## 概要

| 項目 | 値 |
|------|-----|
| プロジェクト | oura-discord-notifier |
| スタック | Python 3.11+, discord.py, requests, matplotlib |
| ソースファイル | 14 (src/) |
| テストファイル | 6 (tests/) |
| テスト数 | 115 passed |
| 総行数 | 約3,544行 (src/) |
| CI/CD | ruff + pytest (GitHub Actions) + Dependabot |
| プロジェクト段階 | ベータ |
| linter結果 | ruff: 指摘なし (All checks passed!) |

## エグゼクティブサマリ

前回レビュー（2026-02-20）の全11件の指摘が修正済み。テストカバレッジは4→6ファイル（115テスト）に拡充され、Dependabotも導入済み。セキュリティ上の重大な問題は検出されなかった。今回の新規指摘は主に防御的プログラミング（ゼロ除算防止、falsy判定）、ログ出力の統一、および残りのテストカバレッジ拡充に関するもの。コードベースは安定しており、ベータ段階として十分な品質水準。

## 指摘サマリ

| 重大度 | 件数 |
|--------|------|
| Critical | 0 |
| High | 0 |
| Medium | 6 |
| Low | 6 |

## 前回比較

| 区分 | 件数 |
|------|------|
| 前回から解決済み | 11 |
| 前回から未解決 | 0 |
| 新規検出 | 12 |

前回11件すべて修正済み: C-001〜C-008, D-001, T-001, T-002

---

## [1] 今すぐやる（高影響 x 低工数）

該当なし

---

## [2] 計画的に対応（高影響 x 高工数）

該当なし

---

## [3] 手が空いたら（低影響 x 低工数）

### C-001: `advice.py` のゼロ除算リスク [Medium]
- ファイル: `src/advice.py:101`
- カテゴリ: bug
- 問題: `steps / steps_goal` でゼロ除算の可能性。71行目では `steps_goal > 0` チェック済みだが、101行目は未チェック。
- 対応: 除算前の防御チェック追加
- 修正案:
```diff
-        elif activity_score < 50 and (steps is None or steps / steps_goal < 0.5):
+        elif activity_score < 50 and (steps is None or (steps_goal > 0 and steps / steps_goal < 0.5)):
```
- 工数: small
- 根拠: `steps_goal` は環境変数経由でデフォルト8000のため実害リスクは低いが、防御的プログラミングとして修正推奨

### C-002: `main.py` の print と logging の混在 [Medium]
- ファイル: `src/main.py` 複数箇所（22, 71, 89, 96, 107, 118, 143, 150, 167, 203, 211, 233, 244行）
- カテゴリ: quality
- 問題: `logging.basicConfig()` でロガー設定済みだが、メイン処理では `print()` を使用。エラーハンドリングのみ `logger.error()` を使用しており不統一。
- 対応: `print()` を `logger.info()` に統一
- 工数: small
- 根拠: 本番運用（GitHub Actions）では print は stdout に出力されるが、ログレベル制御やフォーマット統一ができない

### C-003: `bot_utils.py` の `parse_date()` で日付範囲バリデーションなし [Medium]
- ファイル: `src/bot_utils.py:87-107`
- カテゴリ: quality
- 問題: `N月D日` / `MM-DD` / `MMDD` 形式のパースで、月日の範囲チェックなし。`13月32日` のような不正入力は `date()` コンストラクタの `ValueError` に依存。呼び出し元（Cogコマンド）で `ValueError` はキャッチされるが、エラーメッセージが技術的になる。
- 対応: パース時に範囲チェックを追加し、ユーザーフレンドリーなエラーメッセージを返す
- 修正案:
```diff
     m = re.match(r"(\d{1,2})月(\d{1,2})日?", s)
     if m:
         month, day = int(m.group(1)), int(m.group(2))
+        if not (1 <= month <= 12 and 1 <= day <= 31):
+            raise ValueError(f"月日の範囲が不正です: {month}月{day}日")
         return date(today.year, month, day)
```
- 工数: small
- 根拠: 同一ファイルの `parse_time_str()` では範囲チェック済み（139-140行）。一貫性の観点

### C-004: `formatter.py` の `prev_score` falsy チェック [Low]
- ファイル: `src/formatter.py:177`
- カテゴリ: quality
- 問題: `if prev_score` は `prev_score == 0` も falsy として扱い、スコア0の前日比較が無視される。
- 対応: `if prev_score is not None` に変更
- 修正案:
```diff
-    comparison = format_comparison(score, prev_score) if prev_score else ""
+    comparison = format_comparison(score, prev_score) if prev_score is not None else ""
```
- 工数: small
- 根拠: Ouraスコアは通常1-100だが、APIが0を返す可能性は排除できない

### C-005: `discord_client.py` の `retry_after` 例外ハンドリング [Low]
- ファイル: `src/discord_client.py:39-42`
- カテゴリ: quality
- 問題: `response.json()` の例外を `ValueError` でキャッチしているが、Python 3.11+では `json.JSONDecodeError`（`ValueError` のサブクラス）がより適切。また `retry_after` の型が保証されていない。
- 対応: 例外タイプの明確化と型チェック追加
- 修正案:
```diff
+import json
+
                     try:
-                        retry_after = response.json().get("retry_after")
-                    except ValueError:
+                        data = response.json()
+                        retry_after = data.get("retry_after") if isinstance(data, dict) else None
+                    except (ValueError, json.JSONDecodeError):
                         retry_after = None
```
- 工数: small
- 根拠: 防御的プログラミング。Discord APIが予期しないレスポンスを返した場合の安全策

### T-001: `parse_date` のエッジケーステスト不足 [Low]
- ファイル: `tests/test_bot_utils.py`
- カテゴリ: test
- 問題: 年越え（12/31→1/1）、月末（2/29うるう年）、範囲外入力（13月、32日）のテストなし。
- 対応: parameterize を使いエッジケーステストを追加
- 工数: small
- 根拠: 現在13テストケースで基本パターンはカバー済みだが、境界値テストが不足

### T-002: `get_sleep_details_range` のテスト欠落 [Low]
- ファイル: `tests/test_oura_client.py`
- カテゴリ: test
- 問題: 新規追加された `get_sleep_range()` と `get_sleep_details_range()` メソッドのテストがない。
- 対応: テスト追加（特に `get_sleep_details_range` の日付オフセットロジック検証）
- 工数: small
- 根拠: C-008修正で追加されたメソッドだが、テストが追加されていない

### D-001: README のワークフロー時刻記載に曖昧さ [Low]
- ファイル: `README.md:84`
- カテゴリ: docs
- 問題: README で「09:00 JST - 朝通知」と記載されているが、実際の cron 実行は 07:30 JST（到着は08:30-09:00頃）。「09:00」は到着予定時刻であり、実行時刻との区別が曖昧。
- 対応: 「07:30 JST 実行（到着: 08:30-09:00 JST）」のように明確化
- 工数: small
- 根拠: `notify.yml:5-6` のコメントでは明確だが、README のみ読むユーザーに誤解を与える可能性

---

## [4] 余裕があれば（低影響 x 高工数）

### T-003: テスト未対応ソースファイルが7つ残存 [Medium]
- ファイル: 複数ファイル
- カテゴリ: test
- 問題: 前回レビューで `settings.py` と `discord_client.py` のテストが追加されたが、以下7ファイルはテスト未対応:
  - `chart.py` (307行) — グラフ生成
  - `bot.py` (96行) — Botエントリポイント
  - `cogs/health.py` (313行) — ヘルスデータコマンド
  - `cogs/report.py` (372行) — レポートコマンド
  - `cogs/scheduler.py` (105行) — スケジューラー
  - `cogs/settings_cog.py` (160行) — 設定コマンド
  - `cogs/general.py` (301行) — 汎用コマンド
- 対応: 優先度順にテストを追加
  1. `chart.py` — BytesIO出力のPNGヘッダ検証（テスタビリティ高）
  2. `cogs/health.py` — APIモックで複数日取得ロジック検証
  3. `cogs/report.py` — フォーマッター連携テスト
- 工数: large
- 根拠: ソース14ファイル中7ファイルにテストなし（カバレッジ率50%）。chart.pyとCogファイルは外部連携が多くバグが発生しやすい

### T-004: `bot_utils.py` の `settings` グローバル初期化がテスタビリティを低下 [Medium]
- ファイル: `src/bot_utils.py:17`
- カテゴリ: quality
- 問題: `settings = SettingsManager()` がモジュールレベルで初期化されており、テスト時に独立した設定管理ができない。Cogのテスト追加時にグローバル状態が問題となる。
- 対応: 依存注入パターンの導入、または fixture で上書き可能な設計に変更
- 工数: medium
- 根拠: テスト間の状態汚染リスク。T-003のCogテスト追加時に障壁となる

### T-005: エラーハンドリングが `Exception` 一括キャッチ [Medium]
- ファイル: `src/main.py:117,177,243`
- カテゴリ: quality
- 問題: 3通知関数すべてで `except Exception as e` により全例外を一括キャッチ。API障害、ネットワークエラー、ロジックバグの区別ができず、デバッグが困難。
- 対応: `requests.RequestException`（API/ネットワーク）と `Exception`（ロジック）を分離し、異なるログレベルで記録
- 工数: medium
- 根拠: 現状は全エラーが同一フォーマットでDiscord通知されるため、障害原因の特定に時間がかかる

### C-006: `requests` ライブラリの同期I/OがBotのイベントループをブロック [Medium]
- ファイル: `src/oura_client.py`, `src/discord_client.py`
- カテゴリ: perf
- 問題: OuraClient/DiscordClient は同期ライブラリ（requests）を使用。Discord Bot（asyncio）内で呼ばれた場合、リトライ時の `time.sleep()` がイベントループをブロックする。
- 対応: `aiohttp` への移行を検討。または `asyncio.to_thread()` でラップ
- 工数: large
- 根拠: main.py（GitHub Actions通知）は同期実行のため問題ないが、Bot（Cogコマンド・スケジューラー）では理論上ブロッキングが発生。前回レポートC-002のインメモリキャッシュ追加で settings.py は対応済みだが、API呼び出し部分は未対応

---

## ドキュメント状況

| ドキュメント | 状態 | 備考 |
|-------------|------|------|
| README.md | 充実 | セットアップ、使い方、トラブルシューティング、アーキテクチャ図あり |
| .env.example | 良好 | 全環境変数を網羅（TARGET_WAKE_TIME追加済み） |
| コード内コメント | 適切 | 日本語で必要十分 |
| API仕様書 | なし | 現段階では不要 |

## テスト状況

| テストファイル | 対象 | テスト数 | カバー範囲 |
|---------------|------|---------|-----------|
| test_formatter.py | formatter.py | 27 | スコア判定、比較、時刻変換、レポート生成 |
| test_advice.py | advice.py | 17 | 全条件分岐のアドバイス生成 |
| test_discord_client.py | discord_client.py | 14 | リトライ、429処理、メッセージ/Embed/レポート送信、チャンク分割 |
| test_bot_utils.py | bot_utils.py | 13 | 日付パース、時刻パース |
| test_oura_client.py | oura_client.py | 10 | リトライ、期間取得、構造確認 |
| test_settings.py | settings.py | 17 | 初期化、CRUD、リマインダー、目標通知、日次フラグ、破損復旧 |

**テスト未対応の重要モジュール**（優先度順）:
1. `chart.py` — グラフ生成（PNG出力検証、テスタビリティ高）
2. `cogs/health.py` — ヘルスデータコマンド（複数日取得ロジック）
3. `cogs/report.py` — レポート・分析コマンド
4. `bot.py` — Botエントリポイント
5. `cogs/scheduler.py`, `cogs/settings_cog.py`, `cogs/general.py` — その他Cog

## 運用準備状況（ベータ段階）

| 項目 | 状態 | 備考 |
|------|------|------|
| 定期実行 | 設定済み | cron: 朝07:30JST/昼13:00JST/夜23:30JST |
| シークレット管理 | 良好 | GitHub Secrets使用、.envはgit除外 |
| エラー通知 | 全対応 | 朝・昼・夜すべてDiscordに送信（C-001修正済み） |
| ログ出力 | 基本的 | logging.basicConfig設定済み、main.pyはprint混在（C-002） |
| 二重実行防止 | 設定済み | concurrencyグループ設定あり |
| 依存脆弱性チェック | 設定済み | Dependabot（pip + GitHub Actions） |
| テスト自動実行 | 設定済み | CI: ruff + pytest (Python 3.11, 3.12) |

---

## 推奨アクション（次の3ステップ）

1. **C-001 + C-004** を修正する — advice.pyのゼロ除算防止（1行）+ formatter.pyのfalsyチェック修正（1行）
2. **C-002** を修正する — main.pyのprint()をlogger.info()に統一（13箇所のメカニカルな置換）
3. **T-002** を修正する — get_sleep_range/get_sleep_details_rangeのテスト追加

## 並列修正可能グループ

以下の指摘は互いに独立しており、同時に修正可能:
- グループA: C-001 + C-003 + C-004（防御的プログラミング）
- グループB: C-002（ログ統一）
- グループC: C-005（例外ハンドリング改善）
- グループD: T-001 + T-002（テスト追加）
- グループE: D-001（ドキュメント修正）

## 次回注目ポイント

- GitHub Actionsのビリングブロック解消後、実際の通知動作確認
- テストカバレッジの拡充（特に chart.py, cogs/health.py）
- Oura Personal Access Token の廃止予定への対応検討
- Cogテスト追加時の bot_utils.py グローバル settings 問題（T-004）の解決

## セキュリティスキャン結果

| チェック項目 | 結果 |
|-------------|------|
| ハードコード機密情報 | 検出なし |
| eval/exec使用 | 検出なし |
| ベア例外 | 検出なし |
| TODO/FIXME残留 | 検出なし |
| ログへの機密情報出力 | 検出なし |
| .env gitignore | 設定済み |
| ruff lint | All checks passed |
| Dependabot | pip + GitHub Actions 監視済み |
