#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
tool_hygiene.py —— 本席工具与出件的【机检】体检器。   v1.1.0

为什么要它
──────────
同一个错，本席犯到【第四次】才明白"记住"没用：
  · 第 1 次：scan_secrets.py——中文正文里用 ASCII 直引号 → 语法失败；
  · 第 2 次：led_24 的 JSON detail——同一个动作 → JSON 非法、台账拒收；
  · 第 3 次：led_41 的 JSON detail——又是同一个动作；
  · 第 4 次：本文件的初版——为"检查别人有没有把三引号字面量写进文档串"，
    本席在**自己的文档串里写了那个字面量**，当场把文档串提前闭合。
    （教训：**描述陷阱的文字，自己最容易掉进陷阱**。）
每次都是工具 fail-closed 兜住的；**靠工具兜底不是纪律，是运气**。
⇒ 本器把"靠记住"换成"靠跑一遍"。

★ v1.1.0 删掉了一个检查项 —— 记下为什么
──────────────────────────────────────────
初版第①项用正则查"ASCII 直引号紧邻中文"，**报出 466 项，全是假阳性**：
`print("用法：…")` 这种**正确代码**恰好满足"引号后紧跟中文"，于是每条正常字符串都被报。
而真正的错误形态（**字符串内部夹了引号致其提前闭合**）**正则根本判不了，只有解析器能判**。
⇒ 结论：**这项检查应当删除**，理由有两条——
  ① **它抓不到真问题**（真问题由 `py_compile` / `json.loads` 捕获，二者才是权威）；
  ② **它会训练使用者忽略警报**（假阳性率高的检查项是有害的，与"误报会淹没真信号"同一条理）。
**删掉一个假检查项，比留下它更安全。**

查什么（三项·皆为权威判定，非启发式）
──────────────────────────────────────
1. 每个 .py 是否有 **UTF-8 stdout 块**（否则 GBK 控制台下中文乱码，本席犯过一次）。
2. 每个 .py 是否通过 **-W error::SyntaxWarning 严格编译**
   （★"文档串被三引号提前闭合"这类错**由本项捕获**，故不另设检查）。
3. 每个 .json（本席规格件）是否 **可被 json 解析**（前两次事故的兜底闸）。

