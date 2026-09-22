"""scripts/check.py の回帰テスト。

標準ライブラリの unittest だけで動く。実行方法:
    python3 -m unittest discover -s tests -v
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK_PY = os.path.join(ROOT, "scripts", "check.py")

_spec = importlib.util.spec_from_file_location("check", CHECK_PY)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def run(text, register="business", rules=None):
    """テキストを全チェックにかけ、finding のリストを返す。"""
    masked = check.mask_code(text)
    sents = check.split_sentences(masked)
    max_len = 60 if register in ("kouyou", "chat") else 80
    f = check.Findings()
    check.check_keigo(masked, f, register)
    check.check_style(masked, sents, f, register)
    check.check_hyoki(masked, f, register)
    check.check_ai(masked, f)
    check.check_readability(sents, f, max_len)
    if rules:
        check.check_rules(masked, f, rules)
    return f.items


def messages(items, severity=None, category=None):
    return [
        i["message"] for i in items
        if (severity is None or i["severity"] == severity)
        and (category is None or i["category"] == category)
    ]


class KeigoTest(unittest.TestCase):
    def test_double_keigo(self):
        items = run("部長がおっしゃられました。")
        self.assertIn("二重敬語", messages(items, "ERROR", "敬語"))

    def test_humble_for_others_action(self):
        items = run("資料をご確認してください。")
        self.assertTrue(any(m.startswith("相手の動作に謙譲語") for m in messages(items, "ERROR", "敬語")))

    def test_correct_keigo_is_clean(self):
        items = run("資料をご確認ください。部長がおっしゃいました。")
        self.assertEqual(messages(items, "ERROR"), [])

    def test_sasete_itadaku_count(self):
        text = "送付させていただきます。確認させていただきます。報告させていただきます。"
        items = run(text)
        self.assertTrue(any("させていただく" in m for m in messages(items, "WARN", "敬語")))

    def test_ryokai_only_in_formal_registers(self):
        self.assertTrue(messages(run("了解しました。", "business"), "INFO", "敬語"))
        self.assertFalse(messages(run("了解しました。", "chat"), "INFO", "敬語"))


class GrammarTest(unittest.TestCase):
    def test_ra_nuki(self):
        items = run("明日は見れると思います。")
        self.assertIn("ら抜き言葉", messages(items, "ERROR", "文法"))
        self.assertEqual(items[0]["suggestion"], "見られる")

    def test_ra_nuki_does_not_fire_on_nouns(self):
        # 「意見れ…」のような名詞の一部や、「見れば」は対象外
        items = run("意見を述べれば十分です。見れば分かります。")
        self.assertNotIn("ら抜き言葉", messages(items, "ERROR", "文法"))

    def test_sa_ire(self):
        items = run("明日は休まさせていただきます。")
        self.assertIn("さ入れ言葉", messages(items, "ERROR", "文法"))


class StyleTest(unittest.TestCase):
    def test_mixed_style(self):
        text = "これは資料です。明日送ります。会議は10時からです。準備は必要である。参加者は5名です。"
        items = run(text, "general")
        self.assertTrue(any(m.startswith("文体の混在") for m in messages(items, "ERROR", "文体")))

    def test_mixed_style_is_warn_in_chat(self):
        text = "これは資料です。明日送ります。会議は10時からです。準備は必要である。参加者は5名です。"
        items = run(text, "chat")
        self.assertTrue(any(m.startswith("文体の混在") for m in messages(items, "WARN", "文体")))
        self.assertFalse(messages(items, "ERROR", "文体"))

    def test_mixed_punctuation(self):
        items = run("今日は晴れです，明日は雨です。")
        self.assertTrue(any("句読点の混在" in m for m in messages(items, "ERROR", "句読点")))

    def test_hankaku_katakana(self):
        items = run("ｻｰﾊﾞｰを再起動します。")
        self.assertIn("半角カタカナ", messages(items, "ERROR", "表記"))

    def test_kanji_numerals_in_business(self):
        self.assertTrue(messages(run("三件の報告があります。", "business"), "INFO", "表記"))
        self.assertFalse(messages(run("三件の報告があります。", "general"), "INFO", "表記"))


class HyokiTest(unittest.TestCase):
    def test_kanji_kana_yure(self):
        items = run("出来ることはすべてやります。できる範囲で対応します。")
        self.assertTrue(any(m.startswith("「できる」の表記ゆれ") for m in messages(items, "WARN", "表記ゆれ")))

    def test_long_vowel_yure(self):
        items = run("サーバを止めます。サーバーを再起動します。")
        self.assertTrue(any(m.startswith("長音のゆれ") for m in messages(items, "WARN", "表記ゆれ")))

    def test_kouyou_prefers_kanji_for_subete(self):
        items = run("すべての職員に通知する。", "kouyou")
        self.assertTrue(any("公用文では「すべて」を漢字で書く" in m for m in messages(items, "WARN", "表記")))
        self.assertFalse(messages(run("すべての職員に通知する。", "business"), "WARN", "表記"))


class AiPatternTest(unittest.TestCase):
    def test_suru_koto_ga_dekiru(self):
        items = run("設定を変更することができます。")
        self.assertTrue(any("することができる" in m for m in messages(items, "WARN", "AI調")))

    def test_short_lead_in_sentence(self):
        items = run("コツは一つ。落ち着いて書くことです。")
        self.assertTrue(any("溜めを作る短い前置き文" in m for m in messages(items, "WARN", "AI調")))

    def test_additive_conjunctions(self):
        text = "機能があります。また、速いです。さらに、安いです。加えて、軽いです。"
        items = run(text)
        self.assertTrue(any("足し算の接続詞" in m for m in messages(items, "INFO", "AI調")))


class ReadabilityTest(unittest.TestCase):
    def test_long_sentence(self):
        text = "この文章は" + "とても" * 40 + "長いです。"
        items = run(text)
        self.assertTrue(any(m.startswith("一文が") for m in messages(items, "WARN", "長文")))

    def test_max_len_depends_on_register(self):
        text = "この文章は" + "とても" * 22 + "長いです。"  # 70字前後
        self.assertFalse(messages(run(text, "business"), "WARN", "長文"))
        self.assertTrue(messages(run(text, "chat"), "WARN", "長文"))

    def test_same_tail_three_times(self):
        text = "今日は会議があります。明日は面談があります。来週は出張があります。"
        items = run(text)
        self.assertTrue(any(m.startswith("同じ文末") for m in messages(items, "INFO", "リズム")))


class MaskingTest(unittest.TestCase):
    def test_code_blocks_are_ignored(self):
        text = "次を実行します。\n```\n見れる ご確認してください\n```\n以上です。"
        items = run(text)
        self.assertEqual(messages(items, "ERROR"), [])

    def test_mask_keeps_line_numbers(self):
        text = "```\nabc\ndef\n```\n見れる。"
        items = run(text)
        self.assertEqual([i["line"] for i in items if i["message"] == "ら抜き言葉"], [5])


class RulesTest(unittest.TestCase):
    def test_project_rules(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write("# コメント\nユーザ -> ユーザー\nGithub => GitHub\n")
            path = fh.name
        try:
            items = run("ユーザがGithubを使います。ユーザーも使います。", rules=path)
        finally:
            os.unlink(path)
        rules = messages(items, "WARN", "プロジェクト規則")
        self.assertIn("「ユーザ」→「ユーザー」", rules)
        self.assertIn("「Github」→「GitHub」", rules)
        # 正しい形「ユーザー」の一部は誤検出しない
        self.assertEqual(rules.count("「ユーザ」→「ユーザー」"), 1)


class CliTest(unittest.TestCase):
    def _cli(self, *args, stdin=None):
        return subprocess.run(
            [sys.executable, CHECK_PY, *args],
            input=stdin, capture_output=True, text=True, encoding="utf-8",
        )

    def test_clean_text_via_stdin(self):
        p = self._cli("--register", "business", "-", stdin="明日の会議は10時からです。\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("ERROR=0 WARN=0 INFO=0", p.stdout)
        self.assertIn("問題は見つかりませんでした", p.stdout)

    def test_json_output(self):
        p = self._cli("--json", "-", stdin="見れると思います。\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertEqual(data["register"], "business")
        self.assertEqual(data["counts"], {"ERROR": 1})
        self.assertEqual(data["findings"][0]["message"], "ら抜き言葉")

    def test_missing_file_exits_nonzero(self):
        p = self._cli(os.path.join(ROOT, "no-such-file.md"))
        self.assertEqual(p.returncode, 1)
        self.assertIn("input error", p.stderr)


class SkillLayoutTest(unittest.TestCase):
    """SKILL.md と参照ファイルの整合性。"""

    def _frontmatter(self):
        with open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertTrue(text.startswith("---\n"), "SKILL.md はフロントマターで始まる必要がある")
        body = text.split("---\n", 2)
        self.assertEqual(len(body), 3, "フロントマターが閉じていない")
        meta = {}
        for line in body[1].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        return meta, body[2]

    def test_frontmatter(self):
        meta, _ = self._frontmatter()
        self.assertEqual(meta.get("name"), "super-natural-japanese")
        self.assertTrue(meta.get("description"), "description は必須")
        self.assertLessEqual(len(meta["description"]), 1024, "description は 1024 文字以内")

    def test_referenced_files_exist(self):
        _, body = self._frontmatter()
        import re
        refs = set(re.findall(r"`((?:references|scripts)/[\w.-]+)`", body))
        self.assertTrue(refs, "SKILL.md が参照ファイルを一つも挙げていない")
        for rel in sorted(refs):
            self.assertTrue(os.path.exists(os.path.join(ROOT, rel)), "%s が存在しない" % rel)

    def test_evals_json(self):
        with open(os.path.join(ROOT, "evals", "evals.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["skill_name"], "super-natural-japanese")
        ids = [e["id"] for e in data["evals"]]
        self.assertEqual(len(ids), len(set(ids)), "evals の id が重複している")
        for e in data["evals"]:
            self.assertTrue(e.get("prompt"))
            self.assertTrue(e.get("expected_output"))


if __name__ == "__main__":
    unittest.main()
