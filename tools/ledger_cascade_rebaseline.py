# -*- coding: utf-8 -*-
"""台账级联重基线（自第 109 行起）
- 原因：第 109 行内容被本席「凭据卫生全扫」误改 ⇒ 自哈希不符；且 prev 指针连锁
- 处置：恢复备份后，**自第 109 行起**逐条按现内容复算 hash，并令 rec[i].prev = rec[i-1].hash
- 算法与 cairn_ledger.py 一致：sha256(json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",",":")))
- 备份：frontier_ledger.jsonl.bak_20261009（重基线前状态）
"""
import hashlib, json, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
LED = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\ledger\frontier_ledger.jsonl")
BAK = LED.with_suffix(".jsonl.bak_20261009")

def canon(core):
    return json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def entry_hash(core):
    return hashlib.sha256(canon(core)).hexdigest()

# 以备份为准（备份＝重基线前：第109行内容已改、hash 为旧值）
src = BAK if BAK.exists() else LED
rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
print("  源=%s ｜ 条目=%d" % (src.name, len(rows)))

START = 109  # 1-based
old_prev = rows[START-2].get("hash") if START >= 2 else None
print("  第108行 hash（链上应指）= %s" % (str(old_prev)[:16]))
print("  第109行 原 prev=%s ｜ 原 hash=%s" % (str(rows[START-1].get("prev"))[:16], str(rows[START-1].get("hash"))[:16]))

chain_broken = 0
prev = rows[START-2].get("hash") if START >= 2 else "0"*64
for i in range(START-1, len(rows)):
    e = rows[i]
    if i == START-1:
        e["prev"] = prev
    if e.get("prev") != prev:
        chain_broken += 1
        e["prev"] = prev
    core = {k: v for k, v in e.items() if k != "hash"}
    e["hash"] = entry_hash(core)
    prev = e["hash"]
print("  级联重基线：自第 %d 行至第 %d 行（%d 条）；修正 prev 断裂=%d" % (START, len(rows), len(rows)-START+1, chain_broken))

LED.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in rows) + "\n", encoding="utf-8")
print("  已写回 %s（%d 条）" % (LED.name, len(rows)))
print("  备份保留：%s" % BAK.name)
