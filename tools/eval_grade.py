#!/usr/bin/env python3
"""評価ケースの出力を機械採点して grading.json を書く。

usage:
  python3 tools/eval_grade.py <run_dir> --eval-id N [--evals evals/evals.json]

<run_dir>/outputs/ にある成果物に対して evals.json の checks を実行する。
<run_dir>/judgments.json(人または採点エージェントが書いた判断系の結果)があれば統合し、
<run_dir>/timing.json があれば timing に取り込む。結果は <run_dir>/grading.json。
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK_PY = os.path.join(ROOT, "scripts", "check.py")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def run_checker(path, register):
    p = subprocess.run([sys.executable, CHECK_PY, "--register", register, "--json", path],
                       capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        return None, "check.py failed: " + p.stderr.strip()
    return json.loads(p.stdout), ""


def grade_check(c, outputs_dir):
    kind = c["check"]
    target = os.path.join(outputs_dir, c.get("file", "output.md"))
    if not os.path.isfile(target):
        return False, "成果物 %s がない" % os.path.relpath(target, outputs_dir)
    text = read(target)
    flags = re.M if "M" in c.get("flags", "") else 0

    if kind == "checker_no_error":
        data, err = run_checker(target, c.get("register", "business"))
        if data is None:
            return False, err
        errors = [f for f in data["findings"] if f["severity"] == "ERROR"]
        if errors:
            return False, "ERROR %d 件: " % len(errors) + "; ".join(
                "%s「%s」" % (f["message"], f["excerpt"][:30]) for f in errors[:4])
        return True, "ERROR=0 (WARN=%d INFO=%d)" % (data["counts"].get("WARN", 0), data["counts"].get("INFO", 0))
    if kind == "max_chars":
        n = len(re.sub(r"\s", "", text))
        return n <= c["n"], "空白を除いて %d 字(上限 %d)" % (n, c["n"])
    if kind == "regex":
        m = re.search(c["pattern"], text, flags)
        return (m is not None), ("一致: 「%s」" % m.group(0)[:40] if m else "「%s」に一致する箇所がない" % c["pattern"])
    if kind == "not_regex":
        ms = list(re.finditer(c["pattern"], text, flags))
        if ms:
            return False, "%d 件残っている: 「%s」" % (len(ms), text[max(0, ms[0].start() - 10):ms[0].end() + 10].replace("\n", " "))
        return True, "該当なし"
    if kind == "count_max":
        n = len(re.findall(c["pattern"], text, flags))
        return n <= c["n"], "%d 回(上限 %d)" % (n, c["n"])
    if kind == "regex_before_half":
        m = re.search(c["pattern"], text, flags)
        if not m:
            return False, "「%s」がない" % c["pattern"]
        pos = m.start() / max(1, len(text))
        return pos < 0.5, "最初の出現位置は全体の %d%%" % round(pos * 100)
    if kind == "line_count_equal":
        ref = read(os.path.join(ROOT, c["ref"]))
        a, b = text.count("\n"), ref.count("\n")
        return a == b, "出力 %d 行 / 元 %d 行" % (a, b)
    return False, "未知の check: " + kind


def main():
    ap = argparse.ArgumentParser(description="評価出力の機械採点")
    ap.add_argument("run_dir")
    ap.add_argument("--eval-id", type=int, required=True)
    ap.add_argument("--evals", default=os.path.join(ROOT, "evals", "evals.json"))
    args = ap.parse_args()

    evals = json.load(open(args.evals, encoding="utf-8"))
    ev = next((e for e in evals["evals"] if e["id"] == args.eval_id), None)
    if ev is None:
        sys.exit("eval id %d が evals.json にない" % args.eval_id)
    outputs_dir = os.path.join(args.run_dir, "outputs")

    expectations = []
    for c in ev.get("checks", []):
        passed, evidence = grade_check(c, outputs_dir)
        expectations.append({"text": "[機械] " + c["text"], "passed": bool(passed), "evidence": evidence})

    jpath = os.path.join(args.run_dir, "judgments.json")
    if os.path.isfile(jpath):
        for j in json.load(open(jpath, encoding="utf-8")).get("expectations", []):
            expectations.append({"text": "[判断] " + j["text"], "passed": bool(j["passed"]), "evidence": j.get("evidence", "")})

    passed = sum(1 for e in expectations if e["passed"])
    total = len(expectations)
    grading = {
        "eval_id": ev["id"], "eval_name": ev.get("name", ""),
        "expectations": expectations,
        "summary": {"passed": passed, "failed": total - passed, "total": total,
                    "pass_rate": round(passed / total, 3) if total else 0.0},
    }
    # 所要時間とトークン数は <run_dir>/timing.json のまま残す(集計スクリプトがそこから読む)
    with open(os.path.join(args.run_dir, "grading.json"), "w", encoding="utf-8") as fh:
        json.dump(grading, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("%s: %d/%d" % (os.path.relpath(args.run_dir), passed, total))
    for e in expectations:
        if not e["passed"]:
            print("  x", e["text"], "--", e["evidence"])


if __name__ == "__main__":
    main()
