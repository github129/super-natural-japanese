#!/usr/bin/env python3
"""人の判断が要る観点(expectations)を、A/B を伏せて採点するための準備と結果の統合。

usage:
  python3 tools/eval_blind.py <iteration_dir>            # 各ケースに blind/{A,B}/ と grader_prompt.md を作る
  python3 tools/eval_blind.py <iteration_dir> --merge    # blind/verdict.json を各 run の judgments.json に戻す

準備: 2 つの設定(既定: with_skill / without_skill)の成果物を run-K ごとに組にして、ランダムに A と B に
      割り当ててコピーし、採点エージェントに渡す指示文 blind/pair-K/grader_prompt.md を書く(集計スクリプトが run-* を設定と誤認しないよう pair-K と呼ぶ)。割り当ては mapping.json に記録する。
統合: 採点エージェントが書いた blind/pair-K/verdict.json を mapping.json で元の設定に戻し、
      <config>/run-K/judgments.json に保存する。その後 tools/eval_grade.py を実行すると grading.json に統合される。
"""
import argparse
import json
import os
import random
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROMPT = """あなたは日本語文章の品質を採点する審査員です。同じ依頼に対する 2 つの成果物 A と B を比べ、次の観点を採点してください。どちらが誰の(何の)成果物かは伏せられています。先入観なく、本文の証拠だけで判断してください。

## 依頼(ユーザーが出したもの)

{prompt}

## 入力ファイル(依頼に添付されていたもの)

{inputs}

## 成果物

- A: {blind}/A/{target}
- B: {blind}/B/{target}

## 採点する観点(A と B それぞれについて、満たすなら passed=true)

{exps}

観点の判定では、満たす証拠を本文から具体的に引用してください。判断に迷うときは「満たしていない」に倒してください(証明責任は成果物側にあります)。

## 総合評価

観点の採点とは別に、「依頼した人がそのまま使えるか」「日本語として自然で、読み手に向いているか」「AI が書いた型どおりの文章に見えないか」の 3 点で A と B を比べ、どちらが優れているか(A / B / tie)と理由を書いてください。観点に含まれていない問題(不自然な言い回し、事実の追加や欠落、依頼と違うこと、演出や広告調など)に気づいたら issues に列挙してください。

## 出力

次の JSON を {blind}/verdict.json に保存してください(それ以外のファイルは作らない)。保存したら「done」とだけ返答してください。

{{
  "A": {{"expectations": [{{"text": "<観点の文>", "passed": true, "evidence": "<引用>"}}], "issues": ["<観点外の問題>"]}},
  "B": {{"expectations": [...], "issues": [...]}},
  "preference": "A" | "B" | "tie",
  "reasoning": "<総合評価の理由。A と B の違いが分かるように具体的に>"
}}
"""


def load_evals():
    data = json.load(open(os.path.join(ROOT, "evals", "evals.json"), encoding="utf-8"))
    return {e["id"]: e for e in data["evals"]}


def eval_dirs(iteration_dir):
    for name in sorted(os.listdir(iteration_dir)):
        if name.startswith("eval-"):
            yield int(name.split("-")[1]), os.path.join(iteration_dir, name)


def run_names(edir, configs):
    """両方の設定に存在する run-K の名前を順に返す。"""
    sets = []
    for cfg in configs:
        d = os.path.join(edir, cfg)
        sets.append({n for n in os.listdir(d) if n.startswith("run-")} if os.path.isdir(d) else set())
    common = set.intersection(*sets) if sets else set()
    return sorted(common, key=lambda n: int(n.split("-")[1]))


def build(iteration_dir, configs, seed):
    evals = load_evals()
    rng = random.Random(seed)
    for eid, edir in eval_dirs(iteration_dir):
        ev = evals[eid]
        shutil.rmtree(os.path.join(edir, "blind"), ignore_errors=True)
        in_place = ev["name"] == "jp-style-unify"
        for run in run_names(edir, configs):
            blind = os.path.join(edir, "blind", "pair-" + run.split("-")[1])
            os.makedirs(blind)
            order = list(configs)
            rng.shuffle(order)
            mapping = {"A": order[0], "B": order[1]}
            json.dump(mapping, open(os.path.join(blind, "mapping.json"), "w"))
            for label, cfg in mapping.items():
                src = os.path.join(edir, cfg, run, "outputs")
                if in_place:
                    shutil.copytree(os.path.join(src, "docs"), os.path.join(blind, label, "docs"))
                else:
                    os.makedirs(os.path.join(blind, label))
                    if os.path.isfile(os.path.join(src, "output.md")):
                        shutil.copy(os.path.join(src, "output.md"), os.path.join(blind, label, "output.md"))
            inputs = "\n".join("- " + os.path.join(ROOT, f) for f in ev.get("files", [])) or "なし"
            exps = "\n".join("%d. %s" % (i + 1, t) for i, t in enumerate(ev["expectations"]))
            target = "docs/ 以下のファイル(元の入力と比べて何が変わったかを見る)" if in_place else "output.md"
            text = PROMPT.format(prompt=ev["prompt"], inputs=inputs, blind=blind, target=target, exps=exps)
            open(os.path.join(blind, "grader_prompt.md"), "w", encoding="utf-8").write(text)
            print(os.path.basename(edir), run, mapping)


def merge(iteration_dir):
    for eid, edir in eval_dirs(iteration_dir):
        broot = os.path.join(edir, "blind")
        if not os.path.isdir(broot):
            continue
        pairs = sorted((n for n in os.listdir(broot) if n.startswith("pair-")), key=lambda n: int(n.split("-")[1]))
        for pair in pairs:
            run = "run-" + pair.split("-")[1]
            blind = os.path.join(broot, pair)
            vpath = os.path.join(blind, "verdict.json")
            if not os.path.isfile(vpath):
                print(os.path.basename(edir), run, ": verdict.json がない")
                continue
            mapping = json.load(open(os.path.join(blind, "mapping.json")))
            verdict = json.load(open(vpath, encoding="utf-8"))
            pref = verdict.get("preference", "tie")
            for label, cfg in mapping.items():
                side = verdict.get(label, {})
                out = {
                    "expectations": side.get("expectations", []),
                    "issues": side.get("issues", []),
                    "preferred": (pref == label),
                    "tie": (pref == "tie"),
                    "reasoning": verdict.get("reasoning", ""),
                }
                run_dir = os.path.join(edir, cfg, run)
                with open(os.path.join(run_dir, "judgments.json"), "w", encoding="utf-8") as fh:
                    json.dump(out, fh, ensure_ascii=False, indent=1)
            winner = mapping.get(pref, "tie")
            print("%s %s: preference=%s -> %s" % (os.path.basename(edir), run, pref, winner))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("iteration_dir")
    ap.add_argument("--configs", default="with_skill,without_skill")
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    if args.merge:
        merge(args.iteration_dir)
    else:
        build(args.iteration_dir, args.configs.split(","), args.seed)


if __name__ == "__main__":
    main()
