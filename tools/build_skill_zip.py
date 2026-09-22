#!/usr/bin/env python3
"""配布用 zip(Skills/super-natural-japanese.zip)を作る・検証する。

zip には、スキルとして動くのに必要なファイルだけを、
`super-natural-japanese/` フォルダを先頭に付けて入れる。
展開したフォルダをそのまま `.claude/skills/` や `.github/skills/` に置けば使える。

usage:
  python3 tools/build_skill_zip.py          # zip を作り直す
  python3 tools/build_skill_zip.py --check  # zip の中身がソースと一致するか確かめる(CI 用)
"""
import argparse
import io
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_NAME = "super-natural-japanese"
ZIP_PATH = os.path.join(ROOT, "Skills", SKILL_NAME + ".zip")

# zip に入れるもの。ファイルは個別に、ディレクトリは中身をすべて(隠しファイルと __pycache__ を除く)。
INCLUDE_FILES = ["SKILL.md", "README.md", "CHANGELOG.md"]
INCLUDE_DIRS = ["references", "scripts", "evals"]

# 再現性のため、zip 内のタイムスタンプは固定する
FIXED_DATE = (2020, 1, 1, 0, 0, 0)


def collect():
    """zip に入れる (アーカイブ内パス, 実ファイルパス) を並び順を固定して返す。"""
    entries = []
    for rel in INCLUDE_FILES:
        entries.append((rel, os.path.join(ROOT, rel)))
    for d in INCLUDE_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(n for n in dirnames if not n.startswith(".") and n != "__pycache__")
            for name in sorted(filenames):
                if name.startswith(".") or name.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
                entries.append((rel, full))
    missing = [rel for rel, full in entries if not os.path.isfile(full)]
    if missing:
        sys.exit("missing files: " + ", ".join(missing))
    return entries


def expected_contents():
    """{アーカイブ内パス: bytes}"""
    out = {}
    for rel, full in collect():
        with open(full, "rb") as fh:
            out[SKILL_NAME + "/" + rel] = fh.read()
    return out


def build():
    contents = expected_contents()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for arc in sorted(contents):
            info = zipfile.ZipInfo(arc, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, contents[arc])
    os.makedirs(os.path.dirname(ZIP_PATH), exist_ok=True)
    with open(ZIP_PATH, "wb") as fh:
        fh.write(buf.getvalue())
    print("wrote %s (%d files, %d bytes)" % (os.path.relpath(ZIP_PATH, ROOT), len(contents), len(buf.getvalue())))


def check():
    if not os.path.isfile(ZIP_PATH):
        sys.exit("%s がありません。python3 tools/build_skill_zip.py で作成してください。" % os.path.relpath(ZIP_PATH, ROOT))
    expected = expected_contents()
    with zipfile.ZipFile(ZIP_PATH) as zf:
        actual = {i.filename: zf.read(i) for i in zf.infolist() if not i.is_dir()}
    problems = []
    for name in sorted(set(expected) | set(actual)):
        if name not in actual:
            problems.append("zip にない: " + name)
        elif name not in expected:
            problems.append("ソースにない: " + name)
        elif expected[name] != actual[name]:
            problems.append("内容が違う: " + name)
    if problems:
        print("\n".join(problems))
        sys.exit("Skills/%s.zip が古いです。python3 tools/build_skill_zip.py で作り直してコミットしてください。" % SKILL_NAME)
    print("ok: %s は最新です(%d files)" % (os.path.relpath(ZIP_PATH, ROOT), len(expected)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="zip がソースと一致するか確認するだけ")
    args = ap.parse_args()
    check() if args.check else build()


if __name__ == "__main__":
    main()
