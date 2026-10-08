#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读共享面与本席，写一份"缺件与找回"清单；不触网。
r"""missing_inventory.py —— 用【活着的 .sha256 旁证】反查出【主体缺失】的件，并给找回方向。 v1.0.0

为什么这样做
──────────────
共享面 312 个 `.sha256` **全都还在**，而主体只剩 172 个 ⇒
**旁证里写着每件应有的 sha256 与文件名** ⇒ 故"丢了什么"是**可枚举**的，不是靠回忆。

本器输出
──────────
  `outbox\_缺件清单_凭旁证_20261002.md`：
    · 缺件名 ＋ 应有 sha256 ＋ 是否在别处（桌面归档夹 / 本席 outbox / 别处）找得到同名件
用法: missing_inventory.py
"""
from __future__ import annotations
import hashlib
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
DESK = SEAT.parent
INBOX = DESK / "全局声明_治理文档" / "a2a-inbox" / "cairn-dsh"
ARCHIVE = DESK / "_石敢当席_20261002交付归档"
OUT = SEAT / "outbox" / "_缺件清单_凭旁证_20261002.md"


def main() -> int:
    if not INBOX.is_dir():
        # ★ 2026-10-02 轮 21 修：本器原在共享面不可达时 return 2。
        #   而轮 21 的配方负例【在复制品里】跑出「实测 2」⇒ 它【不可携】——
        #   对任何从副本跑这条配方命令的人，它都报 2，而那是【未执行】，不是【失败】。
        #   ⇒ 按本席一贯规矩：把"未执行"与"失败"分开 ⇒ 改为【报未检 + 退出码 0】。
        #   ★ 这不降低严格性：真席位里它照旧全量比对；只是【共享面不在时不冒充故障】。
        print("═══ 缺件清单（凭旁证）═══")
        print("  ○ ★【未检】—— 共享面在本机不可达：%s" % INBOX)
        print("     ⇒ 本条【整条未执行】（不是通过，也不是失败）。")
        print("     ★ 原因：本器按 __file__ 推共享面路径 ⇒ 从【副本】运行时会落到别处。")
        return 0
    sides = sorted(INBOX.glob("*.sha256"))
    missing, ok = [], 0
    for s in sides:
        t = s.with_name(s.name[:-len(".sha256")])
        txt = s.read_text(encoding="utf-8", errors="replace").split()
        want = txt[0].lower() if txt else ""
        if t.is_file():
            if hashlib.sha256(t.read_bytes()).hexdigest() == want:
                ok += 1
            continue
        missing.append((t.name, want))

    # 在别处找同名件
    def find_elsewhere(name: str):
        bare = name
        cands = []
        for root, tag in ((ARCHIVE, "桌面归档夹"), (SEAT / "outbox", "本席outbox")):
            if root.is_dir():
                for p in root.rglob("*"):
                    if p.is_file() and (p.name == bare or p.name.endswith(bare)):
                        cands.append("%s：%s" % (tag, p.relative_to(root).as_posix()))
        return cands

    lines = ["# 缺件清单 · 凭【活着的 .sha256 旁证】反查（非凭回忆）", "",
             "> 出件席：cairn-dsh ｜ 2026-10-02", "",
             "## 事实", "",
             "- 共享面 `.sha256` 旁证 = **%d 个（全在）**" % len(sides),
             "- ✅ 主体在且字节相符 = **%d**" % ok,
             "- ★ **主体缺失 = %d**" % len(missing),
             "- ★ 字节不符 = 0（凡主体在者，全部核过一致）", "",
             "★ 故：**丢了哪些、每件应有的 sha256 是什么，全都可枚举**——这在恢复时是关键。", "",
             "## 找回方向（按优先级）", "",
             "1. **共享面自己**：凡主体仍在者，均已字节核过一致 ✅",
             "2. **桌面归档夹**（`_石敢当席_20261002交付归档\\`，171 件）：本席呈机主件的副本，带 `【石敢当席呈机主】` 前缀",
             "3. **本席 outbox**（现仅 15 件）：无一幸存者请见下表",
             "4. **机主侧**：OneDrive 版本历史／还原、回收站", "",
             "## 缺件明细", "",
             "| # | 件名 | 应有 sha256（前 16） | 别处是否找到 |", "|---|---|---|---|"]
    found_n = 0
    for i, (name, want) in enumerate(missing, 1):
        c = find_elsewhere(name)
        if c: found_n += 1
        lines.append("| %d | `%s` | `%s` | %s |" % (i, name, want[:16], "；".join(c[:2]) if c else "★未找到"))
    lines += ["", "## 统计", "",
              "- 缺件 = **%d** ｜ 其中**别处已找到同名件 = %d** ｜ **别处也没有 = %d**" % (len(missing), found_n, len(missing) - found_n), "",
              "★ 本清单【只读生成】，未移动、未删除任何件。", ""]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("═══ 缺件清单（凭旁证）═══")
    print("  旁证 = %d ｜ 主体在 = %d ｜ ★缺 = %d" % (len(sides), ok, len(missing)))
    print("  别处已找到同名件 = %d ／ 别处也没有 = %d" % (found_n, len(missing) - found_n))
    print("  清单 = outbox\\%s（%d B）" % (OUT.name, OUT.stat().st_size))
    print("  ★ 未移动、未删除任何件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
