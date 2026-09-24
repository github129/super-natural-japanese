# 変更履歴

このスキルの変更を新しい順に記録します。書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に準じます。

## [Unreleased]

### 変更

- 既存文を直すときの歯止めを、依頼の範囲で切り替えるようにした。範囲が狭い依頼では構成を変えず、「分かりやすく書き直して」のような依頼では見出し・箇条書き・順番の組み替えも範囲に入れる(iteration-4 で公用文の書き直しに歯止めが効きすぎていたため)
- 診断の返答では重大度を日本語で示し、ERROR / WARN / INFO を出さないと SKILL.md に明記
- `references/design.md` の例文を評価題材と重ならない Google スプレッドシートに差し替え、例文を流用しないと明記。型どおりの元文を組み替える前後の例を追加
- `references/keigo.md` と `scripts/check.py` に、数量を述べるだけの「〜となります」を追加
- `tools/eval_setup.py --runs N` と、回ごとに A/B を組む `tools/eval_blind.py`(採点ディレクトリは `blind/pair-K`)。評価結果は `evals/results/iteration-4.md`
- SKILL.md §2 に「既存文を直すとき — 直しすぎない」を追加。keep / change の割り振り、文の順番と記号の保持、掃引しない、事実は残す、補足の明示。design.md §7 に keep / change の表と型どおりの元文を直す手順、hyoki.md と ai-patterns.md に整合する一文を追加(参考元 coji/natural-japanese の「改稿は掃引ではない」に学ぶ)。評価結果は `evals/results/iteration-2.md`
- `tools/eval_setup.py` に `old_skill` 設定(`--old-skill-path`)を追加し、変更前のスキルとの比較ができるようにした

### 追加

- スキル一式(`SKILL.md`、`references/`、`scripts/check.py`、`evals/`)をリポジトリに取り込み
- `scripts/check.py` の回帰テスト(`tests/test_check.py`)と GitHub Actions による CI
- 評価基盤: 評価ケースを 10 件に拡充(`evals/evals.json`、`evals/inputs/`)、機械採点と A/B 伏せ採点のスクリプト(`tools/eval_*.py`)、手順(`evals/README.md`)、iteration-1 の結果(`evals/results/iteration-1.md`)
- 利用者がダウンロードしてすぐ使える配布用 zip(`Skills/super-natural-japanese.zip`)と、それを生成・検証する `tools/build_skill_zip.py`
