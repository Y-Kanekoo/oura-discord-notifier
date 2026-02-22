---
schema_version: 1
generated_at: 2026-02-21T17:40:00+09:00
commit_hash: b4e7ffadc95a8d203ea403dcdd7fe9d578a226c0
file_count: 51
stack: Python 3.11+, discord.py, requests, matplotlib, ruff, pytest
stage: ベータ
total_issues: 9
critical: 0
high: 0
medium: 3
low: 6
---

# プロジェクトレビューレポート

## 概要

| 項目 | 値 |
|------|-----|
| プロジェクト | oura-discord-notifier |
| スタック | Python 3.11+, discord.py, requests, matplotlib |
| ソースファイル | 16 (src/ + src/cogs/) |
| テストファイル | 10 (tests/) |
| テスト数 | 152 passed, 4 warnings |
| 総行数 | 約3,621行 (src/) |
| CI/CD | ruff + pytest (GitHub Actions) + Dependabot |
| プロジェクト段階 | ベータ |
| linter結果 | ruff: ソースコード指摘なし。テストに6件警告 |

## エグゼクティブサマリ

前回レビュー（2026-02-21 00:00）の全12件の指摘が修正済み。テストカバレッジは6→10ファイル（115→152テスト）に拡充され、settings DI対応・Exception分類化・async wrapping（`run_sync`）が完了。セキュリティ上の重大な問題は検出されなかった。今回の新規指摘は軽微なもの（print残留、テスト未対応Cog、ドキュメント精度）に限定され、Critical/Highの指摘はゼロ。コードベースは前回から大幅に改善され、ベータ段階として十分な品質水準。

## 指摘サマリ

| 重大度 | 件数 |
|--------|------|
| Critical | 0 |
| High | 0 |
| Medium | 3 |
| Low | 6 |

## 前回比較

| 区分 | 件数 |
|------|------|
| 前回から解決済み | 12 |
| 前回から未解決 | 0 |
| 新規検出 | 9 |

前回12件すべて修正済み: C-001〜C-006, T-001〜T-005, D-001

---

## [1] 今すぐやる（高影響 x 低工数）

該当なし

---

## [2] 計画的に対応（高影響 x 高工数）

該当なし

---

## [3] 手が空いたら（低影響 x 低工数）

### C-001: `oura_client.py` の `get_daily_stress` で `except Exception` が残存 [Medium]
- ファイル: `src/oura_client.py:340`
- カテゴリ: quality
- 問題: ストレスデータ取得で全例外を一括キャッチしている。main.py では前回レビューで `requests.RequestException` と `Exception` を分離済みだが、oura_client.py のこの箇所は未対応。
- 対応: `except requests.RequestException` に限定
- 修正案:
```diff
-        except Exception:
+        except requests.RequestException:
             logger.warning("ストレスデータの取得に失敗しました", exc_info=True)
```
- 工数: small
- 根拠: `_request()` メソッドは `requests.RequestException` をキャッチする設計。ストレスデータはオプション機能のため影響は限定的だが、一貫性の観点から修正推奨

### C-002: `discord_client.py` と `bot.py` の `print()` 残留 [Low]
- ファイル: `src/discord_client.py:59,63` / `src/bot.py:47,52,54`
- カテゴリ: quality
- 問題: main.py は前回レビューで `print()` → `logger` に統一済みだが、以下の箇所に `print()` が残っている:
  - `discord_client.py:59` — Webhook デバッグ出力（`DISCORD_WEBHOOK_DEBUG` 環境変数制御下）
  - `discord_client.py:63` — RequestException 時のデバッグ出力
  - `bot.py:47` — Bot起動完了メッセージ
  - `bot.py:52` — スラッシュコマンド同期完了
  - `bot.py:54` — コマンド同期エラー
- 対応: `logger.info()` / `logger.debug()` に変更
- 工数: small
- 根拠: main.py との一貫性。bot.py の print は Bot 実行モードでのみ使用されるため影響は限定的

### T-001: `test_cogs_settings.py` の ruff 警告6件 [Low]
- ファイル: `tests/test_cogs_settings.py:3-4,7`
- カテゴリ: lint
- 問題: ruff が以下の未使用import/変数を検出:
  - `import json` — 未使用
  - `from unittest.mock import AsyncMock, MagicMock, patch` — 一部未使用
  - `import pytest` — 未使用
- 対応: 未使用の import を削除
- 工数: small
- 根拠: CI の ruff チェック通過のため（現在はソースのみ対象で影響なし）

