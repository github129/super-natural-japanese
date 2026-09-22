#!/usr/bin/env python3
"""super-natural-japanese checker.

Python 標準ライブラリだけで動く、日本語文章の軽量チェッカー。
敬語の誤用・ら抜き・さ入れ・文体混在・表記ゆれ・AI調・長文などを検出する。
検出結果は「疑い」であり、直すかどうかは文脈で判断すること。

usage:
  python3 check.py [--register business|kouyou|chat|general] [--rules FILE]
                   [--max-len N] [--json] FILE|-
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict

SEV_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}
HIRA = "ぁ-ゖ"
KANJI = "一-龥々"
KATA = "ァ-ヶー"

# ---------------------------------------------------------------- 前処理

def load_text(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def mask_code(text):
    """コードブロック・インラインコード・URL を同じ長さの空白に置き換える（行番号を保つ）。"""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"```.*?```", blank, text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", blank, text)
    text = re.sub(r"https?://\S+", blank, text)
    return text


STRUCT_LINE = re.compile(r"^\s*(#|[-*+・●■◆]|\d+[.)．]|\||>)")


def split_sentences(text):
    """(line_no, sentence, is_structural) のリストを返す。"""
    out = []
    for ln, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        structural = bool(STRUCT_LINE.match(line))
        for s in re.findall(r"[^。！？!?]+[。！？!?]?", line):
            s2 = s.strip()
            if s2:
                out.append((ln, s2, structural))
    return out


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def excerpt(text, start, end, pad=12):
    ls = text.rfind("\n", 0, start) + 1
    le = text.find("\n", end)
    le = len(text) if le < 0 else le
    a = max(ls, start - pad)
    b = min(le, end + pad)
    return text[a:b].strip()


class Findings:
    def __init__(self):
        self.items = []

    def add(self, sev, cat, line, msg, ex="", fix=""):
        self.items.append({"severity": sev, "category": cat, "line": line,
                           "message": msg, "excerpt": ex, "suggestion": fix})


def scan(text, pattern, f, sev, cat, msg, fix="", flags=0):
    for m in re.finditer(pattern, text, flags):
        f.add(sev, cat, line_of(text, m.start()), msg,
              excerpt(text, m.start(), m.end()), fix)


# ---------------------------------------------------------------- 敬語

DOUBLE_KEIGO = [
    ("おっしゃられ", "おっしゃる／おっしゃった"), ("ご覧になられ", "ご覧になる／ご覧になった"),
    ("お見えになられ", "お見えになる"), ("お越しになられ", "お越しになる"),
    ("いらっしゃられ", "いらっしゃる"), ("お帰りになられ", "お帰りになる"),
    ("お読みになられ", "お読みになる"), ("召し上がられ", "召し上がる"),
    ("お聞きになられ", "お聞きになる"), ("拝見させていただ", "拝見します／拝見いたします"),
    ("拝読させていただ", "拝読します／拝読いたします"), ("拝聴させていただ", "拝聴します"),
    ("お伺いさせていただ", "伺います"), ("伺わせていただ", "伺います"),
    ("お伺いいたし", "伺います"),
]

SA_IRE = ["休まさせ", "読まさせ", "行かさせ", "書かさせ", "言わさせ", "帰らさせ", "やらさせ",
          "使わさせ", "送らさせ", "待たさせ", "取らさせ", "作らさせ", "歌わさせ", "撮らさせ",
          "座らさせ", "頑張らさせ", "手伝わさせ", "伺わさせ", "買わさせ", "会わさせ", "選ばさせ",
          "急がさせ", "泳がさせ", "遊ばさせ", "飲まさせ", "住まさせ", "切らさせ", "乗らさせ"]

RA_NUKI_STEMS = ["見", "来", "こ", "食べ", "寝", "着", "出", "起き", "決め", "考え", "覚え",
                 "教え", "変え", "答え", "投げ", "止め", "信じ", "感じ", "生き", "借り", "降り",
                 "調べ", "比べ", "続け", "受け", "伝え", "集め", "始め", "辞め", "逃げ", "避け",
                 "見つけ", "出かけ", "着替え", "耐え", "任せ", "見せ"]


def check_keigo(text, f, register):
    for bad, good in DOUBLE_KEIGO:
        sev = "INFO" if bad == "お伺いいたし" else ("WARN" if bad.startswith(("お伺い", "伺わ")) else "ERROR")
        msg = "二重敬語（慣用として許容される場合もある）" if sev == "INFO" else "二重敬語"
        scan(text, re.escape(bad), f, sev, "敬語", msg, fix=good)
    # 謙譲語「ご〜する」に「れる」を付けた誤用: ご説明される / お待ちされる
    scan(text, rf"[おご][{KANJI}]{{1,3}}[{HIRA}]?される", f, "WARN", "敬語",
         "謙譲の「お／ご〜する」＋「れる」の疑い（尊敬なら「ご〜になる」「〜される」）",
         fix="例: ご説明される → ご説明になる／説明される")
    # 相手の動作に謙譲: ご確認してください
    scan(text, rf"[おご][{KANJI}]{{1,3}}[{HIRA}]?して(ください|下さい|いただけ)", f, "ERROR", "敬語",
         "相手の動作に謙譲語「お／ご〜する」を使っている疑い",
         fix="例: ご確認してください → ご確認ください")
    scan(text, r"よろしかった(でしょうか|ですか)", f, "WARN", "敬語",
         "過去形の「よろしかった」は現在の確認には不自然", fix="よろしいでしょうか")
    scan(text, r"(こちら|それ|これ)[^。\n]{0,15}になります", f, "INFO", "敬語",
         "提示の「〜になります」（いわゆるバイト敬語）", fix="〜です／〜でございます")
    scan(text, r"の(ほう|方)(を|が)(お持ち|お届け|ご用意|お預かり)", f, "INFO", "敬語",
         "ぼかしの「〜のほう」", fix="「のほう」を削る")
    if register in ("business", "kouyou"):
        scan(text, r"了解(しました|いたしました|です)", f, "INFO", "敬語",
             "目上・社外には「承知しました」が無難とされる", fix="承知しました／かしこまりました")
        scan(text, r"ご苦労(様|さま)", f, "INFO", "敬語",
             "目上には「お疲れさまです」が無難とされる")
    n = len(re.findall(r"させていただ", text))
    if n >= 3:
        f.add("WARN", "敬語", 0, f"「させていただく」が{n}回。許可・恩恵がない場面では「〜します／いたします」に",
              "", "references/keigo.md の「させていただく」の節")
    for w in SA_IRE:
        scan(text, re.escape(w), f, "ERROR", "文法", "さ入れ言葉", fix=w.replace("させ", "せ"))
    stems = "|".join(sorted(map(re.escape, RA_NUKI_STEMS), key=len, reverse=True))
    for m in re.finditer(rf"({stems})れ(る|ない|なかっ|ます|ません|まし|た|て|ず)", text):
        # 「見れば」は正しいので後続候補に「ば」を入れていない
        stem = m.group(1)
        prev = text[m.start() - 1] if m.start() else ""
        if len(stem) == 1 and prev and re.match(rf"[{KANJI}]", prev):
            continue  # 意見・提出など名詞の一部
        if stem == "こ" and prev and re.match(rf"[{HIRA}]", prev):
            continue  # 「すこれ」等の誤爆回避
        f.add("ERROR", "文法", line_of(text, m.start()), "ら抜き言葉",
              excerpt(text, m.start(), m.end()), f"{stem}られ{m.group(2)}")


# ---------------------------------------------------------------- 文体・句読点

DESU = re.compile(r"(です|ます|でした|ました|ません|ませんでした|ましょう|でしょう|ください|下さい|ございます)[。！？!?」）)]*$")
DEARU = re.compile(r"(である|であった|であろう|だ|だった|だろう|ではない|のだ|ない|なかった|する|した|いる|いた|ある|あった|なる|なった|できる|できた|られる|られた|れる|れた|思う|考える)[。！？!?」）)]*$")


def check_style(text, sents, f, register):
    desu, dearu = [], []
    for ln, s, structural in sents:
        if structural or len(s) < 8 or not s.endswith(("。", "！", "？", "!", "?")):
            continue
        if DESU.search(s):
            desu.append((ln, s))
        elif DEARU.search(s):
            dearu.append((ln, s))
    if desu and dearu:
        minority, label = (dearu, "である／常体") if len(dearu) <= len(desu) else (desu, "です・ます")
        major = "です・ます" if minority is dearu else "である"
        if len(minority) >= 1 and (len(desu) + len(dearu)) >= 4:
            sev = "WARN" if register == "chat" else "ERROR"
            for ln, s in minority[:5]:
                f.add(sev, "文体", ln, f"文体の混在：主体は「{major}」だが{label}の文", s[-25:])
            if len(minority) > 5:
                f.add(sev, "文体", 0, f"文体の混在 ほか{len(minority)-5}件")
    if re.search(r"[，．]", text) and re.search(r"[、。]", text):
        f.add("ERROR", "句読点", 0, "句読点の混在（「、。」と「，．」）", "", "どちらかに統一する")
    scan(text, r"[ｦ-ﾟ]+", f, "ERROR", "表記", "半角カタカナ", fix="全角カタカナにする")
    scan(text, r"[０-９Ａ-Ｚａ-ｚ]+", f, "WARN", "表記", "全角英数字（横書きでは半角が一般的）")
    if register in ("kouyou", "business"):
        scan(text, r"(?<![一-龥])[二三四五六七八九十百千]+(?=[件個名社本台枚回点%％円])", f, "INFO", "表記",
             "横書きの数量は算用数字が原則", fix="例: 三件 → 3件")


# ---------------------------------------------------------------- 表記ゆれ

# (名前, 漢字側, かな側, 一般での推奨, 公用文での推奨)  推奨: "kana"/"kanji"/None
PAIRS = [
    ("できる", r"出来(?=[るないまたてれずそ])", r"でき(?=[るないまたてれず])", "kana", "kana"),
    ("ください", r"下さい", r"ください", "kana", "kana"),
    ("〜ていただく", r"て頂", r"ていただ", "kana", "kana"),
    ("いたします", r"致し(?=ま|て)", r"いたし(?=ま|て)", "kana", "kana"),
    ("こと", r"(?<=[るたうなの])事(?=[がをはにでもの、。])", r"こと", "kana", "kana"),
    ("とき", rf"(?<=[{HIRA}])時(?=[はにのもで、])", r"とき(?!どき)", "kana", "kana"),
    ("もの", r"(?<=[るたうなの])物(?=[がをはにでだ、。])", r"もの(?!の)", "kana", "kana"),
    ("ところ", rf"(?<=[{HIRA}])所(?=[でにがをは、])", r"ところ", "kana", "kana"),
    ("ように", rf"(?<=[{HIRA}])様(?=に|な)", r"よう(?=に|な)", "kana", "kana"),
    ("すべて", r"全て", r"すべて", "kana", "kanji"),
    ("さまざま", r"様々", r"さまざま", "kana", "kanji"),
    ("ほとんど", r"殆ど", r"ほとんど", "kana", "kana"),
    ("あるいは", r"或いは", r"あるいは", "kana", "kana"),
    ("ただし", r"但し", r"ただし", "kana", "kana"),
    ("なお", r"(?:^|(?<=[。\n]))尚、", r"(?:^|(?<=[。\n]))なお、", "kana", "kana"),
    ("また（接続詞）", r"(?:^|(?<=[。\n]))又、", r"(?:^|(?<=[。\n]))また、", "kana", "kana"),
    ("および", r"及び", r"および", None, "kanji"),
    ("または", r"又は", r"または", None, "kanji"),
    ("ため", rf"(?<=[{HIRA}])為(?=[にのだで、])", r"ため", "kana", "kana"),
    ("まで", r"迄", r"まで", "kana", "kana"),
    ("よろしく", r"宜しく", r"よろしく", "kana", "kana"),
    ("ありがとう", r"有(?:り)?難う", r"ありがとう", "kana", "kana"),
    ("さらに", r"更に", r"さらに", None, "kanji"),
    ("すでに", r"既に", r"すでに", None, "kanji"),
    ("たとえば", r"例えば", r"たとえば", None, "kanji"),
    ("なぜ", r"何故", r"なぜ", "kana", "kana"),
    ("いずれ", r"何れ", r"いずれ", "kana", "kana"),
    ("おこなう", r"行(?=[いうえっわ])(?!って|った|き|か|け|こ)", r"おこな(?=[いうえっわ])", None, "kanji"),
]


def check_hyoki(text, f, register):
    for name, kj, kn, rec_g, rec_k in PAIRS:
        a = [m.start() for m in re.finditer(kj, text, re.M)]
        b = [m.start() for m in re.finditer(kn, text, re.M)]
        rec = rec_k if register == "kouyou" else rec_g
        if a and b:
            want = {"kana": "かな", "kanji": "漢字"}.get(rec, "どちらか")
            first = min(a + b)
            f.add("WARN", "表記ゆれ", line_of(text, first),
                  f"「{name}」の表記ゆれ（漢字{len(a)}件／かな{len(b)}件）", "", f"{want}に統一")
        elif rec == "kana" and a:
            sev = "WARN" if register == "kouyou" else "INFO"
            f.add(sev, "表記", line_of(text, a[0]), f"「{name}」はかな書きが一般的（{len(a)}件）",
                  excerpt(text, a[0], a[0] + 2), name)
        elif rec == "kanji" and b and register == "kouyou":
            f.add("WARN", "表記", line_of(text, b[0]), f"公用文では「{name}」を漢字で書く（{len(b)}件）",
                  excerpt(text, b[0], b[0] + 3))
    # カタカナ語の長音ゆれ（サーバ／サーバー）
    words = Counter(re.findall(rf"[{KATA}]{{3,}}", text))
    for w in list(words):
        if w.endswith("ー") and w[:-1] in words:
            f.add("WARN", "表記ゆれ", line_of(text, text.find(w)),
                  f"長音のゆれ「{w[:-1]}」{words[w[:-1]]}件／「{w}」{words[w]}件", "",
                  "語末の長音は付けるのが公的な原則（references/hyoki.md）")


# ---------------------------------------------------------------- AI調・翻訳調

AI_PATTERNS = [
    # (パターン, 何回以上で出すか, 重大度, メッセージ, 修正案)
    (r"することができ", 1, "WARN", "冗長な「することができる」", "〜できる"),
    (r"と言える(でしょう|だろう)", 1, "WARN", "ぼかしの「と言えるでしょう」", "言い切る／根拠を書く"),
    (r"と言っても過言ではな", 1, "WARN", "決まり文句", "削るか具体的に言う"),
    (r"ではないでしょうか", 2, "WARN", "問いかけ調の多用", "主張は言い切る"),
    (r"において", 2, "WARN", "硬い「において」の多用", "〜で／〜の"),
    (r"に関して", 3, "INFO", "「に関して」の多用", "〜について／〜の"),
    (r"(さまざまな|様々な)", 3, "WARN", "「さまざまな」の多用（中身が空になりがち）", "具体例を挙げる"),
    (r"重要(です|な|である|だ)", 3, "WARN", "「重要」の多用", "なぜ重要かを書く"),
    (r"ではなく、", 3, "WARN", "「AではなくB」構文の反復", "本当の誤解訂正だけに使う"),
    (r"いかがでしたか", 1, "WARN", "まとめ記事の定型句", "削る"),
    (r"(シームレス|包括的な|多岐にわたる|鍵となる|カギとなる|紐解|深掘り|不可欠)", 1, "INFO",
     "AI文章に頻出する語", "具体的な言葉に置き換える"),
    (r"見ていきましょう|解説していきます|ご紹介します", 1, "INFO", "前置きの定型句", "すぐ本題に入る"),
    (r"まさに", 2, "INFO", "強調語「まさに」の多用", "削る"),
    (r"することで", 3, "INFO", "「することで」の多用", "〜して／〜により"),
    (r"を通じて", 3, "INFO", "「を通じて」の多用", "〜で／〜により"),
    (r"(?:^|(?<=[。\n]))[^。\n]{1,10}は(一つ|ひとつ|二つ|ふたつ|三つ|みっつ|シンプル|簡単)(です|だ)?。", 1, "WARN",
     "溜めを作る短い前置き文（「コツは一つ。」型）", "前置きを削り、答えを直接書く"),
    (r"(する|頼む|話しかける|入力する|使う|押す|書く|聞く|選ぶ|置く)だけで", 1, "INFO",
     "手軽さを誇張する「〜だけで」", "できることを淡々と書く"),
    (r"(しましょう|みましょう|ましょう)[。！!]", 1, "INFO",
     "読み手への呼びかけ（教材・解説記事調）", "〜してください／言い切る"),
    (r"(ている|でお困りの|に悩む)[^。\n]{0,6}(職場|会社|チーム|方|人|あなた)なら", 1, "INFO",
     "読み手を呼びかけで絞る広告調（「〜している職場なら」）", "対象を地の文で述べる"),
    (r"(ないわけではない|なくはない|ないことはない)", 1, "INFO", "二重否定", "肯定で言う"),
    (r"のではないかと(思|考)", 1, "INFO", "過剰な婉曲", "〜と考えます"),
]


def check_ai(text, f):
    adds = list(re.finditer(r"(?:^|(?<=[。\n]))\s*(また|さらに|さらには|加えて|そして|それに加えて)、", text))
    if len(adds) >= 3:
        f.add("INFO", "AI調", line_of(text, adds[0].start()),
              f"文頭の足し算の接続詞が{len(adds)}回（事実を同じ重さで並べている疑い）", "",
              "時間・因果・対比など実際の関係でつなぐか、接続詞を外す（design.md の「情報の位置づけ」）")
    for pat, th, sev, msg, fix in AI_PATTERNS:
        ms = list(re.finditer(pat, text))
        if len(ms) >= th:
            if th == 1:
                for m in ms[:5]:
                    f.add(sev, "AI調", line_of(text, m.start()), msg,
                          excerpt(text, m.start(), m.end()), fix)
            else:
                f.add(sev, "AI調", line_of(text, ms[0].start()), f"{msg}（{len(ms)}回）", "", fix)


# ---------------------------------------------------------------- 読みやすさ

def check_readability(sents, f, max_len):
    tails = []
    for ln, s, structural in sents:
        n = len(s)
        commas = s.count("、") + s.count("，")
        if not structural and n > max_len:
            f.add("WARN", "長文", ln, f"一文が{n}字（目安{max_len}字）", s[:30] + "…", "文を分ける")
        if commas >= 5:
            f.add("INFO", "読点", ln, f"読点が{commas}個", s[:30] + "…", "文を分けるか語順を変える")
        elif not structural and n > 60 and commas == 0:
            f.add("INFO", "読点", ln, f"{n}字で読点なし", s[:30] + "…", "意味の切れ目に読点を")
        if re.search(r"(?:[^、。の\s]{1,8}の){4,}", s):
            f.add("INFO", "読みやすさ", ln, "「の」の連続", s[:30] + "…", "「の」を他の助詞や語順で減らす")
        if not structural:
            tails.append((ln, re.sub(r"[。！？!?」）)]+$", "", s)[-4:]))
    run = 1
    for i in range(1, len(tails)):
        if tails[i][1] == tails[i - 1][1] and len(tails[i][1]) == 4:
            run += 1
            if run == 3:
                f.add("INFO", "リズム", tails[i][0], f"同じ文末「{tails[i][1]}」が3文続く", "", "文末を変える")
        else:
            run = 1


# ---------------------------------------------------------------- ユーザールール

def check_rules(text, f, path):
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as e:
        print(f"rules file error: {e}", file=sys.stderr)
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(.+?)\s*(?:->|=>|→)\s*(.+)", line)
        if not m:
            continue
        bad, good = m.group(1).strip(), m.group(2).strip()
        for mm in re.finditer(re.escape(bad), text):
            if text.startswith(good, mm.start()):
                continue  # 正しい形の一部（サーバ → サーバー など）
            f.add("WARN", "プロジェクト規則", line_of(text, mm.start()), f"「{bad}」→「{good}」",
                  excerpt(text, mm.start(), mm.end()), good)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="日本語の軽量チェッカー")
    ap.add_argument("file")
    ap.add_argument("--register", choices=["business", "kouyou", "chat", "general"], default="business")
    ap.add_argument("--rules", help="プロジェクト表記ルール（1行に「誤 -> 正」）")
    ap.add_argument("--max-len", type=int, default=None, help="一文の最大字数（既定: 公用文60／チャット60／他80）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        raw = load_text(args.file)
    except OSError as e:
        print(f"input error: {e}", file=sys.stderr)
        sys.exit(1)
    text = mask_code(raw)
    sents = split_sentences(text)
    max_len = args.max_len or (60 if args.register in ("kouyou", "chat") else 80)

    f = Findings()
    check_keigo(text, f, args.register)
    check_style(text, sents, f, args.register)
    check_hyoki(text, f, args.register)
    check_ai(text, f)
    check_readability(sents, f, max_len)
    if args.rules:
        check_rules(text, f, args.rules)

    # 同一箇所の重複を除く
    seen, items = set(), []
    for it in sorted(f.items, key=lambda x: (SEV_ORDER[x["severity"]], x["line"])):
        key = (it["category"], it["line"], it["message"], it["excerpt"])
        if key not in seen:
            seen.add(key)
            items.append(it)
    counts = Counter(i["severity"] for i in items)

    if args.json:
        print(json.dumps({"register": args.register, "chars": len(raw), "counts": dict(counts),
                          "findings": items}, ensure_ascii=False, indent=1))
        return
    print(f"# check: register={args.register} chars={len(raw)} "
          f"ERROR={counts['ERROR']} WARN={counts['WARN']} INFO={counts['INFO']}")
    if not items:
        print("問題は見つかりませんでした。最後に通読だけしてください。")
    for it in items:
        loc = f"L{it['line']}" if it["line"] else "全体"
        line = f"[{it['severity']}] {loc} {it['category']}: {it['message']}"
        if it["excerpt"]:
            line += f" 「{it['excerpt']}」"
        if it["suggestion"]:
            line += f" → {it['suggestion']}"
        print(line)


if __name__ == "__main__":
    main()
