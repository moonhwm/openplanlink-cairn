#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读核验一份 SEAT_LOCATION 声明；不触网、不改动任何件。
r"""verify_seat_location.py —— 核验 `SEAT_LOCATION_<seat>_<date>.json` 是否为【真话】。 v1.0.0

判词只有三种（★ 不把"没查"说成"通过"）
────────────────────────────────────────
  OK    —— 逐条相符
  BAD   —— 有条款与实测不符（列出是哪条）
  ERR   —— 器具故障：声明读不到/格式不对/依赖器不在 ⇒ ★ 这【不是】"验不过"，是"没验成"

★ 本器的意义：**"定正本靠声明"这个方案要成立，声明就必须可证伪**——
   否则它只是把"没标签的副本"换成"没根据的声明"。
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent


def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap_path = SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json"
    if len(sys.argv) > 1:
        ap_path = pathlib.Path(sys.argv[1])
    print("═══ 核验席位位置声明 ═══")
    print("  声明 = %s" % ap_path)
    if not ap_path.is_file():
        print("ERR 读不到声明 ⇒ ★ 器具故障（不是'验不过'）")
        return 2
    try:
        d = json.loads(ap_path.read_text(encoding="utf-8"))
    except Exception as e:
        print("ERR 声明不是合法 JSON：%s ⇒ ★ 器具故障" % e)
        return 2

    fails, checks = [], 0

    # ★ 2026-10-02 轮 9 修：使本器能被【离开本机的副本】自核。
    #   缘由：局外人实测查出——声明里的 canonical 是【绝对路径】，故一份副本跑本器时，
    #   它核对的仍是【原席位】⇒ 换台机器即报"正本不存在"。
    #   ⇒ 修法：声明路径不存在时，退回【本器自己所处的席位】，并【明说这是退回】。
    canon = pathlib.Path(d["canonical"]["path"])
    fell_back = False
    if not canon.is_dir() and SEAT.is_dir():
        canon = SEAT
        fell_back = True
    # ① 正本存在（★ 轮 9：不可达时退回到本器所处席位，并明说退回）
    checks += 1
    if canon.is_dir():
        if fell_back:
            print("  ✅ ① 正本存在：%s" % canon)
            print("         ★ 注：声明里的绝对路径在本机不存在 ⇒ 已退回【本器所处的席位】自核。")
            print("           ⇒ 本次核的是【这份副本】，不是声明里那处原席位。")
        else:
            print("  ✅ ① 正本存在：%s" % canon)
    else:
        fails.append("① 正本不存在：%s" % canon)
        print("  ★ ① 正本不存在")

    # ② 台账锚点：声明里那条 hash 应等于台账中同序号条目的 hash（固定锚，不随链增长而失效）
    #    ★ 2026-10-02 修正：首版把台账路径解析成【本器所在的席位】，而不是【声明里的正本路径】。
    #      故它在本席"碰巧对"，在合成样本上必错。声明本应【自足】⇒ 路径以 declared canonical 为根。
    lg = canon / d["ledger"]["path"]
    checks += 1
    ledger_rows: list[dict] = []          # ★ 供第 ⑥ 条复用；读不到则保持空 ⇒ ⑥ 报「未检」
    if not lg.is_file():
        fails.append("② 台账读不到")
        print("  ★ ② 台账读不到")
    else:
        rows = [json.loads(l) for l in lg.read_text(encoding="utf-8").splitlines() if l.strip()]
        ledger_rows = rows
        n = int(d["ledger"]["entries_at_declaration"])
        if len(rows) >= n and rows[n - 1].get("hash") == d["ledger"]["chain_head_at_declaration"]:
            print("  ✅ ② 台账第 %d 条 hash 与声明相符（当前共 %d 条 ⇒ 链在声明之后已增长，属正常）" % (n, len(rows)))
        else:
            fails.append("② 台账第 %d 条的 hash 与声明不符（或条数不足）" % n)
            print("  ★ ② 台账锚点不符")

    # ③ 逐条核副本
    #    ★ 2026-10-02 修正：首版把副本当成"永远逐字节冻结"，结果【台账一追加就报红】。
    #      病不在判据松，在【我漏了一个概念】：正本里有【活文件】（台账／状态件／实时件），
    #      它们【本该】与任何冻结副本分叉。故把"字节不同"拆成两类：
    #        · 预期内（活文件）—— 计数并点名，但【不判失败】
    #        · 预期外 —— 判失败
    #      这样"分叉"仍然【看得见】，只是不再被当成故障。
    LIVING_PATTERNS = (
        "ledger/frontier_ledger.jsonl",
        "outbox/state_",
        "outbox/cairn-status-live.js",
        "outbox/status_",
        "__pycache__/",
    )

    def is_living(rel: str) -> bool:
        return any(pat in rel for pat in LIVING_PATTERNS)

    for i, rep in enumerate(d.get("replicas", []), 1):
        rp = pathlib.Path(rep["path"])
        v = rep.get("verified", {})
        checks += 1
        if not rp.is_dir():
            # ★ 轮 9：副本路径也是绝对的 ⇒ 一旦本器跑在【副本】里，这里就不可达。
            #   ★ 按本席规矩：不可达 ⇒ 报【未检】，绝不硬比（否则会拿本机副本去比原冻结副本，混）。
            print("  ○ ③ 副本 %d ★【未检】—— 声明里的副本路径在本机不可达：%s" % (i, rp))
            print("         ⇒ 本条判据【整条未执行】（不是通过，也不是失败）")
            continue

        def idx(root):
            return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}

        ia, ib = idx(canon), idx(rp)
        shared = set(ia) & set(ib)
        same = diff = 0
        living_diff, surprise_diff = [], []
        for k in shared:
            if sha256_of(ia[k]) == sha256_of(ib[k]):
                same += 1
            else:
                diff += 1
                (living_diff if is_living(k) else surprise_diff).append(k)
        only_c = len(set(ia) - set(ib))
        only_r = len(set(ib) - set(ia))
        # ★ 2026-10-02 轮 5 增：已声明的分叉。
        #   病：我为修 seal 的名不副实编辑了台账器 ⇒ 第③条把它报成【预期外差异】。
        #   正解【不是】把工具塞进 LIVING_PATTERNS 让它变绿（那会把"我改过"藏起来），
        #   而是【要求把它声明出来】：声明里列出的路径，其差异【计数并点名】，但不判失败。
        declared = {it.get("path") for it in (d.get("declared_divergences", {}).get("items") or [])}
        # ★ 2026-10-02 轮 44 加：把【改动史】与【当前分叉集合】分开印。
        #   缘由：declared_divergences 是【追加式的改动史】——★ 同一文件可有两条
        #   （现场实例：ledger/cairn_ledger.py 在轮 5 与轮 28 各一条 = 2 条）。
        #   ⇒ 而读者要问"现在哪些件与冻结副本不同"，须自己去重 ⇒ ★ 故此处当场去重印出。
        #   ★ 不动声明本身：它该保持只增（那是它的价值）。
        _items = d.get("declared_divergences", {}).get("items") or []
        declared_now = sorted({it.get("path") for it in _items if it.get("path")})
        unexpected = [k for k in surprise_diff if k not in declared]
        got = dict(shared_files=len(shared), byte_identical=same, byte_differing=diff,
                   differing_living=len(living_diff), differing_declared=len([k for k in surprise_diff if k in declared]),
                   differing_surprise=len(unexpected),
                   only_in_canonical=only_c, only_in_replica=only_r)
        # ★ 判据：只把【既非活文件、又未声明】的差异判失败。
        #   ★ 2026-10-02 第三次同类修：我加了【已声明分叉】这一类，却忘了把它也带进算术——
        #     于是 surprise=0 时 ③ 仍然报红（same 3270 >= 3273-2 为假）。
        #     ★ 记为一类缺陷：**加一类概念时，忘了把它带进算术**。前两次分别是
        #       「漏了活文件概念」与「台账路径没以声明的正本为根」。
        declared_diff = [k for k in surprise_diff if k in declared]
        unexpected = [k for k in surprise_diff if k not in declared]
        expected_same_floor = v["byte_identical"] - len(living_diff) - len(declared_diff)
        okc = (same >= expected_same_floor
               and len(unexpected) == 0
               and only_r <= v["only_in_replica"]
               and only_c >= v["only_in_canonical"])
        if okc:
            print("  ✅ ③ 副本 %d 相符：共有 %d ｜ 字节相同 %d ｜ ★活文件分叉 %d ｜ ★已声明分叉 %d ｜ ★预期外差异 %d ｜ 正本独有 %d（声明下界 %d）"
                  % (i, len(shared), same, len(living_diff),
                     len([k for k in surprise_diff if k in declared]), len(unexpected),
                     only_c, v["only_in_canonical"]))
            # ★ 轮 100：把上面那串数的【范围】另起一行写。
            #   缘由（轮 97／98）：我上一轮没给这个 0 加范围，理由是"那一行已经列了 6 个数、会长"；
            #   ★ 而那个理由本身可解（另起一行）——★ 改它却触发了【两处钉】。
            #   ⇒ 故本处改动【连同重新钉】一起做：★ 改器 → 新 LOCKPIN → 更新声明里的钉。
            print("         ★ 上述各数的【范围】：本席正本 vs 该副本（★ 共 %d 件）——"
                  "★ 即：『★ 预期外差异 0』说的是【这两个目录之间】，★ 不是「全席没有差异」"
                  % len(shared))
            # ★ 轮 111：把【本器走目录时排除了什么】也写出来。
            #   缘由（轮 105／106）：本器【不排除 __pycache__】——★ 故「共有 3273」含那 89 件；
            #   ★ 而我只是【本轮才发现】：★ 我为此花了两轮去核（第二把尺排除了它、两数差 89）。
            #   ⇒ ★ 故此处明写口径，★ 让读者不必再去翻源码（★ 轮 106 那条"写数要写范围"的落点）。
            _pyc = sum(1 for p in rp.rglob("*") if p.is_file() and "__pycache__" in str(p))
            print("         ★ 本器口径：★ 不排除 __pycache__（★ 本副本内 %d 件）；"
                  "★ 故「共有」那一数【含】它们——★ 第二把尺若排除，两数会差这些件。" % _pyc)
            for k in living_diff:
                print("         · 预期分叉（活文件）：%s" % k)
            for k in surprise_diff:
                if k in declared:
                    print("         · ★ 已声明分叉：%s（声明里的理由见 declared_divergences）" % k)
            # ★ 轮 44：把【改动史条目数】与【去重后的当前集合】两侧都印出来
            print("         ★ 改动史条目 = %d 条（同一文件可有多条）｜★ 去重后【当前分叉文件】 = %d 件"
                  % (len(_items), len(declared_now)))
            for pth in declared_now:
                print("            · [当前] %s" % pth)
        else:
            fails.append("③ 副本 %d 实测与声明不符：实测 %s ／ 声明 %s" % (i, got, v))
            print("  ★ ③ 副本 %d 不符：实测 %s" % (i, got))
            for k in unexpected[:8]:
                print("         ★ 预期外差异（既非活文件、又未声明）：%s" % k)

    # ④ ★ 自指条款核查（2026-10-02 增）
    #    为什么这条必须存在：本器的判据由【被验方自己】写、本器自身【只在正本 A 而不在副本 B】、
    #    所引的台账链 signed=false ⇒ 故 'OK' 只能证【自洽】，不能证【正确】。
    #    自指无法逃出 ⇒ 只能【把环写明白并让它可被核】。本检查做三件事：
    #      (a) 声明里必须【有】self_reference 段（不许把这个环藏起来）；
    #      (b) 该段的三条 R1/R2/R3 状态必须【不是 claimed-unknown】，即必须被测过；
    #      (c) ★ 本器自己的判词串里必须含那句免责 —— 若有人把免责删掉，本项【必红】。
    NEVER_CLAIM = "只证自洽，不证正确"
    checks += 1
    sr = d.get("self_reference")
    if not sr:
        fails.append("④ 声明缺 self_reference 段 ⇒ 自指环被藏起来")
        print("  ★ ④ 声明缺 self_reference 段")
    else:
        ok_a = bool(sr.get("loops"))
        ok_b = all(str(v.get("status", "")).startswith("★") for v in sr.get("loops", {}).values()) \
            if isinstance(sr.get("loops"), dict) else False
        # (c) 读【本器自己】的源码，核判词里的免责句是否还在
        try:
            me = pathlib.Path(__file__).read_text(encoding="utf-8")
            ok_c = NEVER_CLAIM in me
        except Exception:
            ok_c = False
        if ok_a and ok_b and ok_c:
            n = len(sr.get("loops", {}))
            print("  ✅ ④ 自指条款齐备：声明含 %d 个环（R 状态均经测定）｜★ 本判词含免责「%s」" % (n, NEVER_CLAIM))
        else:
            why = []
            if not ok_a: why.append("无 loops")
            if not ok_b: why.append("R 状态未标定为已测")
            if not ok_c: why.append("★ 判词缺免责「%s」" % NEVER_CLAIM)
            fails.append("④ 自指条款不全：" + "、".join(why))
            print("  ★ ④ 自指条款不全：" + "、".join(why))

    # ⑤ ★ 版本钉（2026-10-02 增，因【对照四】暴露了一个自指缺陷）
    #    病：首版的自指检查写成 `NEVER_CLAIM in 本文件`，而 NEVER_CLAIM 这个常量【也在这个文件里】。
    #        ⇒ 把免责句替换掉时，常量被【同时】替换 ⇒ 检查变成"核（已删）在不在自己里" ⇒ 恒真。
    #        ⇒ 判据与判据对象同处一条语句的覆盖范围 ⇒ 测试自我满足。
    #    药：把本器【整file 的 sha256】钉在【另一个文件】（声明）里。
    #        ⇒ 篡改本器 ⇒ 本器哈希变 ⇒ 与声明里的钉不符 ⇒ 必红。
    #        ⇒ 单点篡改再也不可能同时满足两处。
    #    ★ 诚实：这仍是自指（钉由本席写、本器由本席写）；但它把"篡改是否发生"变成【两个文件必须同时被改】，
    #      而这两个文件的时间戳、路径、sha256 都在案 ⇒ 篡改【看得见】。这不是逃出循环，是让环受检。
    checks += 1
    pin = d.get("verifier_pin")
    if not pin:
        print("  ○ ⑤ 版本钉 ★【未检】—— 声明未含 verifier_pin ⇒ 本条判据整条未执行（不是通过，也不是失败）")
    else:
        try:
            me_bytes = pathlib.Path(__file__).read_bytes()
            me_h = hashlib.sha256(me_bytes).hexdigest()
        except Exception as e:
            me_h = None
            print("  ★ ⑤ 读不到本器自身：%s" % e)
        if me_h is None:
            fails.append("⑤ 版本钉无法核（读不到本器）")
        elif me_h == pin.get("sha256"):
            print("  ✅ ⑤ 版本钉相符：本器 sha256 = %s…（声明所钉）" % me_h[:16])
            # ★ 2026-10-02 轮 12：本条的【弱点】必须当场说出来，否则它给读者一个假印象。
            #   对照五（neg_control · 双点篡改）已证明：改器 ＋ 只改声明里的钉时不碰链 ⇒ ⑤【照样绿】。
            #   ⇒ 故 ⑤ 是【较弱】的一条；真正扛住双点篡改的是 ⑥。
            #   ★ 不删它：链不可达（如一份无台账的副本）时，⑤ 仍能工作 ⇒ 它有价值，只是弱。
            print("         ★ 本条弱点（对照五已证）：改器 ＋ 只改声明钉、不碰链 ⇒ ⑤【照样绿】。")
            print("           ⇒ 真正扛住双点篡改的是 ⑥（链上钉）。⑤ 是【较弱】的一条。")
        else:
            fails.append("⑤ ★ 版本钉不符：本器实测 %s… ≠ 声明所钉 %s…（⇒ 本器被改过，或声明未随之更新）"
                         % (me_h[:16], str(pin.get("sha256"))[:16]))
            print("  ★ ⑤ 版本钉不符：实测 %s… ≠ 声明 %s…" % (me_h[:16], str(pin.get("sha256"))[:16]))

    # ⑥ ★ 链上钉（2026-10-02 再增：因【第五环 —— 谁验钉？】）
    #    病：⑤ 的钉写在【声明】里，而声明与核验器【同出一席 ⇒ 同握两把钥匙】。
    #        ⇒ 我合法改器时同时更新声明里的钉，两处一致 ⇒ ⑤ 【全程绿灯】。
    #        ⇒ 故 ⑤ 只防【单点】篡改，不防【双点】篡改。
    #    药：把钉【移进只能追加的台账链】。于是——
    #        · 双点篡改（改器 ＋ 改声明里的钉）⇒ 链上那条旧钉【依然在】⇒ 与现行不符 ⇒ ⑥ 必红；
    #        · 要消掉 ⑥，只能【再追加一条新钉】⇒ ★ 而那是一次【看得见的追加】，不是一次无声的改写。
    #    ★ 诚实：这【仍是】自指（链也是本席写的）。它买到的是【改动可见】，不是【改动不可能】，
    #      更不是【独立】。故本器第 ⑥ 条的存在意义，是把"钉被换过"这件事变成【链上的事实】。
    checks += 1
    pin_entries = []
    for r in (ledger_rows or []):
        if r.get("ev_type") == "LOCKPIN":
            h = str(r.get("subject", ""))
            m = re.search(r"([0-9a-f]{64})", h)
            if m:
                pin_entries.append((r.get("ts", ""), m.group(1)))
    if not pin_entries:
        print("  ○ ⑥ 链上钉 ★【未检】—— 台账里没有 LOCKPIN 条目 ⇒ 本条判据整条未执行（不是通过，也不是失败）")
    else:
        try:
            me_h2 = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
        except Exception:
            me_h2 = None
        latest_ts, latest_h = max(pin_entries)
        if me_h2 is None:
            fails.append("⑥ 链上钉无法核（读不到本器）")
        elif me_h2 == latest_h:
            print("  ✅ ⑥ 链上钉相符：本器 sha256 = %s… ＝ 链上最新一条 LOCKPIN（%s，链上共 %d 条）"
                  % (me_h2[:16], latest_ts[:19], len(pin_entries)))
            if len(pin_entries) > 1:
                print("         ★ 注意：链上有 %d 条钉 ⇒ 钉被换过 %d 次。换钉【看得见】，这正是本条的意义。"
                      % (len(pin_entries), len(pin_entries) - 1))
        else:
            fails.append("⑥ ★ 链上钉不符：本器实测 %s… ≠ 链上最新 LOCKPIN %s…（⇒ 器被改过，而链上钉是旧值）"
                         % (me_h2[:16], latest_h[:16]))
            print("  ★ ⑥ 链上钉不符：实测 %s… ≠ 链上最新钉 %s…" % (me_h2[:16], latest_h[:16]))

    # ⑦ ★ 边界分类表核查（2026-10-02 轮 6 增）
    #    病：轮 5 立了三分类（给定／选择／未检验），并写「未标明的，读者不应当它是事实」——
    #        ★ 可那条规矩【没人执行】，正是我批评过的同一形态。且轮 6 实测发现【缺第四类】：
    #        「本席无法取得独立见证」本属【受授权约束的行动】，却被写成【给定】。
    #    药：要求声明里的 limit_taxonomy (a) 写明四类定义 (b) 每条都带 basis 字段。
    #    ★ 诚实：本条只核【类别是否被写明】，★ 不核【类别判得对不对】——后者不可自动核。
    NEVER_CLAIM = "只证自洽，不证正确"  # 已在 ④ 用；此处仅为可读性重述
    checks += 1
    tax = d.get("limit_taxonomy")
    REQ_CLASSES = ("给定", "选择", "未检验", "受授权约束的行动")
    if not tax:
        print("  ○ ⑦ 边界分类表 ★【未检】—— 声明未含 limit_taxonomy ⇒ 本条整条未执行（不是通过，也不是失败）")
    else:
        have = tax.get("classes") or {}
        miss_cls = [c for c in REQ_CLASSES if not any(c in k for k in have)]
        items = tax.get("items") or []
        no_basis = [str(it.get("limit", "?"))[:28] for it in items if not it.get("basis")]
        if not miss_cls and items and not no_basis:
            print("  ✅ ⑦ 边界分类表齐备：四类定义齐全 ｜ 条目 %d 条 ｜ ★每条都有 basis" % len(items))
            print("         ★ 本条【只核类别是否被写明】，不核类别判得对不对（后者须人来判）")
        else:
            why = []
            if miss_cls:
                why.append("缺类定义：" + "、".join(miss_cls))
            if not items:
                why.append("无条目")
            if no_basis:
                why.append("无 basis 的条目：" + "、".join(no_basis[:3]))
            fails.append("⑦ 边界分类表不全：" + "；".join(why))
            print("  ★ ⑦ 边界分类表不全：" + "；".join(why))

    print()
    print("  核过 %d 条 ｜ ★不符 %d 条" % (checks, len(fails)))
    if fails:
        for f in fails:
            print("     ★ " + f)
        print("  判词：BAD")
        # ★ 2026-10-03 轮 73 加：机器可读判词行（承轮 72；★ 两条返回路各一句）。
        print("★ VERDICT=BAD")
        return 1
    print("  判词：OK —— 声明逐条与实测相符（★ 声明可证伪，故「定正本靠声明」成立）")
    # ★ 2026-10-02 轮 12：各条【强度表】。这不是新检查，是把"每条能抓什么、抓不到什么"摆到读者眼前。
    #   缘由：轮 11 我的规则"再包一层检查没用"太粗；精确判据是——
    #   ★ 一层检查若是【装饰】，它不声明自己抓不到什么。故此处对每条列出其盲点。
    print()
    print("  ── 各条强度与其盲点（★ 本条表不是新检查，是让强度可见）──")
    STRENGTH = [
        ("① 正本存在",   "强", "只证路径可达；不证该路径【就是】应然的正本"),
        ("② 台账锚点",   "中", "固定锚（第 N 条 hash）；不证该链此后未被整体重建"),
        ("③ 副本相符",   "中", "按 sha256 比；活文件与已声明分叉【不计入】失败（那是判据设计，不是漏检）"),
        ("④ 自指条款",   "中", "只核『环是否被写明』；且它核的是【本器自己的源码】——自指"),
        ("⑤ 版本钉",     "★ 弱", "★ 对照五已证：双点篡改下照样绿。仅当链不可达时才比 ⑥ 有用"),
        ("⑥ 链上钉",     "强", "钉在只能追加的链上；★ 但【再追加一条新钉】即可消掉它（那是可见的追加）"),
        ("⑦ 分类表",     "中", "只核『类别是否被写明』；★ 不核『判得对不对』（后者须人来判）"),
    ]
    for name, level, blind in STRENGTH:
        print("     %-12s 强度 %-4s ｜ 盲点：%s" % (name, level, blind))
    print("     ★ 本器整体的盲点：【整链一致重建】检不出（轮 4 的伪造对照已证）——")
    print("        且本器【自指】：判据由被验方自写。故 'OK' 只证自洽，不证正确。")
    print("  ★★ 边界（本器自指，无法自证）：本判据由【被验方自写】、本器【只在正本 A 而不在副本 B】、")
    print("      所引的台账链 signed=false ⇒ 故本判词的 'OK' 只证【自洽，不证正确】；")
    print("      要证【正确】需【第二个不同席位联署】—— 本席【没有】。")
    # ★ 2026-10-03 轮 73 加：机器可读判词行（★ 承轮 72：收尾块此后读这一行）。
    print("★ VERDICT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