### C-003: `chart.py` のグラフスタイル設定が3関数で重複 [Low]
- ファイル: `src/chart.py:74-121,159-...,220-...`
- カテゴリ: quality
- 問題: `generate_score_chart`, `generate_steps_chart`, `generate_combined_chart` の3関数で、背景色・軸色・枠線色の設定が重複:
  ```python
  fig.patch.set_facecolor('#2C2F33')
  ax.set_facecolor('#2C2F33')
  ax.tick_params(colors='white')
  for spine in ax.spines.values():
      spine.set_color('white')
  ```
- 対応: `_setup_chart_style(fig, ax)` ヘルパーに共通化
- 工数: small
- 根拠: DRY原則。カラーテーマ変更時に3箇所の同時修正が必要

### C-004: `chart.py` の `%-m/%-d` フォーマットが Windows 非互換 [Low]
- ファイル: `src/chart.py:109` / `src/cogs/report.py:148,250,354`
- カテゴリ: quality
- 問題: `strftime('%-m/%-d')` はmacOS/Linuxでは先頭ゼロなしの月日を出力するが、Windowsでは`%-m`がそのまま出力される。
- 対応: 現状は GitHub Actions（Linux）のみで使用するため実害なし。Windows対応が必要になった場合は `f"{dt.month}/{dt.day}"` に変更
- 工数: small
- 根拠: 実行環境がLinuxに限定されるため優先度は低い。情報として記録

---

## [4] 余裕があれば（低影響 x 高工数）

### T-002: テスト未対応のCogファイルが4つ残存 [Medium]
- ファイル: 複数ファイル
- カテゴリ: test
- 問題: 前回レビューで `chart.py` と `cogs/settings_cog.py` のテストが追加されたが、以下4ファイルはテスト未対応:
  - `cogs/general.py` (303行) — 自然言語パターンマッチング（14パターン）
  - `cogs/scheduler.py` (107行) — バックグラウンドタスク・日付境界処理
  - `cogs/health.py` (315行) — ヘルスデータコマンド群
  - `cogs/report.py` (374行) — レポート・分析コマンド群
- 対応: 優先度順にテストを追加
  1. `cogs/general.py` — 正規表現パターンマッチテスト（誤マッチリスク高）
  2. `cogs/scheduler.py` — 日付境界処理、例外ハンドリングテスト
  3. `cogs/health.py` — コマンド引数パース、複数日取得ロジック
  4. `cogs/report.py` — レポート種別ごとのデータ取得テスト
- 工数: large
- 根拠: ソース16ファイル中4ファイルにテストなし（ファイルカバレッジ75%）。前回レビューの50%から改善したが、Cog層（計1,099行）がテスト外

### T-003: CI でテストカバレッジレポートが未実装 [Medium]
- ファイル: `.github/workflows/ci.yml`
- カテゴリ: ci-cd
- 問題: ruff + pytest は実行されているが、テストカバレッジの計測・可視化が未実装。カバレッジの推移が追跡できない。
- 対応:
  1. `pytest-cov` を `requirements-dev.txt` に追加
  2. CI workflow に `pytest --cov=src --cov-report=term-missing` ステップを追加
  3. オプション: coverageバッジの追加（codecov等）
- 工数: medium
- 根拠: Dependabot（pip + GitHub Actions）は設定済み。次のステップとしてカバレッジ可視化が有効

### D-001: README の構成改善 [Low]
- ファイル: `README.md` 複数箇所
- カテゴリ: docs
- 問題: 以下の改善点を検出:
  1. 機能セクション（5-25行）でメイン機能（定期通知）とBot機能（対話型）が混在
  2. アーキテクチャ図（275-297行）が定期通知フローのみで、Bot実行パスが未記載
  3. 「プッシュ後、毎日自動実行」（83行）が誤解を招く表現（cron実行であり、プッシュは不要）
  4. `.env` 設定と `data/settings.json` の役割分担がドキュメント上不明確
- 対応: 機能セクションの分割、アーキテクチャ図の拡張、表現の修正
- 工数: medium
- 根拠: 機能的には問題なく、ドキュメントの精度向上。初見ユーザーの理解を助ける

---

## ドキュメント状況

