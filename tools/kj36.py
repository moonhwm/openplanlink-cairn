# -*- coding: utf-8 -*-
"""kj36.py —— 更新 directing_approx_run.py 之 STATE 为本夜（10-12/13）之实（2026-10-13）
缘由：令条第二模式「实时导演」之近似承载（qwen-max 单次前向）★今夜未运行（产物止于 10-09）；
      而其 STATE（态势输入）为 10-09 之旧态 ⇒ ★须先更新，否则「导演」之输入过时。
本补丁（★最小改动；★改动前备份）：
  ① 备份至 exp/_patch_backup_<日期>/directing_approx_run.py
  ② 将 STATE = ( ... ) 整段替换为本夜之实（三五句）
  ③ 编译 + 印认
（中文串一律用「」）
"""
import pathlib, re, shutil, sys, time, py_compile

SEAT = pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
P = SEAT/"exp"/"directing_approx_run.py"

NEW = '''STATE = ("【真实态势，作为世界的当前状态】时段：北京时间 2026-10-13 约 01:40（夜间运维窗 23:00–08:00 内）。"
         "在场：Cairn 席（本席）。★世界面：平台已有 50 个 ready 世界；★本夜本席亲手建三世界并皆 ready —— "
         "「霓虹虚空」（v7 初版）、「夜游回望」（v8 动态完善第二轮）、「夜色游乐场」（v9 动作池之试），"
         "且三对「我传之首帧 ↔ 平台回渲之首帧」★一致。★模型面：CAIRN v6b 有 ★18 节点骨架＋★7 组语义动画"
         "（WALK 14 通道；本席另加 LOOK_AROUND）。★动作池：characterActions 恒四项（dash／jump／crouch／attack）；"
         "environmentActions ★可经建世界之 prompt 点名扩充（v9 得 ['open_close_door']）。★演绎面：★服务端记录指令"
         "而 status 恒 UNEXECUTED（五假设否证＋我自建世界复验亦同）⇒ ★执行环节在客户端或平台侧。"
         "★文档面：三件 watch（outline 無變；polish／polish_otl 云端微变而实质 0）。"
         "★风险面：本机内存 107.5 MB（深警戒）；本机 Edge 不可用（连 --version 都挂）。")'''

t = P.read_text(encoding="utf-8")
n = 0
if "夜色游乐场" not in t:
    m = re.search(r'STATE = \(.*?\)\n', t, re.S)
    if m:
        t = t[:m.start()] + NEW + "\n" + t[m.end():]
        n += 1
        bak = SEAT/"exp"/("_patch_backup_%s" % time.strftime("%Y%m%d"))
        bak.mkdir(parents=True, exist_ok=True)
        shutil.copy2(P, bak/P.name)
        P.write_text(t, encoding="utf-8", newline="\n")
        print("  ✓ 已替换 STATE（1 处）；备份至 %s" % bak.name)
    else:
        print("  ★未匹配 STATE 段 ⇒ 未改（如实报）")
else:
    print("  · 已在（无需再改）")

try:
    py_compile.compile(str(P), doraise=True)
    print("   ★编译 ✓")
except Exception as ex:
    print("   ★编译 ✗：")
    for l in str(ex).splitlines()[:5]:
        print("      " + l[:100])
lines = P.read_text(encoding="utf-8").splitlines()
for i, l in enumerate(lines, 1):
    if l.startswith("STATE = ("):
        print("   ★L%-4d ｜ %s" % (i, l.strip()[:90]))
        print("   ★L%-4d ｜ %s" % (i+1, lines[i].strip()[:90] if i < len(lines) else ""))
print("   ★含「夜色游乐场」之行：%d 处"
      % sum(1 for l in lines if "夜色游乐场" in l))
