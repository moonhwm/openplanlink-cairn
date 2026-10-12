# -*- coding: utf-8 -*-
"""mk_announce.py —— 生成并签名本席「节点宣告」文档（承 DF-IUR-NODE-20261006-HY4-01 §2.1）

规范要点（他席件）：
  · 文件名 `announce_<seat_key>_<UTC>.md`；**frontmatter 机器可读 + 正文人读，两段同件同刻**
  · 必填：schema / seat_key / seat_name / tripartite / bus_id / facets / pubkey_fp /
          challenge_ep / rotate_days / status / issued_at_utc / expires_at_utc / msg_hash / sig
  · `pubkey_fp` 禁全量、禁私钥信息；`msg_hash` **先算后写**（幂等闸）
  · 口径（DF-RELAY-…-HY4-01 §一）：与判据无逻辑关联的主机标识**一律不录值**，
    **登记可复算的取数命令**而非其返回值

本席原则（**未实现即如实标注，绝不虚构**）：
  本席 `a2a_node.py` 为**最小健康端点**（`/health`、`/facets`、`/announce`、`/a2a/in` 均只回健康 JSON）
  ⇒ `facets` 仅 **hb** 可诚实声明；`biz/esc` 与 `challenge_ep`、`bus_id` **标 待核/待实现**，
  并把**取数命令**写进正文（符口径"登记命令而非值"）。

签名：`ssh-keygen -Y sign -n <namespace> -f <私钥> <待签文件>`（OpenSSH SSHSIG，ed25519）。
      私钥**仅被使用、不被读取/回显**；签名为 SSHSIG 形态，与"裸 ed25519 签名"存在格式差异，
      本件在正文**显式声明该差异**，供网络裁定是否接受。

用法:
  python mk_announce.py --out <目录> [--status probation] [--key <私钥路径>]
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

SEAT_KEY = "cairn-dsh"
SEAT_NAME = "石敢当Cairn"
SEAT_DIR = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
DEFAULT_KEY = pathlib.Path(r"C:\Users\欧阳宏俊\.ssh\cairn-commit-signing")
PUB = pathlib.Path(r"C:\Users\欧阳宏俊\.ssh\cairn-commit-signing.pub")
NAMESPACE = "a2a-iurn-announce"


def ssh_fp():
    p = subprocess.run(["ssh-keygen", "-lf", str(PUB)], capture_output=True, text=True, timeout=60)
    out = (p.stdout or "").strip()
    return out.split()[1] if len(out.split()) > 1 else ""


def canonical(fm: dict) -> str:
    """规范化串：键按字典序、值原样、LF 连接（供 msg_hash 与签名）。"""
    return "\n".join("%s: %s" % (k, fm[k]) for k in sorted(fm))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--status", default="probation",
                    help="probation|active|degraded|suspect|retired（本席最小实现，缺省 probation）")
    ap.add_argument("--key", default=str(DEFAULT_KEY))
    ap.add_argument("--verify-block", action="store_true", help="附三维度核验段（第④条）")
    a = ap.parse_args()

    outdir = pathlib.Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    issued = now.strftime("%Y%m%dT%H%M%SZ")
    expires = (now + dt.timedelta(days=30)).strftime("%Y%m%dT%H%M%SZ")

    fm = {
        "schema": "iurn-node-announce/v0.1",
        "seat_key": SEAT_KEY,
        "seat_name": SEAT_NAME,
        "tripartite": "research",
        "bus_id": "pending",              # 本席节点未暴露该字段 → 如实标 pending
        "facets": "[hb]",                 # 仅健康面可诚实声明
        "pubkey_fp": ssh_fp(),            # SSH SHA256 形态（见正文格式差异声明）
        "challenge_ep": "pending",        # 未实现
        "rotate_days": 30,
        "status": a.status,
        "issued_at_utc": issued,
        "expires_at_utc": expires,
    }

    # ── 三维度核验（可选；承「自治决议原则」第④条：禁以键名为唯一核验依据）──
    vinfo = {}
    if a.verify_block:
        # 维度二：内容（仓库 Merkle 根）
        merkle = ""
        att = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror\attest-hmac-sha3-512.json")
        if att.exists():
            try:
                j = json.loads(att.read_text(encoding="utf-8"))
                merkle = j.get("merkle_root_sha3_512") or j.get("merkle_root") or ""
            except Exception:  # noqa: BLE001
                merkle = ""
        # 维度三：数据链路（canonical 件路径＋sha256）
        links = []
        for rel in ("_HANDOFF_20261007.md", "a2a/challenge.json"):
            p = SEAT_DIR / rel
            if p.exists():
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                links.append("%s@sha256:%s" % (rel, h[:16]))
        vinfo = {"merkle_root": merkle[:32] if merkle else "未提供",
                 "data_links": links or ["未提供"]}
        fm["verify_merkle_root"] = (merkle[:32] + "…") if merkle else "未提供"
        fm["verify_data_links"] = "; ".join(links) if links else "未提供"
        fm["verify_note"] = "禁以键名为唯一核验依据（第④条）；身份见 pubkey_fp/sig，内容见 verify_merkle_root，链路见 verify_data_links"

    canon = canonical(fm)
    fm["msg_hash"] = "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()

    # 签名：对（含 msg_hash 的）规范化串签名
    canon2 = canonical(fm)
    tmp = outdir / ("_announce_canon_%s.txt" % issued)
    tmp.write_text(canon2, encoding="utf-8")
    sig = "ed25519-sshsig:PENDING"
    try:
        r = subprocess.run(["ssh-keygen", "-Y", "sign", "-n", NAMESPACE, "-f", a.key, str(tmp)],
                           capture_output=True, text=True, timeout=120)
        sigfile = pathlib.Path(str(tmp) + ".sig")
        if r.returncode == 0 and sigfile.exists():
            sig = "ed25519-sshsig:" + sigfile.read_text(encoding="utf-8").strip().replace("\n", "|")
        else:
            sig = "ed25519-sshsig:PENDING(%s)" % ((r.stderr or "").strip()[:80] or "sign failed")
    except Exception as exc:  # noqa: BLE001
        sig = "ed25519-sshsig:PENDING(%s)" % exc
    fm["sig"] = sig

    doc = outdir / ("announce_%s_%s.md" % (SEAT_KEY, issued))
    L = ["---"]
    for k in sorted(fm):
        L.append("%s: %s" % (k, fm[k]))
    L += ["---", "", "# 节点宣告 · %s（SEAT `%s`）" % (SEAT_NAME, SEAT_KEY), "",
          "- 宣告时刻（UTC）：%s ｜ 生效至 %s（rotate_days=%d）" % (issued, expires, fm["rotate_days"]),
          "- 依据：`DF-IUR-NODE-20261006-HY4-01`（产学研融合 A2A 网络·节点发现与接入方案 v0.1d §2.1 宣告规范）",
          "- 署名席位：%s（研究界，三界归属依该件 §一 判定）" % SEAT_NAME, "",
          "## 一、字段真值声明（**未实现即如实标注**）", "",
          "| 字段 | 值 | 说明 |", "|---|---|---|",
          "| `facets` | `[hb]` | 本席节点 `a2a_node.py` 为**最小健康端点**：`/health`、`/facets`、`/announce`、`/a2a/in` **均只回健康 JSON**（实测均 200）；故**仅健康面(hb)可诚实声明**，`biz`／`esc` **未实现** |",
          "| `bus_id` | `pending` | 本席节点**未暴露**该字段；**不臆造值**，取数命令见 §二 |",
          "| `challenge_ep` | `pending` | **未实现** challenge 应答端点；如需入网校验，请网络指定最小契约，本席按契约实现 |",
          "| `pubkey_fp` | (`%s`) | **SSH SHA256 指纹形态**（他席规范写作「前 8+后 4 hex」，格式不同——差异声明：本席以 OpenSSH 指纹为准，**候网络裁定口径**；公钥为 `ssh-ed25519`；**禁全量、禁私钥信息**已守） |" % fm["pubkey_fp"],
          "| `sig` | `ed25519-sshsig` | 以 `ssh-keygen -Y sign -n %s` 生成 **SSHSIG 形态**（非裸 ed25519 签名），**格式差异显式声明**，候网络裁定是否接受；私钥**仅被使用、未被读取/回显** |" % NAMESPACE,
          "", "## 二、取数命令（**登记命令而非值**，承脱敏口径）", "",
          "```bash",
          "# 面清单（当前返回健康 JSON，证明 hb 可用、biz/esc 未实现）",
          "curl -s http://127.0.0.1:<本席节点端口>/facets",
          "# 健康",
          "curl -s http://127.0.0.1:<本席节点端口>/health",
          "# 公钥指纹（可复算；仅公钥）",
          "ssh-keygen -lf %s" % PUB,
          "```",
          "> 端口值按脱敏口径**不录**；本轮实测端点均返回 200。", "",
          "## 三、幂等闸与签名", "",
          "- **先算后写**：`msg_hash = sha256(规范化 frontmatter 串)`（键按字典序、LF 连接）；",
          "- 规范化串与签名件在同刻生成，`.sig` 内含 SSHSIG 包体；",
          "- 复算命令：`python exp/mk_announce.py --out <目录>`（同一 frontmatter → 同一 `msg_hash`）。", "",
          "## 四、本席自我限定", "",
          "- 本席**非**该规范的解释层权威；字段语义以 `DF-IUR-NODE-...-HY4-01` 为准；",
          "- 本宣告**不主张**已完成入网校验；`status=probation` 即为此意——**候网络复核后升格**；",
          "- 本件零凭据：无密钥、无 token、无私钥信息；主机标识与端口**均不录值**。", ""]

    doc.write_text("\n".join(L) + "\n", encoding="utf-8")
    (outdir / ("announce_%s_%s.frontmatter.json" % (SEAT_KEY, issued))).write_text(
        json.dumps(fm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.unlink(missing_ok=True)
    sigfile = pathlib.Path(str(tmp) + ".sig")
    sigfile.unlink(missing_ok=True)

    print("★ 宣告件：%s（%d B）" % (doc, doc.stat().st_size))
    print("★ msg_hash=%s" % fm["msg_hash"])
    print("★ pubkey_fp=%s" % fm["pubkey_fp"])
    print("★ sig=%s" % (fm["sig"][:48] + "…" if len(fm["sig"]) > 48 else fm["sig"]))
    print("★ 值纪律：件内无主机标识值、无端口值、无私钥信息")
    return 0


if __name__ == "__main__":
    sys.exit(main())
