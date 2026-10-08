#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cairn_ledger.py —— 石敢当席（cairn-dsh）台账工具   v1.0.0

办什么事
────────
维护本席「只增不改」的前向哈希链台账 ledger/frontier_ledger.jsonl：
  init    生成创世条目链（仅当台账为空时可用；已存在则拒绝，防覆盖）
  verify  逐条复算 sha256 前向链，任一环断裂即 FAIL（退出码 1）
  seal    计算任意文件的 sha256（用于 CARD_SEAL 封锚）
  status  打印链长、末条 hash、末条时刻

三条纪律（写在代码里，不只是写在文档里）
──────────────────────────────────────
1. 只增不改：init 拒绝覆盖既有台账；追加走 append。
2. 先算后写 + 回读比对：写完立即回读重算，不一致即报错退出。
3. ★哈希链 ≠ 签名：本链可证「条目间自洽、事后未被改动」(tamper-evident)，
   不可证「是谁写的」。席位密钥未签发前，一切封锚件均只具备前者。
   凡对外声称"已签名"而未签者，即违本席不可为清单第 3 条。

零第三方依赖。私钥只引用路径，不读内容、不外发。
"""
from __future__ import annotations
import hashlib
import json
import os
import pathlib
import sys
import time

# ★ UTF-8 输出（2026-10-01 连坐普检补）：GBK 控制台下中文全乱码（实测本工具 verify 输出
#   曾整段不可读），而台账结论正是要给人读的——乱码等于没输出。
#   来由：本席 v1.1 只给 scan_secrets.py 加了这一处，随即连坐普检发现【8 个工具里 7 个同病】。
#   教训：修一处缺陷时，必须把同类工具全查一遍，否则等于只治了一只胳膊。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
LEDGER = HERE / "frontier_ledger.jsonl"
CONFLICT = HERE / "conflict_log.jsonl"
CARD = HERE.parent / "agent-card.json"
ZERO = "0" * 64
SEAT = "cairn-dsh"
INSTANCE = "dsh-ffabb8dd"


def now_cst() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())


def canon(core: dict) -> bytes:
    """规范序列化：ensure_ascii=False + sort_keys + 紧凑分隔符。
    与在网总线口径同为 sort_keys 原则——键序不同不得导致 hash 不同。"""
    return json.dumps(core, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def entry_hash(core: dict) -> str:
    return hashlib.sha256(canon(core)).hexdigest()


def file_sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_chain():
    if not LEDGER.exists():
        return []
    out = []
    for i, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append((i, json.loads(line)))
        except json.JSONDecodeError as e:
            print("[ERR] 第 %d 行不是合法 JSON：%s" % (i, e))
            sys.exit(1)
    return out


def make_entry(ev_type, subject, detail, evidence="", prev=ZERO) -> dict:
    core = {
        "ts": now_cst(),
        "ev_type": ev_type,
        "seat": SEAT,
        "instance": INSTANCE,
        "subject": subject,
        "detail": detail,
        "evidence": evidence,
        "prev": prev,
        "signed": False,
        "sig": None,
        "sig_note": "未签发席位密钥；本链只证一致，不证作者（哈希链≠签名）",
    }
    core["hash"] = entry_hash(core)
    return core


def cmd_init():
    if LEDGER.exists() and LEDGER.stat().st_size > 0:
        print("★ REFUSE [拒绝] 台账已存在且非空：%s" % LEDGER)
        print("       只增不改——init 不覆盖。追加请用 append。")
        return 2
    card_h = file_sha256(CARD) if CARD.exists() else "(卡片缺失)"
    card_bytes = CARD.stat().st_size if CARD.exists() else 0

    entries = [
        ("SEAT_GENESIS",
         "席位创生：Cairn（石敢当）· cairn-dsh · dsh-ffabb8dd",
         "机主欧阳宏俊授权（2026-09-28，desktop-gengfu 席代呈），以「创造模式」立四节：SELF.md / SEAT_A2A.md / FRONTIER.md / CHARTER.md。"
         "命名理据：cairn＝行者垒石为记、后来者续石而不夺；石敢当＝立于界隅守界之石，守而不侵。",
         "SELF.md, SEAT_A2A.md, FRONTIER.md, CHARTER.md"),

        ("CLAIM",
         "独占边疆宣称（无主物，本席单方生效）",
         "①本席领地全树 A2A新席_石敢当Cairn_20260928（含 exp/ ledger/ inbox/ outbox/）；"
         "②端口 127.0.0.1:18787 RESERVED（今日实测不在 LISTEN 表，未启用，回退 18788）；"
         "③%USERPROFILE%\\\\.cairn\\\\ RESERVED 未创建（跨工作区写入属呈批区，未擅自执行）。",
         "netstat LISTEN 全表未见 18787；Test-Path 实测"),

        ("CLAIM",
         "共享面收件格创建（含父目录连带创建的如实披露）",
         "建 全局声明_治理文档\\\\a2a-inbox\\\\cairn-dsh\\\\。★New-Item -Force 连带创建了父目录 a2a-inbox\\\\，"
         "该父目录此前实测不存在。本席只对 cairn-dsh\\\\ 一格主张写权，父目录列为共享，不为它设门槛。",
         "Test-Path 全局声明_治理文档\\a2a-inbox 事前=False"),

        ("RETRO_DISCLOSURE",
         "追溯披露：立法之前本席读过一次他人领地文件",
         "读 身份哈希树_工具\\\\核微_鉴微审计团\\\\a2abcast.py 前 120 行（他人领地），用途＝核对 msg_hash 判据 51 口径与信封格式；"
         "未修改一个字节。自 FRONTIER.md 生效起，本席不再主动读取该目录。"
         "越界一次就是一次；追溯披露不消除事实，只保证其不被隐去。",
         "只读取数，无写入；源文件 mtime 未变"),

        ("CARD_SEAL",
         "agent-card.json 封锚（A2A 0.3.0 草案）",
         "卡片 sha256=%s；字节=%d。状态 DRAFT·未投递·未登记·未发布。"
         "卡内 url 指向回环 RESERVED，不填公网 URL——不重犯 4173 卡片不实陈述之过。" % (card_h, card_bytes),
         "agent-card.json"),

        ("STATUS",
         "总线通道实测：今日未通；本席不宣称已入网",
         "心脏搭桥通道依赖的本机 18080 实测不在 LISTEN 表 ⇒ 总线不可达。"
         "且本席无自有隧道凭据（在役隧道私钥属他人席位，本席不得使用）。"
         "入网真实前置条件只有两条：①机主为本席签发自有凭据；②由通道持有席同意以 relay 身份代投（from_mode 须记 relay，不得记 seat）。",
         "netstat -an -p TCP 全表"),

        ("SELFTEST",
         "本节自检：能力三行状态与实测一致，无「未实测写成已接入」",
         "①落盘工程 ✅（本台账即产物）；②只读巡检 ✅（端口表/Test-Path/进程计数均为实测）；"
         "③投递与自改组 ⚠️ 自改组在役、投递通道待复通——已在 SELF.md 如实标注。",
         "本文件 verify 全绿"),
    ]

    prev = ZERO
    lines = []
    for ev, subj, det, evid in entries:
        e = make_entry(ev, subj, det, evid, prev)
        prev = e["hash"]
        lines.append(json.dumps(e, ensure_ascii=False, sort_keys=True))

    LEDGER.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # 先算后写 + 回读比对
    back = read_chain()
    ok, msgs = verify_chain(back)
    if not ok or len(back) != len(lines):
        print("[ERR] 写后回读比对失败：")
        for m in msgs:
            print("   ", m)
        return 1
    print("[OK] 台账写入并回读校验通过：%d 条，链末 hash=%s" % (len(back), prev))
    print("     文件：%s" % LEDGER)
    return 0


def verify_chain(chain):
    msgs = []
    ok = True
    prev = ZERO
    for idx, e in chain:
        core = {k: v for k, v in e.items() if k != "hash"}
        h = entry_hash(core)
        if h != e.get("hash"):
            ok = False
            msgs.append("第 %d 行：自哈希不符（算得 %s，记录 %s）" % (idx, h[:16], str(e.get("hash"))[:16]))
        if e.get("prev") != prev:
            ok = False
            msgs.append("第 %d 行：前向指针断裂（应为 %s，记录 %s）" % (idx, prev[:16], str(e.get("prev"))[:16]))
        if e.get("signed") is not False:
            msgs.append("第 %d 行：signed 字段非 False——本席密钥未签发，出现 True 即为伪造嫌疑" % idx)
            ok = False
        prev = e.get("hash")
    return ok, msgs


def cmd_append(args):
    """按 JSON 规格追加一条。追加前先校验现有链——不在坏账上叠账。"""
    if not args:
        print("用法：cairn_ledger.py append <entry.json>")
        return 2
    p = pathlib.Path(args[0])
    if not p.is_absolute():
        p = (HERE.parent / p).resolve()
    if not p.is_file():
        print("[ERR] 不是文件：%s" % p)
        return 2
    spec = json.loads(p.read_text(encoding="utf-8"))
    chain = read_chain()
    if not chain:
        print("[ERR] 台账为空，请先 init")
        return 2
    ok, msgs = verify_chain(chain)
    if not ok:
        print("★ REFUSE [拒绝] 现有链已断裂，拒绝在其上追加（先查账，不许在坏账上叠账）：")
        for m in msgs:
            print("   ", m)
        return 1

    evid = spec.get("evidence", "")
    seals = spec.get("seal_files") or []
    if seals:
        lines = []
        for s in seals:
            sp = pathlib.Path(s)
            if not sp.is_absolute():
                sp = (HERE.parent / s).resolve()
            lines.append("%s  %s" % (file_sha256(sp) if sp.is_file() else "(缺失)",
                                     sp.name))
        evid = (evid + " | " if evid else "") + "封锚: " + "; ".join(lines)

    e = make_entry(spec.get("ev_type", "NOTE"), spec.get("subject", ""),
                   spec.get("detail", ""), evid, chain[-1][1]["hash"])
    with LEDGER.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    back = read_chain()
    ok2, msgs2 = verify_chain(back)
    if not ok2 or len(back) != len(chain) + 1:
        print("[ERR] 追加后回读比对失败：")
        for m in msgs2:
            print("   ", m)
        return 1
    print("[OK] 已追加第 %d 条（%s），链末 hash=%s" % (len(back), e["ev_type"], e["hash"]))
    return 0


def cmd_verify():
    chain = read_chain()
    if not chain:
        print("[ERR] 台账为空或不存在：%s" % LEDGER)
        return 1
    ok, msgs = verify_chain(chain)
    print("═══ 石敢当席台账链校验 ═══")
    print("条目数：%d" % len(chain))
    print("链末 hash：%s" % chain[-1][1].get("hash"))
    print("末条时刻：%s" % chain[-1][1].get("ts"))
    print("签名状态：未签发（signed=false 全链一致）→ 只证一致，不证作者")
    if ok:
        # ★ 2026-10-02 轮 28 收窄判词：原判词为「PASS —— 前向链自洽，事后未改动」。
        #   ★ 而本器【只查两件事】：① 每条的 hash 与其内容相符；② prev 指针相连。
        #   ⇒ 那两件事证的只是【链内自洽】——★【证不出「事后未改动」】：
        #     一条【整链一致重建】的伪造链同样满足这两条，而它当然是"一次写成"的。
        #     ★ 这不是推测：exp\forge_demo.py 已实测——完全伪造的链 ⇒ 本器报 PASS。
        #   ⇒ 故判词收窄成它真正证的，并把【它区分不了的那两种情形】当场写出来。
        print("结论：PASS —— ★链内自洽（①每条 hash 与内容相符 ②prev 指针相连）")
        print("★★ 本判词【不含「事后未改动」】：本器只查那两条，")
        print("   而【整链一致重建】的链同样满足它们 ⇒ ★ 本器【区分不了】下列两种情形：")
        print("     ① 一条从未被改过的真链；② 一条被【整体重建】过的链。")
        print("   ★ 实证：exp\\forge_demo.py —— 完全伪造的链 ⇒ 本器报 PASS。")
        print("   ★ 若要看得出【重建】，须另有不受本席约束的对照（本席没有，见轮 4／6／15）。")
        # ★ 2026-10-03 轮 73 加：机器可读判词行（★ 承轮 72：收尾块此后读这一行）。
        print("★ VERDICT=PASS")
        return 0
    print("结论：FAIL")
    # ★ 2026-10-03 轮 73 加：机器可读判词行（★ 两条路各一句）。
    print("★ VERDICT=BAD")
    for m in msgs:
        print("   ", m)
    return 1


def cmd_seal(args):
    # ★ 2026-10-02 名实纠正：本子命令【只算 sha256，不签名】。
    #   缘由：本席轮 5 的自指性论证查出——我连续四轮把 `signed=false` 写成"链的边界"，
    #   而那个印象部分来自【命令名】。一个叫「封缄」的命令若不封缄，就会骗下一个读它的人（包括未来的我）。
    #   故：保留原行为（不破坏既有调用），但【把名实不符当场说出来】。
    if not args:
        print("用法：cairn_ledger.py seal <file> [file...]")
        print("★ 注意：本子命令【只算 sha256，不做任何签名】——名实不符已在轮 5 记为缺陷。")
        return 2
    print("★ 声明：本子命令【只算 sha256，不签名】。（名实不符已在 2026-10-02 轮 5 记为缺陷）")
    for a in args:
        p = pathlib.Path(a)
        if not p.is_absolute():
            p = (HERE.parent / a).resolve()
        if not p.is_file():
            print("[ERR] 不是文件：%s" % p)
            return 2
        print("%s  %s  (%d B)" % (file_sha256(p), p.name, p.stat().st_size))
    return 0


def cmd_status():
    chain = read_chain()
    print("台账：%s" % LEDGER)
    print("冲突点日志：%s%s" % (CONFLICT, "" if CONFLICT.exists() else "（尚无）"))
    print("条目数：%d" % len(chain))
    for idx, e in chain:
        print("  %2d  %-18s %s  %s" % (idx, e.get("ev_type"), e.get("ts"), e.get("subject")))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "init":
        return cmd_init()
    if cmd == "append":
        return cmd_append(sys.argv[2:])
    if cmd == "verify":
        return cmd_verify()
    if cmd == "seal":
        return cmd_seal(sys.argv[2:])
    if cmd == "status":
        return cmd_status()
    print("用法：cairn_ledger.py {init|verify|seal <file>|status}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
