# -*- coding: utf-8 -*-
"""patch_arch.py —— 一次性修补 arch_diagram.py：弃用 str.format（与 JS 花括号冲突），改 @@TOKEN@@ 替换。"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
p = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp\arch_diagram.py")
t = p.read_text(encoding="utf-8")

before = t

# 1) 花括号回落单（模板里为 format 转义的 {{ }} → { }）
t = t.replace("{{", "{").replace("}}", "}")

# 2) 占位符改为 token（避免与 JS 模板字面量 ${ } 冲突）
t = t.replace("生成 {ts} ｜ 采样时点 {sample}", "生成 @@TS@@ ｜ 采样时点 @@SAMPLE@@")
t = t.replace("const DATA = {data};", "const DATA = @@DATA@@;")
t = t.replace("const SC = {sc}, ST = {st};", "const SC = @@SC@@, ST = @@ST@@;")

# 3) 调用点：format → 顺序替换
old_call = """    html = HTML.format(ts=ts, sample=SAMPLE_AT,
                       data=json.dumps(data, ensure_ascii=False),
                       sc=json.dumps(STATE_COLOR, ensure_ascii=False),
                       st=json.dumps(STATE_TEXT, ensure_ascii=False))"""
new_call = """    html = (HTML
            .replace("@@TS@@", ts)
            .replace("@@SAMPLE@@", SAMPLE_AT)
            .replace("@@DATA@@", json.dumps(data, ensure_ascii=False))
            .replace("@@SC@@", json.dumps(STATE_COLOR, ensure_ascii=False))
            .replace("@@ST@@", json.dumps(STATE_TEXT, ensure_ascii=False)))
    if "@@" in html:
        raise SystemExit("未替换的占位符残留：%s" % [s for s in ("@@TS@@", "@@SAMPLE@@", "@@DATA@@", "@@SC@@", "@@ST@@") if s in html])"""
if old_call not in t:
    print("★ 未找到调用点，未修改")
    raise SystemExit(2)
t = t.replace(old_call, new_call)

p.write_text(t, encoding="utf-8")
print("★ 已修补：%s（%d → %d 字符）" % (p.name, len(before), len(t)))
print("★ 残留 '{{'：%d ｜ 残留 '}}'：%d ｜ 残留 '@@'（调用点外不应有）：%d" % (
    t.count("{{"), t.count("}}"), t.count("@@")))