| ドキュメント | 状態 | 備考 |
|-------------|------|------|
| README.md | 充実 | セットアップ、使い方、トラブルシューティング、アーキテクチャ図あり。構成改善の余地あり（D-001） |
| .env.example | 良好 | 全環境変数を網羅（TARGET_WAKE_TIME追加済み） |
| コード内コメント | 適切 | 日本語で必要十分。docstring充実 |
| API仕様書 | なし | 現段階では不要 |

## テスト状況

| テストファイル | 対象 | テスト数 | カバー範囲 |
|---------------|------|---------|-----------|
| test_formatter.py | formatter.py | 27 | スコア判定、比較、時刻変換、レポート生成 |
| test_advice.py | advice.py | 17 | 全条件分岐のアドバイス生成 |
| test_discord_client.py | discord_client.py | 14 | リトライ、429処理、メッセージ/Embed/レポート送信 |
| test_bot_utils.py | bot_utils.py | 23 | 日付パース、時刻パース、エッジケース |
| test_oura_client.py | oura_client.py | 16 | リトライ、期間取得、range取得 |
| test_settings.py | settings.py | 17 | 初期化、CRUD、リマインダー、目標通知 |
| test_chart.py | chart.py | 12 | PNG生成、空データ、部分データ |
| test_cogs_settings.py | cogs/settings_cog.py | 9 | 目標設定、リマインダー、通知設定 |
| test_main.py | main.py | 10 | 通知関数のロジック |
| conftest.py | 共通 | - | サンプルデータフィクスチャ |

**テスト未対応の重要モジュール**（優先度順）:
1. `cogs/general.py` — 自然言語パターンマッチ（14パターン、誤マッチリスク）
2. `cogs/scheduler.py` — バックグラウンドタスク（日付境界処理）
3. `cogs/health.py` — ヘルスデータコマンド（引数パース）
4. `cogs/report.py` — レポートコマンド（データ取得フロー）

## 運用準備状況（ベータ段階）

| 項目 | 状態 | 備考 |
|------|------|------|
| 定期実行 | 設定済み | cron: 朝07:30JST/昼13:00JST/夜23:30JST |
| シークレット管理 | 良好 | GitHub Secrets使用、.envはgit除外 |
| エラー通知 | 全対応 | 朝・昼・夜すべてDiscordに送信。Exception分類済み |
| ログ出力 | 改善済み | main.py: logger統一。bot.py/discord_client.py: print残留（C-002） |
| 二重実行防止 | 設定済み | concurrencyグループ設定あり |
| 依存脆弱性チェック | 設定済み | Dependabot（pip + GitHub Actions） |
| テスト自動実行 | 設定済み | CI: ruff + pytest (Python 3.11, 3.12) |
| 非同期対応 | 完了 | `run_sync()` で同期API呼び出しをラップ済み |
| Settings DI | 完了 | `_SettingsProxy` パターンでテスタビリティ向上 |

---

## 推奨アクション（次の3ステップ）

1. **C-001 + C-002 + T-001** を修正する — oura_client.pyの例外限定（1行）+ print→logger統一（5箇所）+ ruff警告修正（3行削除）
2. **T-002** の `cogs/general.py` テストを追加する — 14パターンの正規表現マッチテスト（最優先Cogテスト）
3. **T-003** のカバレッジレポートを CI に追加する — `pytest-cov` 導入でカバレッジ可視化

## 並列修正可能グループ

以下の指摘は互いに独立しており、同時に修正可能:
- グループA: C-001 + C-002 + T-001（コード品質改善、small）
- グループB: C-003 + C-004（chart.py改善、small）
- グループC: T-002（Cogテスト追加、large）
- グループD: T-003（CI改善、medium）
- グループE: D-001（ドキュメント改善、medium）

## 次回注目ポイント

- Cog層テストの追加状況（general.py → scheduler.py の順）
- テストカバレッジの数値的な把握（pytest-cov導入後）
- Oura Personal Access Token の廃止予定への対応検討
- bot.py のリポジトリPublic化後のセキュリティ確認

## セキュリティスキャン結果

| チェック項目 | 結果 |
|-------------|------|
| ハードコード機密情報 | 検出なし |
| eval/exec使用 | 検出なし |
| ベア例外 | 1件（C-001: oura_client.py get_daily_stress） |
| TODO/FIXME残留 | 検出なし |
| ログへの機密情報出力 | 検出なし |
| .env gitignore | 設定済み |
| ruff lint | ソースコード: All checks passed |
| Dependabot | pip + GitHub Actions 監視済み |
| Git履歴の機密情報 | 検出なし（全27コミット調査済み） |
