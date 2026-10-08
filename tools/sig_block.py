# -*- coding: utf-8 -*-
"""sig_block.py v2 —— 「署名 + 唯一标识符」块生成器（承令条 2026-10-08 强化纪律）

令条原文要求（摘）：
    「所有修改必须**署名和唯一标识符**，不能仅仅以不可识别证伪、难以对抗性审查的『本席』为自称书写本文档」

## 摘要口径（**v2 收紧，可独立复算**）
    正文 sha256 ＝ 本文件字节中 **`\\n<!-- SIG-BLOCK` 之前**的部分之 sha256。
    ⇒ 复算：`sha256(raw[:raw.find(b"\\n<!-- SIG-BLOCK")])`

## v2 相对 v1 之修复（**自纠留痕**）
  1. **占位块**（哨兵在、**无摘要**）不得视为"已含块"而跳过 ⇒ **截断重写**；
  2. 幂等判据**须要求 64 位摘要**（仅凭标签文字会被占位块欺骗）；
  3. **★ 重写路径之摘要须取自"截断后的正文"**（v1 误取**含旧块**之内容 ⇒ 复算必然不一致）；
  4. 新块以**哨兵为首行**（前置单个 `\\n`），使"哨兵前字节"恰等于所签正文；
  5. **写后自验**：写毕即复算，与前记摘要比对（**不一致即报错退出**）。

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
DIG_RE = re.compile(r"本件正文 sha256（署名块之前）\*\* \| `([0-9a-f]{64})`")


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
        "| **本件正文 sha256（署名块之前）** | `%s` |" % dig,
        "| 署名时点 | %s |" % ts,
        "| 令条锚 | %s |" % MANDATE,
        "| 用途 | %s |" % (note or "—"),
        "",
        "> **唯一标识符定义**：**(seat_key, 公钥指纹)** 二元组 ＋ **本件正文 sha256**；",
        "> 三者任一不同即**非同一署名**。**复算规则**：取本文件字节中 `\\n<!-- SIG-BLOCK` **之前**的部分计 sha256。",
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
    # ★v3：「存在摘要」≠「摘要正确」⇒ 须**复算相符**方视为有效（承"报告值≠核实值"）
    if a.append and has_sent:
        _idx = raw.find(SENT.encode("utf-8"))
        _body = raw[:_idx]
        if _body.endswith(b"\r\n"):
            _body = _body[:-2]
        elif _body.endswith(b"\n"):
            _body = _body[:-1]
        _m = DIG_RE.search(cur)
        if _m and _m.group(1) == hashlib.sha256(_body).hexdigest():
            print("★ 该件署名块**有效且复算相符**（幂等：未重复追加）")
            return 0
        print("★ 该件署名块**无效或摘要不符** ⇒ 重写" + ("（无摘要）" if not _m else "（摘要=%s…）" % _m.group(1)[:16]))

    if has_sent:
        idx = raw.find(SENT.encode("utf-8"))
        body = raw[:idx]
        # ★v4：复算切片**不含紧邻哨兵的那个换行** ⇒ 正文须**恰去一个**尾部换行（口径统一）
        if body.endswith(b"\r\n"):
            body = body[:-2]
        elif body.endswith(b"\n"):
            body = body[:-1]
        dig = hashlib.sha256(body).hexdigest()
        out = body + b"\n" + ("\n".join(block(dig, ts, a.note)) + "\n").encode("utf-8")
        mode = "重写（占位块/旧块→有效块）"
    else:
        dig = hashlib.sha256(raw).hexdigest()
        out = raw + b"\n" + ("\n".join(block(dig, ts, a.note)) + "\n").encode("utf-8")
        mode = "追加"

    if a.dry:
        print("★ DRY ｜ 模式=%s ｜ 正文摘要=%s…" % (mode, dig[:24]))
        return 0

    p.write_bytes(out)
    chk = p.read_bytes()
    pos = chk.find(b"\n" + SENT.encode("utf-8"))
    body = chk[:pos] if pos > 0 else chk
    ok = hashlib.sha256(body).hexdigest() == dig
    print("★ %s → %s（%d B）｜ 正文摘要=%s… ｜ **写后自验：%s**"
          % (mode, p.name, len(out), dig[:24], "逐位相符 ✅" if ok else "**不一致 ✗**"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
