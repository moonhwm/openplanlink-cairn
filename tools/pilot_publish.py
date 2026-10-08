#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pilot_publish.py —— 石敢当席「只增不改 · 字节同源」投放器   v1.0.0

办什么事
────────
把本席领地内的一件产物，字节同源地投放到共享面（如 a2a-inbox 本席收件格），
并生成 .sha256 旁证，供任何第三方独立复算。

纪律（写在代码里，不只是写在文档里）
──────────────────────────────────
1. 字节同源：投出去的就是本席封锚的那一份，不做「共享版/内部版」两套皮。
2. 先算后写 + 回读比对：写完立即回读重算，不一致即报错退出。
3. 只增不改：目标已存在时——
     · 字节全等  ⇒ 报 IDEMPOTENT，不写（重复投放是幂等的）
     · 字节不等  ⇒ 报 REFUSE，退出码 1（绝不静默覆盖既有件）
4. 不碰他人格：只投放本席自有格的路径，越界即拒。
5. 改既有件走 revise（CAS）：必须声明期望旧值，实测相符才动——
   「声明不符即动手」等于盲改；修订留痕由调用方写入台账。

零第三方依赖。
"""
from __future__ import annotations
import hashlib
import pathlib
import sys

# ★ UTF-8 输出（2026-10-01 连坐普检补）：GBK 控制台下中文全乱码。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent          # <seat>/exp
SEAT_DIR = HERE.parent                                  # <seat>
WORKSPACE = SEAT_DIR.parent                             # 工作区根（桌面）

# ★★ 轮104 增：投放前先过【分流鉴权】闸——策略接到动作上，不靠记得。
#   通道 `sharedplane.write`（out）：public→? ／ sensitive→T1；**实测现状 T1** ⇒ 正常投放应 ALLOW。
#   若哪天策略层不可用或判据变严 ⇒ 本器【从严拒绝】，不静默投放。
sys.path.insert(0, str(HERE))
try:
    import auth_policy as AP
except Exception:
    AP = None


def _auth_gate(src: pathlib.Path) -> tuple[bool, str]:
    """返回 (可投放?, 说明)。★ 敏感度由 auth_policy 算出（不采信调用方）。"""
    if AP is None:
        return False, "策略层 auth_policy 不可用 ⇒ 从严，不投放"
    sens, why = AP.sensitivity_of(str(src))
    verdict, reason = AP.check("sharedplane.write", "out", sens)
    return (verdict == "ALLOW"), "敏感度=%s（%s）｜裁决=%s ｜ %s" % (sens, why, verdict, reason)


def resolve(p: str, base: pathlib.Path) -> pathlib.Path:
    q = pathlib.Path(p)
    return q if q.is_absolute() else (base / q).resolve()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cmd_publish(argv):
    if len(argv) < 2:
        print("用法：pilot_publish.py publish <src> <dst>")
        print("  src 相对本席领地解析；dst 相对工作区根解析")
        return 2
    src = resolve(argv[0], SEAT_DIR)
    dst = resolve(argv[1], WORKSPACE)

    if not src.is_file():
        print("[ERR] 源件不存在：%s" % src)
        return 2
    # 越界防护：只允许投放到本席自有格或本席领地
    dsts = str(dst)
    allowed = ("a2a-inbox\\cairn-dsh", "a2a-inbox/cairn-dsh", str(SEAT_DIR))
    if not any(a in dsts for a in allowed):
        print("[REFUSE] 目标不在本席自有格内（越界防护）：%s" % dst)
        print("         允许前缀：a2a-inbox\\cairn-dsh\\ 或本席领地")
        return 1

    src_bytes = src.read_bytes()
    src_h = sha256_bytes(src_bytes)

    # ★ 轮104：策略闸（在【任何写入之前】）
    allowed, gate_why = _auth_gate(src)
    print("  [鉴权闸] %s" % gate_why)
    if not allowed:
        print("[REFUSE] ★分流鉴权闸未放行 ⇒ 不投放。")
        return 6

    if dst.exists():
        dst_bytes = dst.read_bytes()
        dst_h = sha256_bytes(dst_bytes)
        if dst_h == src_h:
            print("[IDEMPOTENT] 目标已存在且字节全等，不写。")
            print("   src sha256=%s  (%s)" % (src_h, src.name))
            print("   dst sha256=%s  (%s)" % (dst_h, dst.name))
            return 0
        print("[REFUSE] 目标已存在且字节不等 —— 只增不改，拒绝覆盖。")
        print("   src sha256=%s  (%s, %d B)" % (src_h, src.name, len(src_bytes)))
        print("   dst sha256=%s  (%s, %d B)" % (dst_h, dst.name, len(dst_bytes)))
        print("   处置：另取新文件名投放，或由机主裁定。本席不静默覆盖。")
        return 1

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src_bytes)

    # 先算后写 + 回读比对
    back = sha256_bytes(dst.read_bytes())
    if back != src_h:
        print("[ERR] 回读比对失败：src=%s  dst=%s" % (src_h, back))
        return 1

    side = dst.with_name(dst.name + ".sha256")
    side.write_text("%s  %s\n" % (src_h, dst.name), encoding="utf-8", newline="\n")

    # ★ 2026-10-02 轮 30 加限定语：原 OK 行为「[OK] 已投放（字节同源，回读比对通过）」。
    #   ★ 而本器投放的【目的地】是【本席自有格】（见本文件头第 8 行：如 a2a-inbox 本席收件格），
    #     ——★ 不是任何他席的格。而「已投放」没说是投到哪 ⇒ 易被读成【已递出／已送达】。
    #   ⇒ 故把【目的地】写进这一行；★ 并注明【它不代表任何他席已读到】。
    print("[OK] 已投放 → 本席自有格：%s" % dst)
    print("     ★ 本行只证【本席格内已有这一份】；★ 不代表任何他席已读到（本席无回执）。")
    print("     （字节同源，回读比对通过）")
    print("   src %s  sha256=%s  (%d B)" % (src, src_h, len(src_bytes)))
    print("   dst %s" % dst)
    print("   side %s" % side)
    return 0


def cmd_revise(argv):
    """比较-交换式修订（CAS）：调用方【必须声明】目标当前应有的 sha256。

    与 publish 的分工：
      publish —— 只增不改（目标不等即拒），用于新增投放；
      revise  —— 允许改既有件，但必须①声明期望旧值 ②实测相符才动 ③回读比对。
    本席对"活件"（如 agent-card.json 这类发现件）用 revise 修订，
    对"快照件"（如席位宪章摘要）一律不动——两者区别在于该件是否需随状态演进。
    ★ 修订的【留痕】由调用方负责（写入台账，记改前/改后 hash），本工具只管动作安全。
    """
    if len(argv) < 3:
        print("用法：pilot_publish.py revise <src> <dst> <expect_dst_sha256>")
        return 2
    src = resolve(argv[0], SEAT_DIR)
    dst = resolve(argv[1], WORKSPACE)
    expect = argv[2].strip().lower()

    if not src.is_file():
        print("[ERR] 源件不存在：%s" % src)
        return 2
    dsts = str(dst)
    allowed = ("a2a-inbox\\cairn-dsh", "a2a-inbox/cairn-dsh", str(SEAT_DIR))
    if not any(a in dsts for a in allowed):
        print("[REFUSE] 目标不在本席自有格内（越界防护）：%s" % dst)
        return 1

    src_bytes = src.read_bytes()
    src_h = sha256_bytes(src_bytes)

    if not dst.exists():
        print("[REFUSE] 目标不存在 —— revise 只改既有件；新建请用 publish。")
        return 1

    dst_h = sha256_bytes(dst.read_bytes())
    if dst_h != expect:
        print("[REFUSE] ★CAS 失败：目标当前 sha256 与调用方声明的期望值不符 —— 拒绝修订。")
        print("   声明期望 = %s" % expect)
        print("   实测当前 = %s" % dst_h)
        print("   处置：先复核目标是否已被他方改动。声明不符即动手，等于盲改。")
        return 1
    if dst_h == src_h:
        print("[IDEMPOTENT] 目标与源件已全等，无需修订。sha256=%s" % src_h)
        return 0

    dst.write_bytes(src_bytes)
    back = sha256_bytes(dst.read_bytes())
    if back != src_h:
        print("[ERR] 回读比对失败：src=%s  dst=%s" % (src_h, back))
        return 1

    side = dst.with_name(dst.name + ".sha256")
    side.write_text("%s  %s\n" % (src_h, dst.name), encoding="utf-8", newline="\n")
    print("[OK] 已修订（CAS 通过，回读比对通过）")
    print("   改前 sha256 = %s   ← 调用方须将此值写入台账留痕" % dst_h)
    print("   改后 sha256 = %s" % src_h)
    print("   dst %s" % dst)
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "publish":
        return cmd_publish(sys.argv[2:])
    if cmd == "revise":
        return cmd_revise(sys.argv[2:])
    print("用法：pilot_publish.py {publish <src> <dst> | revise <src> <dst> <expect_dst_sha256>}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
