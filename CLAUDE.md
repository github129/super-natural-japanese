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
- `evals/evals.json`: 評価ケース(依頼文・入力・機械判定 `checks`・判断 `expectations`・過去の指摘 `past_feedback`)。回し方は `evals/README.md`、結果は `evals/results/`
- `tools/eval_setup.py` / `eval_grade.py` / `eval_blind.py`: 評価の実行準備・機械採点・A/B 伏せ採点。ワークスペースはリポジトリの外に作り、結果はコミットしない
- `tests/test_check.py`: `check.py` の回帰テスト
- `Skills/super-natural-japanese.zip`: 利用者がダウンロードしてすぐ使うための配布用 zip。手で編集せず `tools/build_skill_zip.py` で生成する
- `tools/build_skill_zip.py`: 配布用 zip の生成(`--check` で検証)。zip に入れるファイルの一覧もここで管理する

## コマンド

```bash
# テスト(必ず通してから push する)
python3 -m unittest discover -s tests -v

# チェッカーの動作確認
echo "本文" | python3 scripts/check.py --register business -

# 配布用 zip を作り直す(スキルのファイルを変えたら必ず実行してコミットする)
python3 tools/build_skill_zip.py
python3 tools/build_skill_zip.py --check   # 最新か確認(CI でも実行される)
```

## 変更時のルール

- `scripts/check.py` を変えたら、その挙動を固定するテストを `tests/test_check.py` に追加する
- 検出パターンを追加するときは、`references/` の該当ファイル(誤り例が書かれている)にも説明を足す
- `references/*.md` には「誤りの例」が意図的に含まれているため、`check.py` を references に対して通しても ERROR が出るのは正常
- `SKILL.md` や `references/` を変えたら、`evals/README.md` の手順で全ケースをスキルあり・なしで再実行し、結果を `evals/results/iteration-N.md` と `past_feedback` に残してから `CHANGELOG.md` の `[Unreleased]` に記録する
- スキルの中身を大きく変えるときは、先に「なぜ」を PR 説明に書く
- `SKILL.md`・`README.md`・`CHANGELOG.md`・`references/`・`scripts/`・`evals/` のどれかを変えたら、`python3 tools/build_skill_zip.py` で `Skills/super-natural-japanese.zip` を作り直して同じコミットに含める(古いままだと CI が失敗する)

## ブランチ運用

- `main` へ直接 push しない。作業ブランチから `main` 向けの Pull Request を作成する
- PR は `.github/PULL_REQUEST_TEMPLATE.md` の項目に沿って記入する

## コーディング規約

- 文字コードは UTF-8、改行コードは LF(`.editorconfig` / `.gitattributes` に従う)
- Python はスペース 4、それ以外はスペース 2
- 秘密情報はコミットしない
