# -*- coding: utf-8 -*-
"""sig_block.py v5 —— 「署名 + 唯一标识符」块生成器（**摘要口径全面改用 SHA3-512 树**）

承令条 2026-10-08 强化纪律，及机主指示「全面改用 SHA3-512 树，并面向未来实时更新」。

## ★v5 摘要口径（SHA3-512 树，可独立复算）
    正文 SHA3-512 树根 ＝ 对本文件字节中 `\\n<!-- SIG-BLOCK` **之前**的部分：
      ① norm：latin1 往返 + CRLF→LF（照仓内 merkle.cjs 口径）；
      ② 叶 ＝ SHA3-512( norm(正文字节) )（**单文件 ⇒ 叶即根**；多文件树见 verify_hub_merkle.py）；
      ③ 根 ＝ 归约至单节点（此处一叶 ⇒ 根＝叶）。
    复算：`root_of_1(norm(raw[:raw.find(b"\\n<!-- SIG-BLOCK")]))`

## v5 相对 v4 之变更（自纠留痕）
  1. **摘要算法**：sha256 → **SHA3-512 树根**（128-hex；标签改为「本件正文 SHA3-512 树根（署名块之前）」）；
  2. **★历史兼容**：旧件之 **sha256 块若复算相符 ⇒ 有效保留（幂等，不改写）**——承"只增不改"，
     历史证明链不因换算法而断裂；**新件与重写件一律 SHA3-512 树根**；
  3. 其余 v4 要点不变：占位块截断重写｜幂等须复算相符｜重写摘要取自截断后正文｜哨兵前单换行｜**写后自验**。

用法：
    python sig_block.py --file <件> [--note <用途>] [--append] [--dry]
性质：**不回显任何私钥/凭据**；只读公钥指纹与文件哈希。
"""
import argparse
import datetime as dt
import hashlib
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

SEAT_NAME = "A2A新席_石敢当Cairn"
SEAT_KEY = "a2a-node-local"
PUB = pathlib.Path(r"C:\Users\欧阳宏俊\.ssh\cairn-commit-signing.pub")
MANDATE = "全局声明 /loop-dual-pillar-ops（2026-10-08 扩写版，内含署名与唯一标识符强化条款）"
SENT = "<!-- SIG-BLOCK v1"
DIG_SHA3_RE = re.compile(r"本件正文 SHA3-512 树根（署名块之前）\*\* \| `([0-9a-f]{128})`")
DIG_SHA256_RE = re.compile(r"本件正文 sha256（署名块之前）\*\* \| `([0-9a-f]{64})`")


def norm(b: bytes) -> bytes:
    """照仓内 merkle.cjs 口径：latin1 往返 + CRLF→LF。"""
    return b.decode("latin1").replace("\r\n", "\n").encode("latin1")


def sha3_root_1(b: bytes) -> str:
    """单文件之 SHA3-512 树根（叶即根）。"""
    return hashlib.sha3_512(norm(b)).hexdigest()


def sha256_of(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pub_fp_short():
    try:
        if not PUB.exists():
            return "未提供"
        out = subprocess.run(["ssh-keygen", "-lf", str(PUB)], capture_output=True, text=True, timeout=60).stdout.strip()
        fp = out.split()[1] if out else ""
        return (fp[:15] + "…" + fp[-4:]) if (fp.startswith("SHA256:") and len(fp) > 20) else (fp or "未提供")
    except Exception:  # noqa: BLE001
        return "未提供"


def block(dig, ts, note):
    return [
        SENT + " seat=%s -->" % SEAT_KEY,
        "",
        "## 署名与唯一标识符（承令条：不以「本席」为唯一自称）",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 席位 | **%s** |" % SEAT_NAME,
        "| seat_key | `%s` |" % SEAT_KEY,
        "| 公钥指纹 | `%s`（ssh-ed25519；**私钥不出、不录**） |" % pub_fp_short(),
        "| **本件正文 SHA3-512 树根（署名块之前）** | `%s` |" % dig,
        "| 署名时点 | %s |" % ts,
        "| 令条锚 | %s |" % MANDATE,
        "| 用途 | %s |" % (note or "—"),
        "",
        "> **唯一标识符定义**：**(seat_key, 公钥指纹)** 二元组 ＋ **本件正文 SHA3-512 树根**；",
        "> 三者任一不同即**非同一署名**。**复算规则**：取本文件字节中 `\\n<!-- SIG-BLOCK` **之前**的部分，",
        "> 按 **SHA3-512 树**口径（norm：latin1 往返＋CRLF→LF；单文件叶即根）计根。",
        "",
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    p = pathlib.Path(a.file)
    if not p.exists():
        print("★ 件不存在：%s" % p)
        return 2
    raw = p.read_bytes()
    cur = raw.decode("utf-8", errors="replace")
    ts = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S +0800")
    has_sent = SENT in cur
    if a.append and has_sent:
        _idx = raw.find(SENT.encode("utf-8"))
        _body = raw[:_idx]
        if _body.endswith(b"\r\n"):
            _body = _body[:-2]
        elif _body.endswith(b"\n"):
            _body = _body[:-1]
        _m3 = DIG_SHA3_RE.search(cur)
        if _m3 and _m3.group(1) == sha3_root_1(_body):
            print("★ 该件 SHA3-512 树根署名块**有效且复算相符**（幂等：未重复追加）")
            return 0
        _m2 = DIG_SHA256_RE.search(cur)
        if _m2 and _m2.group(1) == sha256_of(_body):
            print("★ 历史件之 sha256 署名块**有效且复算相符 ⇒ 保留（只增不改）**；新件一律 SHA3-512 树根")
            return 0
        print("★ 该件署名块**无效或摘要不符** ⇒ 以 SHA3-512 树根重写"
              + ("（无摘要）" if not (_m3 or _m2) else ""))

    if has_sent:
        idx = raw.find(SENT.encode("utf-8"))
        body = raw[:idx]
        if body.endswith(b"\r\n"):
            body = body[:-2]
        elif body.endswith(b"\n"):
            body = body[:-1]
        dig = sha3_root_1(body)
        out = body + b"\n" + ("\n".join(block(dig, ts, a.note)) + "\n").encode("utf-8")
        mode = "重写（占位块/旧块→SHA3-512 树根块）"
    else:
        dig = sha3_root_1(raw)
        out = raw + b"\n" + ("\n".join(block(dig, ts, a.note)) + "\n").encode("utf-8")
        mode = "追加（SHA3-512 树根）"

    if a.dry:
        print("★ DRY ｜ 模式=%s ｜ 树根=%s…" % (mode, dig[:32]))
        return 0

    p.write_bytes(out)
    chk = p.read_bytes()
    pos = chk.find(b"\n" + SENT.encode("utf-8"))
    body = chk[:pos] if pos > 0 else chk
    ok = sha3_root_1(body) == dig
    print("★ %s → %s（%d B）｜ 树根=%s… ｜ **写后自验：%s**"
          % (mode, p.name, len(out), dig[:32], "逐位相符 ✅" if ok else "**不一致 ✗**"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
