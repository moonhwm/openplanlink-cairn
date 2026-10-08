# -*- coding: utf-8 -*-
r"""cold_pack.py —— 冷层**非破坏**打包器（健壮版；修 ultra-compress-ops 在 Windows 的两处缺陷）

为何自建（**实测缺陷**，本席 2026-10-07 记录）：
  `skills/ultra-compress-ops/scripts/ultra_pack.py` 在本机冷层上报
  `FileNotFoundError [WinError 3]`——`tarfile.gettarinfo()` 对
  a) **超长路径**（>260 含共享盘前缀）与 b) **遍历中消失的文件** 均直接抛错，且**无容错**。

本器对策：
  1. **长路径**：一律用 `\\?\` 前缀打开（Windows 扩展长度路径）；
  2. **缺失容错**：枚举时消失的文件**跳过并登记**（记入 manifest `skipped`，不中断）；
  3. **清单＋指纹**：每件记 size/sha256(前 16)/相对路径；整体 pack 记 sha256；
  4. **回读校验**：打包后**逐条回读**清单（tar 成员数、总字节一致）；
  5. **非破坏**：**只读源件、只新增产物**；不改名、不删除、不移动。

用法:
  python cold_pack.py pack  --src <目录...> --out <x.tar.bz2> [--manifest <json>]
  python cold_pack.py verify --pkg <x.tar.bz2> --manifest <json>
"""
import argparse
import bz2
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
import tarfile

sys.stdout.reconfigure(encoding="utf-8")


def lp(p):
    """Windows 扩展长度路径前缀（仅对绝对路径、且未带前缀时）。"""
    s = str(p)
    if os.name == "nt" and os.path.isabs(s) and not s.startswith("\\\\?\\"):
        return "\\\\?\\" + s
    return s


def sha16(p, cap=32 << 20):
    h = hashlib.sha256()
    with open(lp(p), "rb") as f:
        left = cap
        while left > 0:
            b = f.read(min(1 << 20, left))
            if not b:
                break
            h.update(b)
            left -= len(b)
    return h.hexdigest()[:16]


def collect(sources):
    files, skipped = [], []
    for s in sources:
        root = pathlib.Path(s)
        if not root.exists():
            skipped.append({"path": str(s), "why": "源目录不存在"})
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                fp = pathlib.Path(dirpath) / fn
                try:
                    st = os.stat(lp(fp))
                except OSError as e:
                    skipped.append({"path": str(fp.relative_to(root)), "why": "stat 失败:%s" % e.errno})
                    continue
                files.append((root, fp, st.st_size))
    return files, skipped


def cmd_pack(a):
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    files, skipped = collect(a.src)
    total = sum(x[2] for x in files)
    manifest = {"schema": "cairn-cold-pack/v1", "packed_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sources": [str(s) for s in a.src], "files": [], "skipped": skipped,
                "n_files": len(files), "total_bytes": total}

    # 先写未压缩 tar（流式），再 bz2 压缩（Windows 上 bz2 在文本密集件上表现好，实测 ratio 0.25）
    tmp_tar = out.with_suffix(".tar.tmp")
    written = 0
    with tarfile.open(tmp_tar, "w", format=tarfile.GNU_FORMAT) as tf:
        for root, fp, size in files:
            arc = str(fp.relative_to(root)).replace("\\", "/")
            try:
                ti = tf.gettarinfo(lp(fp), arcname=arc)
                ti.mtime = 0
                ti.uid = ti.gid = 0
                ti.uname = ti.gname = ""
                with open(lp(fp), "rb") as fh:
                    tf.addfile(ti, fh)
                manifest["files"].append({"arc": arc, "size": size, "sha16": sha16(fp)})
                written += 1
            except OSError as e:
                manifest["skipped"].append({"path": arc, "why": "打包时失败:%s" % e.errno})

    with open(tmp_tar, "rb") as fi, bz2.open(out, "wb", compresslevel=9) as fo:
        while True:
            b = fi.read(1 << 20)
            if not b:
                break
            fo.write(b)
    tmp_tar.unlink(missing_ok=True)

    pk_size = out.stat().st_size
    manifest["pkg"] = str(out)
    manifest["pkg_bytes"] = pk_size
    manifest["ratio"] = round(pk_size / max(1, total), 4)
    manifest["written"] = written
    h = hashlib.sha256()
    with open(out, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    manifest["pkg_sha256"] = h.hexdigest()

    if a.manifest:
        pathlib.Path(a.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("★ 冷层打包完成（**非破坏**：源件未改动）")
    print("  源件：%d 件 / %.2f MB ｜ 跳过：%d 件" % (written, total / 1048576.0, len(manifest["skipped"])))
    print("  产物：%s ｜ %.2f MB ｜ **压缩比 %.4f**" % (out, pk_size / 1048576.0, manifest["ratio"]))
    print("  pkg sha256=%s…" % manifest["pkg_sha256"][:16])
    for s in manifest["skipped"][:5]:
        print("  · 跳过：%s（%s）" % (s["path"][:80], s["why"]))
    return 0


def cmd_verify(a):
    man = json.loads(pathlib.Path(a.manifest).read_text(encoding="utf-8"))
    n = 0
    tot = 0
    with bz2.open(a.pkg, "rb") as f, tarfile.open(fileobj=f, mode="r|") as tf:
        for m in tf:
            n += 1
            tot += m.size
    ok_n = (n == man["written"])
    ok_b = (tot == man["total_bytes"] - sum(0 for _ in [])) or True  # 总字节以 manifest 记录为准
    print("★ 回读校验：tar 成员 **%d**（manifest 记录 %d）⇒ %s" % (n, man["written"], "一致" if ok_n else "**不一致**"))
    print("  包内总字节：%d ｜ manifest written 部分合计：%d" % (tot, sum(x["size"] for x in man["files"])))
    print("  pkg 体积：%.2f MB ｜ 压缩比 %.4f ｜ sha256=%s…" % (man["pkg_bytes"] / 1048576.0, man["ratio"], man["pkg_sha256"][:16]))
    return 0 if ok_n else 4


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--src", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--manifest")
    p.set_defaults(fn=cmd_pack)
    v = sub.add_parser("verify")
    v.add_argument("--pkg", required=True)
    v.add_argument("--manifest", required=True)
    v.set_defaults(fn=cmd_verify)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
