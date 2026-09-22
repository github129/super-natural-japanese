# 評価の手順

スキルを変えたら、変更が本当に効いたかをここで確かめます。評価は 3 層です。

| 層 | 何を見るか | 誰が判定するか |
| --- | --- | --- |
| 機械判定(`checks`) | ら抜きが残っていない、数字が保たれている、字数、禁止表現など | `tools/eval_grade.py` |
| 判断(`expectations`) | 型に流れていないか、読み手の問いの順か、事実の捏造がないか | A/B を伏せた採点エージェント |
| 総合 | 2 つの成果物のどちらが自然で使えるか | 同上(`preference`) |

## ファイル

- `evals.json`: 評価ケース。各ケースに `prompt`(依頼文)、`files`(入力)、`register`、`checks`(機械判定)、`expectations`(判断)、`past_feedback`(過去の指摘)を持つ
- `inputs/`: 依頼に添付する入力ファイル
- `../tools/eval_setup.py`: 実行用ワークスペースを組み立て、実行エージェントに渡す指示文 `prompt.md` を書く
- `../tools/eval_grade.py`: 機械判定を実行し、`judgments.json` があれば統合して `grading.json` を書く
- `../tools/eval_blind.py`: 判断系の観点を A/B を伏せて採点するための準備と、結果の統合

## 一周の回し方

ワークスペースはリポジトリの外(例: `../super-natural-japanese-workspace/iteration-N/`)に作ります。結果はコミットしません。

```bash
WS=../super-natural-japanese-workspace/iteration-1

# 1. ワークスペースを作る(各ケースに with_skill / without_skill の run ディレクトリと prompt.md ができる)
python3 tools/eval_setup.py $WS

# 2. 各 run の prompt.md をサブエージェントに渡して実行する(スキルあり・なしを同時に起動する)
#    完了通知の total_tokens と duration_ms を <run>/timing.json に保存する

# 3. 機械判定
for d in $WS/eval-*/*/run-1; do
  id=$(basename $(dirname $(dirname $d)) | sed -E 's/eval-0*([0-9]+)-.*/\1/')
  python3 tools/eval_grade.py $d --eval-id $id
done

# 4. 判断系の観点を A/B を伏せて採点する
python3 tools/eval_blind.py $WS            # blind/ と grader_prompt.md を作る
#    各ケースの blind/grader_prompt.md を採点エージェントに渡し、verdict.json を書かせる
python3 tools/eval_blind.py $WS --merge    # verdict.json を各 run の judgments.json に戻す
#    3. をもう一度実行すると grading.json に判断系の結果が入る

# 5. 集計とビューアー(skill-creator の同梱スクリプト)
python -m scripts.aggregate_benchmark $WS --skill-name super-natural-japanese   # skill-creator のディレクトリで実行
python eval-viewer/generate_review.py $WS --skill-name super-natural-japanese --benchmark $WS/benchmark.json --static $WS/review.html
```

## 結果の読み方

- 機械判定は、スキルあり・なしの両方で通ることが多い(素の Claude も明らかな誤りは避ける)。**差が出るのは判断系と総合評価**なので、そちらを中心に見る
- `preference` がスキルなし側に付いたケースは、スキルの手順が逆効果になっている疑いがある。`reasoning` と `issues` を読んで原因を SKILL.md か references/ に反映する
- 採点エージェントが `issues` に挙げた観点外の問題は、次の周で `checks` か `expectations` に昇格させる
- 直したら `past_feedback` に何が問題だったかを一行で残す

## ケースを足すとき

1. 実際の依頼に近い `prompt` を書く(短すぎる依頼はスキルの差が出ない)
2. 入力が要るなら `inputs/` に置き、意図した誤りを仕込む
3. `checks` は「正しくやらないと通らない」ものだけにする。ファイルの存在や単語の有無だけの判定は差がつかない
4. `expectations` は 1〜3 個。人が読んで yes/no が決まる文にする
