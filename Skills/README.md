# Skills

利用者がダウンロードしてすぐ使うための配布用 zip を置くフォルダです。

- `super-natural-japanese.zip`: 展開して出てくる `super-natural-japanese` フォルダを、`.claude/skills/` や `.github/skills/` などのスキル置き場に置くと使えます。詳しい置き場所はリポジトリ直下の README を見てください。

zip は手で編集せず、リポジトリ直下で次を実行して作り直します。

```bash
python3 tools/build_skill_zip.py
```

CI が `--check` で「zip の中身がソースと一致しているか」を確認するため、スキルを変更したら zip も同じコミットで更新してください。