零依赖。
"""
from __future__ import annotations
import json
import pathlib
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ★ 2026-10-03 轮 61 修：原为【硬编码绝对路径】：
#     SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面\A2A新席_石敢当Cairn_20260928")
#   ⇒ ★ 两个后果：① 它【不可携】——搬到别处或从副本跑，扫的还是那一条绝对路径；
#      ② ★ 我【没法给它造负例对照】——负例要在临时副本里造坏件再让它去扫。
#   ★★ 而"不可携"这个缺陷我在【轮 21】就修过一件（missing_inventory.py）——
#      即：那次修【只落在了一件器上】，本器一直是老样子。
#   ⇒ 故改为【由 __file__ 推】，与其余器一致。
SEAT = pathlib.Path(__file__).resolve().parent.parent


def main():
    print("═══ 本席工具与出件·机检体检 ═══")
    pys = sorted(list((SEAT / "exp").glob("*.py")) + list((SEAT / "ledger").glob("*.py")))
    jsons = sorted((SEAT / "exp").glob("*.json"))
    no_utf8, bad_compile, bad_json = [], [], []

    for p in pys:
        t = p.read_text(encoding="utf-8", errors="replace")
        if "reconfigure" not in t:
            no_utf8.append(p.name)
        try:
            r = subprocess.run([sys.executable, "-W", "error::SyntaxWarning", "-m", "py_compile", str(p)],
                               capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                bad_compile.append((p.name, (r.stderr or "").strip().replace("\n", " ")[:150]))
        except Exception as e:
            bad_compile.append((p.name, "compile 失败：%s" % e))

    for p in jsons:
        try:
            json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            bad_json.append((p.name, str(e)[:120]))

    print("\n① 缺 UTF-8 输出块：%d 个" % len(no_utf8))
    for n in no_utf8:
        print("   ★ %s" % n)
    print("\n② 严格编译未过：%d 个" % len(bad_compile))
    for n, e in bad_compile:
        print("   ★ %s :: %s" % (n, e))
    print("\n③ JSON 不可解析：%d 个" % len(bad_json))
    for n, e in bad_json:
        print("   ★ %s :: %s" % (n, e))

    total = len(no_utf8) + len(bad_compile) + len(bad_json)
    # ★ 2026-10-02 轮 27 改判词：原判词是「PASS —— 三项全洁」。
    #   而轮 27 实测：我在每轮收尾都引这句，读者（含我）会读成【整体健康】。
    #   ★ 而这三项【全是形式性的】：只有编码块／能编译／JSON 能解析。
    #   ⇒ 故把它【收窄成它真正说的】，并把【它不含的】当场点出来、指向对应器。
    # ★ 2026-10-03 轮 61 修：**失败时也要印一句【可被读到的判词】。**
    #   缘由（轮 61 的负例对照当场抓到）：本器失败时【退出码 1 正确】，但判词那行印的是
    #   「结论：FAIL」——★ 而任何按「结论：PASS/BAD」过滤的读法【都读不到 FAIL】⇒
    #   于是负例对照报「判词 ?」。★ 这与轮 26 查出的 verify_seat_location／pilot_publish 是【同一类】：
    #   **失败时的输出若不可读，就等于把失败藏起来了。**
    #   ⇒ 故改为：**成功与失败【各印一句明确的判词】**，且失败时【把待修项点名】。
    if total == 0:
        verdict = "PASS —— ★形式三项全洁（有 UTF-8 stdout 块／可编译／JSON 可解析）"
    else:
        verdict = "BAD —— ★形式三项【不洁】：有 %d 项待修（见上方逐条）" % total
    print("\n═══ 结论：%s ═══" % verdict)
    if total:
        print("  ★★ 逐条待修（上面的明细里已点名）：")
        for name, ok, why in [("① 有 UTF-8 stdout 块", not no_utf8, "缺 stdout 块"),
                              ("② 可编译", not bad_compile, "编译不过"),
                              ("③ JSON 可解析", not bad_json, "解析不过")]:
            print("     %s %s" % ("✅" if ok else "★★ 不符 ⇒", name if ok else "%s：%s" % (name, why)))
    print("扫过：.py %d 个 ｜ .json %d 个" % (len(pys), len(jsons)))
    print()
    print("★★ 本器【只证形式】：它不说下列任何一件事 ——")
    print("     ① 这些器【能不能跑】（编译 ≠ 可运行；轮 20 查出过一条配方命令跑不通）")
    print("     ② 它们下的【结论对不对】")
    print("     ③ 它们【有没有被引用】（轮 20 实测：106 器中 24 个是孤儿）")
    print("     ④ 我的【过滤词会不会吞掉失败】（轮 26 实测：4 个惯用词里 2 个瞎）")
    print("   ★ 那四件事各有专器，请分别跑：")
    print("       python exp\\verify_recipe.py      # ①能不能跑（逐条实跑比对退出码）")
    print("       python exp\\audit_orphans.py      # ③谁被引用")
    print("       python exp\\audit_filters.py      # ④过滤词盲区")
    print("       （②『结论对不对』★ 无器可代 —— 须人读，见轮 11／14／17）")
    print("★本器不含启发式检查项：能被解析器判定的，不该用正则再判一遍（见文件头 v1.1.0 说明）。")
    # ★ 2026-10-03 轮 72 加：**机器可读判词行**。
    #   缘由（轮 72 实证）：收尾块靠【正则抓散文】报各器判词 ⇒ 副本里把「结论：」改成「判词：」后，
    #   ★ 收尾块【照样印"退出码 0"】而【判词内容静默消失】——★ 看上去一切正常。
    #   ⇒ 故各器此后印这一行；★ 读它比读散文可靠。
    print("★ VERDICT=%s" % ("PASS" if total == 0 else "BAD"))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
