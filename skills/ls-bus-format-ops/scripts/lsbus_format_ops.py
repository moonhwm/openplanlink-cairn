#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""lsbus_format_ops.py —— 总线格式运维（`ls-bus-format-ops` 之器物）v1.0.0

## 立法定位（★本件为「全权授权…初始化」下之首版）
A2A 网络中，各席皆往"总线"写件，然**格式无统一** ⇒ 三类病：
  ①**同件异记**（同一件在不同席之记法不同，无法对账）
  ②**重复入总**（同内容多条目，总线信噪比下降）
  ③**有件无账 / 有账无件**（磁盘与索引漂移，审计追溯断链）
本器即为此三病之**机械处置**：**统一条目格式 ＋ 校验 ＋ 去重规范化 ＋ 漂移扫描**。

## 条目格式（canonical bus entry，一行一 JSON；`bus.jsonl`）
```json
{"seq": 1, "id": "<sha256 前 16 位>", "ts": "2026-10-08 13:00:00 +0800",
 "seat": "a2a-node-local", "kind": "artifact|pack|note|skill",
 "path": "<相对总线根之路径>", "bytes": 1234, "sha256": "<64hex>", "refs": []}
```
**必填**：seq / id / ts / seat / kind / path / bytes / sha256。
**id 规则**：`sha256` 之前 16 位（同内容同 id ⇒ 天然去重键）。
**seq 规则**：自 1 起**严格递增且无跳号**（与事件链同法）。

## 子命令
```bash
python lsbus_format_ops.py emit    --bus <总线根> --path <件> [--kind artifact] [--seat <席>] [--refs a,b]
python lsbus_format_ops.py validate <bus.jsonl>          # 0 通过 / 1 有缺陷（逐行报）/ 2 未测（空）
python lsbus_format_ops.py norm    <bus.jsonl> [--apply] # 去重＋排序；默认只报不改
python lsbus_format_ops.py scan    --bus <总线根>        # 漂移：有账无件 / 有件无账
python lsbus_format_ops.py --smoke                       # 自检：emit→validate→norm→scan 全链
```
**性质**：`emit`／`norm --apply` 为**写操作**（须显式指定）；其余只读。**不删任何内容件**（只动索引）。
**零值**：本器不读写凭据；不输出 MAC／IP／密钥。

## 与既有件之关系
- `exp/lsprobe.py`（Linux `ls` 真机探针）：**探环境**；本器**探总线**——互补。
- `exp/push_all.py`（三面推送）：**外送**；本器**内账**——互补。
- `ledger/frontier_ledger.jsonl`（**决策台账**）；`ops/ops_event.jsonl`（**事件链**）：
  本器之 `bus.jsonl` 为**第三账**（**件之账**）⇒ **三账分立，勿混**。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
TZ = datetime.timezone(datetime.timedelta(hours=8))
REQ = ("seq", "id", "ts", "seat", "kind", "path", "bytes", "sha3_512")
KINDS = ("artifact", "pack", "note", "skill", "other")


def _ts() -> str:
    return datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S +0800")


FULL_HASH_MAX = 4 * 1024 * 1024  # v1.1：梯度三档之全量上限（采 Kimi 侧 v2.1 定谳）
TAIL_HEAD = 1 * 1024 * 1024      # v1.1：>4MB 件头尾采样各 1MB
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules"}  # v1.1：默认排除（承 Kimi 侧定谳）


def _norm(b: bytes) -> bytes:
    """v1.2：SHA3-512 树口径之 norm（照仓内 merkle.cjs：latin1 往返＋CRLF→LF）。"""
    return b.decode("latin1").replace("\r\n", "\n").encode("latin1")


def graded_hash(p: pathlib.Path):
    """v1.2 梯度指纹（SHA3-512 树口径：单文件叶即根）：
    <=4MB 全量（full）；>4MB 头尾各 1MB+size 合成（sampled）。返回 (hex128, hash_mode)。"""
    size = p.stat().st_size
    if size <= FULL_HASH_MAX:
        with p.open("rb") as f:
            data = f.read()
        return hashlib.sha3_512(_norm(data)).hexdigest(), "full"
    h = hashlib.sha3_512()
    h.update(_norm(str(size).encode()))
    with p.open("rb") as f:
        h.update(_norm(f.read(TAIL_HEAD)))
        f.seek(max(0, size - TAIL_HEAD))
        h.update(_norm(f.read(TAIL_HEAD)))
    return h.hexdigest(), "sampled"


def read_bus(p: pathlib.Path) -> list:
    if not p.exists():
        return []
    out = []
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append((i, json.loads(line)))
        except Exception as e:  # 保留行号以便报错
            out.append((i, {"__parse_error__": str(e)}))
    return out


