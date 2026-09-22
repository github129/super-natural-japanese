# CLAUDE.md

このファイルは Claude Code がこのリポジトリで作業するときの前提情報です。

## プロジェクト

- リポジトリ名: super-natural-japanese
- 目的・技術スタック: 未定(決まり次第ここと README.md を更新すること)
- 主な言語: 日本語(ドキュメント・コミットメッセージ・PR 説明は日本語で書く)

## ブランチ運用

- `main` は常にマージ可能・リリース可能な状態に保つ
- `main` へ直接 push しない。必ず作業ブランチを切り、`main` 向けの Pull Request を作成する
- PR は `.github/PULL_REQUEST_TEMPLATE.md` の項目に沿って記入する

## コーディング規約

- 文字コードは UTF-8、改行コードは LF(`.editorconfig` / `.gitattributes` に従う)
- インデントはスペース 2(Python は 4)
- 秘密情報(API キー、トークンなど)はコミットしない。`.env` は `.gitignore` 済み

## 作業時の注意

- 技術スタック導入時は、セットアップ手順と実行コマンドを README.md に追記する
- テストやリンターを追加したら、このファイルに実行コマンドを追記する
