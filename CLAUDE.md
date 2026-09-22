# CLAUDE.md

このファイルは Claude Code がこのリポジトリで作業するときの前提情報です。

## プロジェクト

- 日本語文章を自然・正確・一貫に仕上げる Agent Skill「super-natural-japanese」の開発リポジトリ
- リポジトリ直下がそのままスキルフォルダ(`SKILL.md` がスキル本体)
- ドキュメント・コミットメッセージ・PR 説明は日本語で書く

## 構成

- `SKILL.md`: スキルの手順とルール。フロントマターの `name` は `super-natural-japanese` から変えない
- `references/*.md`: 必要なときだけ読む参照資料。`SKILL.md` から相対パスで参照されている
- `scripts/check.py`: 標準ライブラリのみで動く軽量チェッカー。Python 3.8 互換を保つ(外部依存を追加しない)
- `evals/evals.json`: スキル改善時に確認する評価ケースと過去の指摘
- `tests/test_check.py`: `check.py` の回帰テスト

## コマンド

```bash
# テスト(必ず通してから push する)
python3 -m unittest discover -s tests -v

# チェッカーの動作確認
echo "本文" | python3 scripts/check.py --register business -
```

## 変更時のルール

- `scripts/check.py` を変えたら、その挙動を固定するテストを `tests/test_check.py` に追加する
- 検出パターンを追加するときは、`references/` の該当ファイル(誤り例が書かれている)にも説明を足す
- `references/*.md` には「誤りの例」が意図的に含まれているため、`check.py` を references に対して通しても ERROR が出るのは正常
- `SKILL.md` や `references/` を変えたら `evals/evals.json` の全ケースを確認し、`CHANGELOG.md` の `[Unreleased]` に記録する
- スキルの中身を大きく変えるときは、先に「なぜ」を PR 説明に書く

## ブランチ運用

- `main` へ直接 push しない。作業ブランチから `main` 向けの Pull Request を作成する
- PR は `.github/PULL_REQUEST_TEMPLATE.md` の項目に沿って記入する

## コーディング規約

- 文字コードは UTF-8、改行コードは LF(`.editorconfig` / `.gitattributes` に従う)
- Python はスペース 4、それ以外はスペース 2
- 秘密情報はコミットしない