def cmd_emit(a) -> int:
    bus_root = pathlib.Path(a.bus)
    idx = bus_root / "bus.jsonl"
    src = pathlib.Path(a.path)
    if not src.exists():
        print("★ 待入总之件不存在 ⇒ **未测**（不以 0 条冒充成功）")
        return 2
    try:
        rel = str(src.resolve().relative_to(bus_root.resolve())).replace("\\", "/")
    except Exception:
        rel = src.name
    dg, hmode = graded_hash(src)
    rows = [r for _, r in read_bus(idx) if "__parse_error__" not in r]
    nid = dg[:16]
    if any(r.get("id") == nid and r.get("hash_mode") == hmode for r in rows):
        print("· 已入总（同 id＋hash_mode，跳过）：%s" % nid)
        return 0
    ent = {"seq": (max([r.get("seq", 0) for r in rows]) + 1) if rows else 1,
           "id": nid, "ts": _ts(), "seat": a.seat, "kind": a.kind,
           "path": rel, "bytes": src.stat().st_size, "sha3_512": dg,
           "hash_mode": hmode,
           "refs": [x for x in (a.refs or "").split(",") if x]}
    bus_root.mkdir(parents=True, exist_ok=True)
    with idx.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ent, ensure_ascii=False) + "\n")
    print("★ 已入总 seq=%d id=%s hash_mode=%s bytes=%d ｜ %s" % (ent["seq"], ent["id"], hmode, ent["bytes"], rel))
    return 0


def _check(rows) -> list:
    errs = []
    if not rows:
        return errs
    prev = 0
    seen = set()
    for ln, r in rows:
        if "__parse_error__" in r:
            errs.append("第%d行：JSON 解析失败（%s）" % (ln, r["__parse_error__"][:60]))
            continue
        for k in REQ:
            if k not in r:
                errs.append("第%d行：缺必填字段 %s" % (ln, k))
        if "sha3_512" in r and (not isinstance(r["sha3_512"], str) or len(r["sha3_512"]) != 128
                                or any(c not in "0123456789abcdef" for c in r["sha3_512"])):
            errs.append("第%d行：sha3_512 非 128 位小写十六进制" % ln)
        if "sha3_512" in r and "id" in r and isinstance(r["sha3_512"], str) and r["sha3_512"][:16] != r.get("id"):
            errs.append("第%d行：id 与 sha3_512 前 16 位不符（id 规则）" % ln)
        if "hash_mode" in r and r["hash_mode"] not in ("full", "sampled"):
            errs.append("第%d行：hash_mode 非法（%s）" % (ln, r.get("hash_mode")))
        if "kind" in r and r["kind"] not in KINDS:
            errs.append("第%d行：kind 非法（%s）" % (ln, r.get("kind")))
        if isinstance(r.get("seq"), int):
            if r["seq"] <= prev:
                errs.append("第%d行：seq 未严格递增（%s ≤ %s）" % (ln, r["seq"], prev))
            elif r["seq"] != prev + 1:
                errs.append("第%d行：seq 有跳号（%s → %s）" % (ln, prev, r["seq"]))
            prev = r["seq"]
        if r.get("id") in seen:
            errs.append("第%d行：id 重复（%s）" % (ln, r.get("id")))
        seen.add(r.get("id"))
    return errs


def cmd_validate(a) -> int:
    rows = read_bus(pathlib.Path(a.busfile))
    if not rows:
        print("★ 总线为空 ⇒ **未测**（不以空为通过）")
        return 2
    errs = _check(rows)
    print("═══ 总线校验（只读）═══")
    print("  行数=%d ｜ 缺陷=%d" % (len(rows), len(errs)))
    for e in errs[:20]:
        print("   ✗ " + e)
    if errs:
        print("  VERDICT=INVALID")
        return 1
    print("  VERDICT=VALID")
    return 0


def cmd_norm(a) -> int:
    p = pathlib.Path(a.busfile)
    rows = [r for _, r in read_bus(p) if "__parse_error__" not in r]
    if not rows:
        print("★ 总线为空 ⇒ **未测**")
        return 2
    seen, kept, dropped = set(), [], []
    for r in sorted(rows, key=lambda x: x.get("seq", 0)):
        key = (r.get("sha256"), r.get("path"))
        if key in seen:
            dropped.append(r)
        else:
            seen.add(key)
            kept.append(r)
    for i, r in enumerate(kept, 1):
        r["seq"] = i
    print("═══ 规范化%s ═══" % ("（写入）" if a.apply else "（只报不改）"))
    print("  原 %d 条 ⇒ 保留 %d 条 ｜ **重复 %d 条**" % (len(rows), len(kept), len(dropped)))
    for d in dropped[:10]:
        print("   · 去重：seq=%s id=%s %s" % (d.get("seq"), d.get("id"), d.get("path")))
    if a.apply:
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
        print("  已写入（原文件以 .bak 备份）")
        (p.with_suffix(p.suffix + ".bak")).write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return 0


