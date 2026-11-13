---
id: K-20261113-01
date: 2026-11-13
repo: oura-discord-notifier
category: environment
severity: medium
status: mitigated
recurrence: 1
promoted_to:
---

# ネットワーク制限下で local-ci の依存取得が止まる

## 起きたこと

`local-ci run .` の setup で PyPI の名前解決に失敗し、後続ステージが実行されなかった。

## 原因

作業環境からパッケージ配布サイトへ接続できなかった。コード変更の失敗ではない。

## 対処

利用可能な既存の Python 環境で lint と全ユニットテストを実行し、結果を PR に記録した。`local-ci` の全件成功は未確認として扱う。

## 再発防止案

依存パッケージのオフラインキャッシュを検証環境へ事前配置する。再発時は開発環境標準へ反映する。

## 確認方法

キャッシュを利用できる環境で `local-ci run .` を再実行し、setup と後続ステージを確認する。
