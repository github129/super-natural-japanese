# 変更履歴

このスキルの変更を新しい順に記録します。書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に準じます。

## [Unreleased]

### 追加

- スキル一式(`SKILL.md`、`references/`、`scripts/check.py`、`evals/`)をリポジトリに取り込み
- `scripts/check.py` の回帰テスト(`tests/test_check.py`)と GitHub Actions による CI
- 評価基盤: 評価ケースを 10 件に拡充(`evals/evals.json`、`evals/inputs/`)、機械採点と A/B 伏せ採点のスクリプト(`tools/eval_*.py`)、手順(`evals/README.md`)、iteration-1 の結果(`evals/results/iteration-1.md`)
- 利用者がダウンロードしてすぐ使える配布用 zip(`Skills/super-natural-japanese.zip`)と、それを生成・検証する `tools/build_skill_zip.py`
