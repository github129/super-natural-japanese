# 変更履歴

このスキルの変更を新しい順に記録します。書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に準じます。

## [Unreleased]

### 変更

- SKILL.md §2 に「既存文を直すとき — 直しすぎない」を追加。keep / change の割り振り、文の順番と記号の保持、掃引しない、事実は残す、補足の明示。design.md §7 に keep / change の表と型どおりの元文を直す手順、hyoki.md と ai-patterns.md に整合する一文を追加(参考元 coji/natural-japanese の「改稿は掃引ではない」に学ぶ)。評価結果は `evals/results/iteration-2.md`
- `tools/eval_setup.py` に `old_skill` 設定(`--old-skill-path`)を追加し、変更前のスキルとの比較ができるようにした

### 追加

- スキル一式(`SKILL.md`、`references/`、`scripts/check.py`、`evals/`)をリポジトリに取り込み
- `scripts/check.py` の回帰テスト(`tests/test_check.py`)と GitHub Actions による CI
- 評価基盤: 評価ケースを 10 件に拡充(`evals/evals.json`、`evals/inputs/`)、機械採点と A/B 伏せ採点のスクリプト(`tools/eval_*.py`)、手順(`evals/README.md`)、iteration-1 の結果(`evals/results/iteration-1.md`)
- 利用者がダウンロードしてすぐ使える配布用 zip(`Skills/super-natural-japanese.zip`)と、それを生成・検証する `tools/build_skill_zip.py`