def cmd_scan(a) -> int:
    bus_root = pathlib.Path(a.bus)
    rows = [r for _, r in read_bus(bus_root / "bus.jsonl") if "__parse_error__" not in r]
    if not bus_root.exists():
        print("★ 总线根不存在 ⇒ **未测**")
        return 2
    on_disk = {}
    excluded = 0
    for f in bus_root.rglob("*"):
        rel = str(f.resolve().relative_to(bus_root.resolve())).replace("\\", "/")
        if any(seg in EXCLUDE_DIRS for seg in rel.split("/")):
            excluded += 1
            continue
        if f.is_file() and f.name not in ("bus.jsonl",) and not f.name.endswith(".bak"):
            on_disk[rel] = f
    in_bus = {r.get("path") for r in rows}
    no_file = sorted(in_bus - set(on_disk))
    no_rec = sorted(set(on_disk) - in_bus)
    print("═══ 漂移扫描（只读）═══")
    print("  总线根=%s ｜ 账 %d 条 ｜ 盘上件 %d ｜ **v1.1 排除目录 %d 件**" % (bus_root.name, len(rows), len(on_disk), excluded))
    print("  **有账无件**：%d" % len(no_file))
    for x in no_file[:10]:
        print("   ✗ " + x)
    print("  **有件无账**：%d" % len(no_rec))
    for x in no_rec[:10]:
        print("   · " + x)
    return 0 if (not no_file) else 1


def cmd_smoke() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "a.txt").write_text("hello", encoding="utf-8")
        (root / "b.txt").write_text("world", encoding="utf-8")
        idx = root / "bus.jsonl"

        class NS:
            pass
        for name in ("a.txt", "b.txt"):
            n = NS(); n.bus = str(root); n.path = str(root / name); n.seat = "smoke"; n.kind = "artifact"; n.refs = ""
            assert cmd_emit(n) == 0
        # 重复入总应被幂等跳过
        n = NS(); n.bus = str(root); n.path = str(root / "a.txt"); n.seat = "smoke"; n.kind = "artifact"; n.refs = ""
        assert cmd_emit(n) == 0
        rows = read_bus(idx)
        assert len(rows) == 2, "重复入总未被跳过"
        # 校验
        class NA: pass
        na = NA(); na.busfile = str(idx)
        assert cmd_validate(na) == 0
        # 人为造缺陷 ⇒ 须报 INVALID
        idx.write_text(idx.read_text(encoding="utf-8").replace('"seq": 2', '"seq": 5'), encoding="utf-8")
        assert cmd_validate(na) == 1, "跳号未被检出"
        # 修复并规范化
        idx.write_text(idx.read_text(encoding="utf-8").replace('"seq": 5', '"seq": 2'), encoding="utf-8")
        na.apply = False
        assert cmd_norm(na) == 0
        # v1.1 负断言：>4MB 件 ⇒ 必标 hash_mode: sampled（能报才算检出）
        big = root / "big.bin"
        with big.open("wb") as f:
            f.write(b"0" * (FULL_HASH_MAX + 1024))
        n = NS(); n.bus = str(root); n.path = str(big); n.seat = "smoke"; n.kind = "artifact"; n.refs = ""
        assert cmd_emit(n) == 0
        assert any(r.get("hash_mode") == "sampled" for _, r in read_bus(idx)), ">4MB 件未标 sampled"
        # 负断言：空总线 ⇒ 未测（exit 2）
        na.busfile = str(root / "empty.jsonl")
        (root / "empty.jsonl").write_text("", encoding="utf-8")
        assert cmd_validate(na) == 2, "空总线未报未测"
    print("  SMOKE PASS（emit 幂等→validate→负断言跳号→norm→v1.1 sampled 断言→负断言空总线）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="lsbus_format_ops", description="总线格式运维")
    ap.add_argument("--smoke", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    e = sub.add_parser("emit"); e.add_argument("--bus", required=True); e.add_argument("--path", required=True)
    e.add_argument("--kind", default="artifact", choices=list(KINDS)); e.add_argument("--seat", default="a2a-node-local")
    e.add_argument("--refs", default=""); e.set_defaults(fn=cmd_emit)
    v = sub.add_parser("validate"); v.add_argument("busfile"); v.set_defaults(fn=cmd_validate)
    nn = sub.add_parser("norm"); nn.add_argument("busfile"); nn.add_argument("--apply", action="store_true"); nn.set_defaults(fn=cmd_norm)
    s = sub.add_parser("scan"); s.add_argument("--bus", required=True); s.set_defaults(fn=cmd_scan)
    a = ap.parse_args()
    if a.smoke:
        return cmd_smoke()
    if not getattr(a, "fn", None):
        ap.print_help()
        return 0
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
