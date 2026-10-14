# -*- coding: utf-8 -*-
"""otl_chunk_write.py —— 分块写（承 led_1550／1552 之真限）（2026-10-14 立）

缘起：器物 `otl_batch.py` 把**整篇正文经命令行**传给 `kdocs-cli` ⇒ 超 Windows 命令行上限
      （约 32 KB）即失败且**近乎静默**（`create` 成而 `insert` 败 ⇒ 留**空件**）。
处置：本器**按块分批**写 —— 首批 `mode=replace`，后续 `mode=append`，**每批 ≤ 28 KB**；
      **每批必回读**（★"件已建 ≠ 内容已入"，承口径第十八章第 1 条）。

★另承 led_1552「id 名之辨」：建件返回 `file_id`（44 字符）；清单返回 `id`（33 字符）／`link_id`（12）
      ⇒ **本器一律以清单之 `id`（≥32 字符）为准**，并按名复用（幂等）。

用法：
    python otl_chunk_write.py <源 .md 之文件名>        # 在 outbox/mem 下按名取
    python otl_chunk_write.py <源文件名> --dry        # 只示分块计划
"""
import json, pathlib, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
CLI = HOME / ".kimi-work" / "bin" / "kdocs-cli.exe"
SEAT = (HOME / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
CHUNK = 28000          # ★每批字节上限（留余量于 32 KB 命令行上限之下）
BOX = re.compile(r"[│├└─┌┐┘┬┴┼╔╗╚╝║═]")


def call(svc, cmd, args, t=240):
    r = subprocess.run([str(CLI), svc, cmd, "--args", json.dumps(args, ensure_ascii=False)],
                       capture_output=True, text=True, encoding="utf-8", timeout=t)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_raw": (r.stdout or "")[:200], "_err": (r.stderr or "")[:200]}


def to_commonmark(t: str) -> str:
    out, buf = [], []
    def flush():
        if buf:
            out.append("```"); out.extend(buf); out.append("```"); buf.clear()
    for ln in t.splitlines():
        if BOX.search(ln):
            buf.append(ln)
        else:
            flush(); out.append(ln)
    flush()
    return "\n".join(out)


def split_chunks(md: str, limit: int = CHUNK):
    """★按段（空行分隔）聚合，保每批 ≤ limit 字节；单段超限则按行硬切。"""
    paras, cur = [], []
    for block in md.split("\n\n"):
        b = block.encode("utf-8")
        if len(b) > limit:
            if cur:
                paras.append("\n\n".join(cur)); cur = []
            lines, buf = block.split("\n"), []
            for ln in lines:
                if len("\n".join(buf + [ln]).encode("utf-8")) > limit and buf:
                    paras.append("\n".join(buf)); buf = []
                buf.append(ln)
            if buf:
                paras.append("\n".join(buf))
            continue
        if len(("\n\n".join(cur + [block])).encode("utf-8")) > limit and cur:
            paras.append("\n\n".join(cur)); cur = []
        cur.append(block)
    if cur:
        paras.append("\n\n".join(cur))
    return paras


def lookup_existing(title: str):
    j = call("drive", "list-my-files", {"page_size": 300, "filter_type": "file"})
    for it in (((j.get("data") or {}).get("items")) or []):
        nm = str(it.get("name") or "")
        if nm.replace(".otl", "") == title:
            for k in ("id", "file_id"):
                v = it.get(k)
                if isinstance(v, str) and len(v) >= 32:
                    return v
    return None


def readback(fid: str):
    j = call("drive", "read-file", {"file_id": fid, "format": "markdown"})
    d = j.get("data") or {}
    t = next((d[k] for k in ("content", "text", "markdown", "body") if isinstance(d.get(k), str)), "")
    return j.get("code"), len(t)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python otl_chunk_write.py <源 .md 文件名> [--dry]"); return 1
    src_name = sys.argv[1]
    dry = "--dry" in sys.argv
    p = SEAT / "outbox" / "mem" / src_name
    if not p.exists():
        print("   ★源不在：%s" % src_name); return 2
    md = to_commonmark(p.read_text(encoding="utf-8", errors="replace"))
    chunks = split_chunks(md)
    total = len(md.encode("utf-8"))
    title = re.sub(r"\.md$", "", src_name)[:48]
    print("   源 %.1f KB ⇒ 分 %d 批（每批 ≤ %.1f KB）｜ 件名 %s" % (
        total / 1024, len(chunks), CHUNK / 1024, title))
    for i, c in enumerate(chunks, 1):
        print("     批 %2d：%7.1f KB" % (i, len(c.encode('utf-8')) / 1024))
    if dry:
        print("   · dry：不动云端"); return 0

    fid = lookup_existing(title)
    if fid:
        print("   ★已存在同名件 ⇒ 复用（不新建）：%s" % fid)
    else:
        j1 = call("drive", "create-empty-file", {"name": title, "file_extension": "otl"})
        fid = lookup_existing(title)
        print("   建件 code=%s ⇒ 复用查得 id=%s" % (j1.get("code"), str(fid)[:36]))
        if not fid:
            print("   ★建件后仍取不到 id（★列名报告，不吞）⇒ 中止"); return 3

    ok = 0
    log = []
    for i, c in enumerate(chunks, 1):
        mode = "replace" if i == 1 else "append"
        j = call("otl", "insert-content", {"file_id": fid, "title": title, "content": c,
                                          "format": "markdown", "mode": mode})
        time.sleep(1.5)
        code, n = readback(fid)
        ver = None
        try:
            ver = j["data"]["detail"]["result"]["version"]
        except Exception:
            pass
        good = (j.get("code") == 0 and code == 0 and n > 0)
        ok += 1 if good else 0
        print("     批 %2d（%s）写=%s 回读=%s %6d 字 version=%s ⇒ %s" % (
            i, mode, j.get("code"), code, n, ver, "✓" if good else "✗"))
        log.append({"batch": i, "mode": mode, "write": j.get("code"), "readback_code": code,
                    "readback_chars": n, "version": ver, "ok": good})
    out = SEAT / "outbox" / "wps_read" / ("OTL分块写_%s.json" % time.strftime("%Y%m%d_%H%M"))
    out.write_text(json.dumps({"src": src_name, "title": title, "file_id": fid,
                               "chunks": len(chunks), "bytes": total, "log": log,
                               "summary": {"ok": ok, "total": len(chunks)}},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("   ★汇总：%d/%d 批通过 ｜ 台账 %s" % (ok, len(chunks), out.name))
    return 0 if ok == len(chunks) else 4


if __name__ == "__main__":
    sys.exit(main())
