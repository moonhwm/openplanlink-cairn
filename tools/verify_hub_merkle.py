#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
verify_hub_merkle.py —— 对 qoder-skills-hub 做【100% 叶核验】＋ root 复算。 v1.0.0

来由
────
上一轮本席只做了 **0.13%（4/2995）抽样**叶核验，并**明确声明那不是全量**。
本轮依 L1136（『下载更新自动运维相关技能』）**整包取回（33.8 MB）**，故可把覆盖推到 **100%**。
★ 本席一以贯之的规矩：**覆盖率必须说清；抽样通过不等于全库通过。**

它照抄对端公布的口径（tools/merkle.cjs）
────────────────────────────────────────
· 叶   = SHA3-512( 文件内容经 CRLF→LF 归一 后的字节 )
· 叶序 = 按路径排序
· 奇数 = 复制末节点（非上提）
· 节点 = SHA3-512( 左字节 ‖ 右字节 )
· root = 归约至单一节点

用法：verify_hub_merkle.py <tarball> <MERKLE.json>
退出码：0 = 全库相符；1 = 存在不符/缺件/多余。
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys
import tarfile
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def safe_extract(tar: tarfile.TarFile, dest: pathlib.Path):
    dest = dest.resolve()
    bad, members = [], []
    for m in tar.getmembers():
        if m.issym() or m.islnk():
            bad.append((m.name, "链接")); continue
        p = (dest / m.name).resolve()
        if not str(p).startswith(str(dest)) or m.name.startswith("/") or ".." in pathlib.PurePosixPath(m.name).parts:
            bad.append((m.name, "越界")); continue
        members.append(m)
    tar.extractall(dest, members=members, filter="data")
    return bad, len(members)


def norm(b: bytes) -> bytes:
    """照 merkle.cjs 的 norm()：latin1 往返 + CRLF→LF。"""
    s = b.decode("latin1")
    return s.replace("\r\n", "\n").encode("latin1")


def sha3(b: bytes) -> bytes:
    return hashlib.sha3_512(b).digest()


def root_of(hexes: list) -> str:
    L = [bytes.fromhex(x) for x in hexes]
    while len(L) > 1:
        n = []
        for i in range(0, len(L), 2):
            r = L[i + 1] if (i + 1) < len(L) else L[i]
            n.append(sha3(L[i] + r))
        L = n
    return L[0].hex() if L else sha3(b"").hex()


def main():
    tar_p, mfj = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    m = json.loads(mfj.read_text(encoding="utf-8"))
    files = m["files"]
    print("═══ qoder-skills-hub · 100%% 叶核验 ═══")
    print("清单 generatedAt=%s ｜ fileCount=%d ｜ files=%d" % (m["generatedAt"], m["fileCount"], len(files)))

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hubverify_"))
    try:
        with tarfile.open(tar_p, "r:gz") as tar:
            bad, n = safe_extract(tar, tmp)
        print("安全解包：%d 成员 ｜ 拒收 %d（%s）" % (n, len(bad), "、".join({w for _, w in bad}) or "无"))
        roots = [p for p in tmp.iterdir() if p.is_dir()]
        root_dir = roots[0] if roots else tmp

        ok, mism, missing = 0, [], []
        for rel, want in files.items():
            p = root_dir / rel
            if not p.is_file():
                missing.append(rel); continue
            got = sha3(norm(p.read_bytes())).hex()
            if got == want:
                ok += 1
            else:
                mism.append((rel, want, got))

        # 仓库有、清单无（多余件）
        in_repo = {p.relative_to(root_dir).as_posix() for p in root_dir.rglob("*") if p.is_file()}
        extra = sorted(in_repo - set(files) - {"MERKLE.json"})

        hexes = [files[k] for k in sorted(files.keys())]
        r = root_of(hexes)

        print("\n① 叶核验：相符 %d ｜ 不符 %d ｜ 缺件 %d ／ 声明 %d"
              % (ok, len(mism), len(missing), len(files)))
        print("   ★叶核验覆盖率 = %.2f%%（本机全量）" % (100.0 * ok / max(len(files), 1)))
        for rel, want, got in mism[:20]:
            print("   ★[不符] %s\n       清单 %s…\n       实算 %s…" % (rel, want[:24], got[:24]))
        for rel in missing[:20]:
            print("   ★[缺件] %s" % rel)
        print("\n② root 复算：%s" % ("★相符" if r == m["root"] else "★不符"))
        print("   声明 %s…" % m["root"][:40])
        print("   复算 %s…" % r[:40])
        print("\n③ 仓库有、清单无（MERKLE.json 自身除外）：%d 件" % len(extra))
        for x in extra[:20]:
            print("   %s" % x)

        bad_n = len(mism) + len(missing) + len(extra) + (0 if r == m["root"] else 1)
        print("\n═══ 结论：%s ═══" % ("PASS —— 全库叶哈希与 root 皆相符，且无多余件" if bad_n == 0 else "FAIL（异常 %d）" % bad_n))
        return 0 if bad_n == 0 else 1
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
