# super-natural-japanese

日本語の文章を「自然・正確・一貫」で仕上げる Agent Skill。敬語・表記ゆれ・公用文に対応し、依存ゼロの高速チェッカー付き。

このリポジトリはスキル本体の開発・更新用です。リポジトリ直下がそのままスキルフォルダになっています。

## インストール

### zip をダウンロードして置く(いちばん簡単)

次の zip をダウンロードします。

- [Skills/super-natural-japanese.zip](https://github.com/github129/super-natural-japanese/raw/main/Skills/super-natural-japanese.zip)

展開して出てくる `super-natural-japanese` フォルダを、スキル置き場に置きます。

| 環境 | 置き場所 |
| --- | --- |
| GitHub Copilot(リポジトリ単位) | `.github/skills/super-natural-japanese/` |
| GitHub Copilot(個人単位・全プロジェクト共通) | `~/.copilot/skills/super-natural-japanese/` |
| Claude Code(リポジトリ単位) | `.claude/skills/super-natural-japanese/` |
| Claude Code(個人単位) | `~/.claude/skills/super-natural-japanese/` |

zip は `main` の内容と常に同期しています(CI で検証)。更新するときは zip をダウンロードし直して置き換えてください。

### git clone で置く(更新を `git pull` で済ませたいとき)

```bash
# 例: Claude Code(リポジトリ単位)
git clone https://github.com/github129/super-natural-japanese .claude/skills/super-natural-japanese
```

Copilot CLI では `/skills reload` で再読み込み。`/super-natural-japanese` で明示的に呼び出せます。

## 使い方の例

- 「この議事録を自然な日本語に直して」
- 「このメール、敬語に問題ないかチェックだけして」
- 「docs/ 以下の表記ゆれを統一して」
- 「この通知文を公用文のルールで書き直して」

## チェッカー単体

```bash
python3 scripts/check.py --register business doc.md
python3 scripts/check.py --register kouyou --rules .jp-style.txt notice.md
echo "本文" | python3 scripts/check.py --register chat -
```

Python 3.8 以上で、標準ライブラリのみで動きます。

## ファイル構成

```
.
├── SKILL.md                 # スキル本体(手順とルール)
├── references/              # 必要なときだけ読む参照資料
│   ├── design.md            #   設計(読み手・主メッセージ・型の見分け方)
│   ├── keigo.md             #   敬語の誤用パターン
│   ├── hyoki.md             #   漢字・かな・数字・記号の表記
│   ├── kouyoubun.md         #   公用文のルール
│   ├── ai-patterns.md       #   AI調・翻訳調の言い回し
│   └── checklist.md         #   Python が使えないときの目視チェック
├── scripts/check.py         # 軽量チェッカー(標準ライブラリのみ)
├── evals/evals.json         # スキル改善時に確認する評価ケース
├── Skills/                  # 配布用 zip(上記のスキルファイルを固めたもの)
├── tools/build_skill_zip.py # 配布用 zip を作る・検証するスクリプト
├── tests/test_check.py      # check.py の回帰テスト
├── CHANGELOG.md             # 変更履歴
└── CLAUDE.md                # Claude Code 向けの開発ルール
```

## 開発

### テスト

```bash
python3 -m unittest discover -s tests -v
```

`scripts/check.py` を変更したら、必ず対応するテストを `tests/test_check.py` に追加してください。
push と Pull Request のたびに、GitHub Actions が Python 3.8 と最新版でテストを実行します。

### スキルを改善するとき

1. `SKILL.md` や `references/` を変更する
2. `evals/evals.json` の全ケースで文章を作り直し、`past_feedback` に挙がった指摘が再発しないか確かめる
3. 新しく見つかった指摘は `past_feedback` に追記する
4. `CHANGELOG.md` の `[Unreleased]` に変更を書く
5. 配布用 zip を作り直してコミットする

```bash
python3 tools/build_skill_zip.py          # Skills/super-natural-japanese.zip を作り直す
python3 tools/build_skill_zip.py --check  # zip がソースと一致しているか確認(CI と同じ)
```

zip が古いままだと CI が失敗します。

### ブランチ運用

`main` は常に使える状態に保ちます。直接 push せず、作業ブランチから Pull Request を作成してください。

```bash
git switch main && git pull origin main
git switch -c feature/<内容が分かる名前>
# 変更・コミット
git push -u origin feature/<内容が分かる名前>
```

| プレフィックス | 用途 |
| --- | --- |
| `feature/` | ルール・参照資料・チェッカーの追加 |
| `fix/` | 誤検出や誤りの修正 |
| `docs/` | README など説明のみの変更 |
| `chore/` | CI・設定の変更 |

## ライセンス

MIT です。設計の一部は coji/natural-japanese(MIT)に着想を得ています。
