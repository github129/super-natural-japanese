#!/usr/bin/env python3
"""評価実行用のワークスペースを組み立て、各実行に渡す指示文を書き出す。

usage:
  python3 tools/eval_setup.py <workspace>/iteration-N [--configs with_skill,without_skill]
  python3 tools/eval_setup.py <workspace>/iteration-N --configs with_skill,old_skill --old-skill-path <snapshot>/SKILL.md

作るもの(ケースごと):
  eval-NN-<name>/eval_metadata.json
  eval-NN-<name>/<config>/eval_metadata.json      (ビューアーが親ディレクトリから探すため)
  eval-NN-<name>/<config>/run-K/inputs/...        (入力ファイルのコピー)
  eval-NN-<name>/<config>/run-K/outputs/          (成果物の保存先。ファイル編集の依頼では入力をここにコピー)
  eval-NN-<name>/<config>/run-K/prompt.md         (実行エージェントに渡す指示文)
  (K は 1..--runs。同じ指示文で複数回実行してぶれを見る)
"""
import argparse
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MD = os.path.join(ROOT, "SKILL.md")

WITH_SKILL_HEAD = """あなたは日本語文章のタスクを実行するエージェントです。
まず {skill} を読み、その手順に従ってタスクを実行してください。参照ファイルやスクリプトも SKILL.md の指示どおりに使ってください。
"""
WITHOUT_SKILL_HEAD = """あなたは日本語文章のタスクを実行するエージェントです。
注意: 比較実験のため、{root} 以下のファイル(SKILL.md、references/、scripts/ など)は読まないでください。入力ファイルは下記のパスから読んでください。
"""
BODY = """
## タスク(ユーザーからの依頼)

{prompt}

## 入力ファイル

{inputs}

## 成果物の保存先

{save}
成果物を保存したら、最後に「done」とだけ返答してください。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("iteration_dir")
    ap.add_argument("--configs", default="with_skill,without_skill",
                    help="with_skill(現行スキル) / without_skill(スキルなし) / old_skill(--old-skill-path のスナップショット)")
    ap.add_argument("--old-skill-path", help="old_skill 設定で読ませる SKILL.md のパス(比較基準のスナップショット)")
    ap.add_argument("--runs", type=int, default=1, help="各設定を何回実行するか(run-1 .. run-N)。ぶれを抑えるなら 3")
    args = ap.parse_args()
    if "old_skill" in args.configs and not args.old_skill_path:
        ap.error("old_skill を使うには --old-skill-path が必要")
    evals = json.load(open(os.path.join(ROOT, "evals", "evals.json"), encoding="utf-8"))
    configs = args.configs.split(",")

    for ev in evals["evals"]:
        eval_dir = os.path.join(args.iteration_dir, "eval-%02d-%s" % (ev["id"], ev["name"]))
        meta = {"eval_id": ev["id"], "eval_name": ev["name"], "prompt": ev["prompt"],
                "assertions": [c["text"] for c in ev.get("checks", [])] + ev.get("expectations", [])}
        os.makedirs(eval_dir, exist_ok=True)
        json.dump(meta, open(os.path.join(eval_dir, "eval_metadata.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        edit_in_place = ev["name"] == "jp-style-unify"
        for cfg, r in [(c, r) for c in configs for r in range(1, args.runs + 1)]:
            cfg_dir = os.path.join(eval_dir, cfg)
            run_dir = os.path.join(cfg_dir, "run-%d" % r)
            outputs = os.path.join(run_dir, "outputs")
            inputs = os.path.join(run_dir, "inputs")
            os.makedirs(outputs, exist_ok=True)
            json.dump(meta, open(os.path.join(cfg_dir, "eval_metadata.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

            input_lines = []
            if edit_in_place:
                src = os.path.join(ROOT, "evals", "inputs", "jp-style")
                for name in (".jp-style.txt",):
                    shutil.copy(os.path.join(src, name), os.path.join(outputs, name))
                shutil.copytree(os.path.join(src, "docs"), os.path.join(outputs, "docs"), dirs_exist_ok=True)
                input_lines.append("- 作業ディレクトリ: %s(この中の docs/ と .jp-style.txt)" % outputs)
                save = ("- ファイルを直す依頼なので、%s/docs/ 以下のファイルをその場で編集してください。output.md は作りません。\n"
                        "- 何をどう変えたかの短い説明は %s/user_notes.md に書いてください。" % (outputs, outputs))
            else:
                for rel in ev.get("files", []):
                    os.makedirs(inputs, exist_ok=True)
                    dst = os.path.join(inputs, os.path.basename(rel))
                    shutil.copy(os.path.join(ROOT, rel), dst)
                    input_lines.append("- " + dst)
                if ev["name"] == "diagnose-only":
                    save = ("- 依頼への返答本文(問題箇所・理由・修正案の一覧と、最後の一言)を %s/output.md に保存してください。\n"
                            "- 元のメールの書き換え版は作らないでください。" % outputs)
                else:
                    save = ("- 完成した文章の本文だけを %s/output.md に保存してください(設計メモ・説明・変更点の要約・見出し「台本」などは含めない)。\n"
                            "- ユーザーに添える説明(変更点の要約など)があれば %s/user_notes.md に書いてください。" % (outputs, outputs))
            if cfg == "with_skill":
                head = WITH_SKILL_HEAD.format(skill=SKILL_MD)
            elif cfg == "old_skill":
                head = WITH_SKILL_HEAD.format(skill=os.path.abspath(args.old_skill_path))
            else:
                head = WITHOUT_SKILL_HEAD.format(root=ROOT)
            prompt = head + BODY.format(prompt=ev["prompt"], inputs="\n".join(input_lines) or "なし", save=save)
            with open(os.path.join(run_dir, "prompt.md"), "w", encoding="utf-8") as fh:
                fh.write(prompt)
        print(eval_dir)


if __name__ == "__main__":
    main()
