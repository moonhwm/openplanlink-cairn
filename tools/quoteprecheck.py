# -*- coding: utf-8 -*-
"""quoteprecheck.py —— 引号错之机械预检（承《运行口径》第二十章第 2 条）（2026-10-14 立）

缘起：同类引号错**已四犯**（kj47.py／kj49.py／-1559／-1561），皆「已入口径而仍复犯」
      ⇒ 判「凡已入口径而仍复犯者，即为**再器物化**之信号」⇒ 故器物化。

★所检三类：
    ★1 **中文串内嵌半角双引号**：一行中 `"` 之数为偶数，且两引号之间含 CJK 而整行**不成对成串**
       ⇒ 典型致 `SyntaxError`（如 `"本行含"内嵌"⇒ …"`）；
    ★2 **`b"…"` 含非 ASCII**：bytes 字面量只可含 ASCII ⇒ 含 CJK 必致
       `SyntaxError: bytes can only contain ASCII literal characters`；
    ★3 **`ast.parse` 之语法错**（★最终把关，等价于编译）。

★对接：★本器可独立跑，亦可由 `pyrun.py` 前置调用（★二重把关）。
★用法：
    python quoteprecheck.py <脚本路径> …
★退出码：★0 ＝ 通过；★2 ＝ 有疑；★3 ＝ 语法错。
"""
import ast, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
BS = re.compile(r'b"([^"\n]*)"')          # 简化：不含转义之 bytes 字面量


def scan_bytes_literals(text: str):
    """★2：b"…" 含非 ASCII"""
    bad = []
    for i, ln in enumerate(text.splitlines(), 1):
        for m in BS.finditer(ln):
            try:
                m.group(1).encode("ascii")
            except UnicodeEncodeError:
                bad.append((i, ln.strip()[:110]))
    return bad


def scan_embedded_quotes(text: str):
    """★1：中文串内嵌半角双引号
    判据（★收紧以免误报）：出现 **两侧皆 CJK 之引号交界**（`CJK"CJK`）⇒ 真内嵌之签名；
    另**排除**：注释行、含反引号之说明行、三引号文档串内之行。
    """
    bad = []
    in_doc = False
    for i, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        # ★三引号文档串之粗判（成对计数）
        if s.count('"""') % 2 == 1:
            in_doc = not in_doc
            continue
        if in_doc or s.startswith("#") or "`" in ln:
            continue
        if re.search(r'[\u4e00-\u9fff]"[\u4e00-\u9fff]', ln):
            bad.append((i, s[:110]))
    return bad


def scan_bom(text: str):
    """★4：BOM（U+FEFF）—— PowerShell 5 之 Set-Content -Encoding UTF8 会写入"""
    return [(1, "文件以 BOM（U+FEFF）开头")] if text.startswith("\ufeff") else []


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python quoteprecheck.py <脚本路径> …"); return 1
    total = 0
    worst = 0
    for a in sys.argv[1:]:
        p = pathlib.Path(a)
        if not p.exists():
            print("   ★不在：%s" % a); worst = max(worst, 2); total += 1; continue
        t = p.read_text(encoding="utf-8", errors="replace")
        b1 = scan_embedded_quotes(t)
        b2 = scan_bytes_literals(t)
        try:
            ast.parse(t); syn = None
        except SyntaxError as e:
            syn = (e.lineno or 0, (e.msg or "")[:90])
        b4 = scan_bom(t)
        tag = "✓ 通过" if not (b1 or b2 or b4 or syn) else "★★有疑"
        print("   %s %s（%d 行）" % (tag, p.name, len(t.splitlines())))
        if b1:
            print("      ★类1 疑内嵌半角双引号 %d 处：" % len(b1))
            for i, s in b1[:4]:
                print("        L%-4d %s" % (i, s))
            worst = max(worst, 2)
        if b2:
            print("      ★类2 b\"…\" 含非 ASCII %d 处：" % len(b2))
            for i, s in b2[:4]:
                print("        L%-4d %s" % (i, s))
            worst = max(worst, 2)
        if b4:
            print("      ★类4 BOM：%s" % b4[0][1])
            worst = max(worst, 2)
        if syn:
            print("      ★类3 语法错：L%s %s" % (syn[0], syn[1]))
            worst = max(worst, 3)
        total += 1
    print("   ══ 检查 %d 件 ｜ 结论：%s ══" % (
        total, {0: "✓ 皆通过", 2: "★★ 有疑（须修）", 3: "★★ 语法错（须修）"}[worst]))
    return worst


if __name__ == "__main__":
    sys.exit(main())
