# -*- coding: utf-8 -*-
"""disclosure_scan.py —— 披露前扫描闸（网络标识 + 凭据形态；**不回显值**）

缘起（本席轮13 实测）：
  · 他席口径 `DF-IUR-NODE-20261006-HY4-03`：网络标识类值一律**最小披露**（不录值，只记命中与否）；
  · 本席自陈两类披露错误——**漏扫**（他席："初改后仍命中 1 处"）与**复述**（本席：登记问题时把值当例子写进正文）；
  ⇒ 统一对策：**提交/推送前做一次全档复扫**，并把该动作**工具化**。

🔴 工具自带纪律（源于"复述即再披露"）：
  1. **绝不打印命中值本身**——只打印**类别**＋**掩码**（前 2 字符 + `***`）＋位置；
  2. 报告本身可入库（不含值）；如须复核原值，**只在本机终端即时查看**，不入件。

用法:
  python disclosure_scan.py                       # 扫全仓（git grep 语义）
  python disclosure_scan.py --staged             # 只扫暂存区（提交前闸）
  python disclosure_scan.py --paths <目录...>     # 扫指定路径（工作树）
  python disclosure_scan.py --mine-only          # 仅扫 deliverables/<本席>
  python disclosure_scan.py --net-only           # 只查网络标识（默认两者都查）
  python disclosure_scan.py --report-only        # 只报告不设退出码
退出码：发现命中 1；干净 0。
"""
import argparse
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror")

# 网络标识（类别名 → 正则）
NET_PATTERNS = [
    ("网卡物理地址", re.compile(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}")),
    ("回环地址端口", re.compile(r"127\.0\.0\.1[:：]\d{2,5}")),
    ("私网地址(192.168)", re.compile(r"192\.168\.\d{1,3}\.\d{1,3}")),
    ("私网地址(10.)", re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
    ("私网地址(172.16-31)", re.compile(r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b")),
    ("任意 IPv4:端口", re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}[:：]\d{2,5}\b")),
    # ↓ 承 DF-RELAY-20261006-HY4-01 §一 扩展口径：主机名与磁盘卷序列号同列"不录值"
    ("主机名(本机前缀)", re.compile(r"(?i)\bLAPTOP-[A-Z0-9]{4,}\b")),
    ("主机名(通用模式)", re.compile(r"\b(?:DESKTOP|SERVER|WIN|PC)-[A-Z0-9]{4,}\b")),
    ("磁盘卷序列号(带语境)", re.compile(r"(?i)(?:卷序列号|volume\s*serial[^\n:：]{0,12})[:：]?\s*([0-9A-F]{4}-[0-9A-F]{4})\b")),
    # ↓ 轮19 新增、轮20 精化：裸「名:端口」形态（如 relay:<端口值不录>）——同属口径所指"高位端口"。
    #   轮19 首版无排除 → 全仓 364 命中，抽样实证 16/16 为 CSS 属性（font-weight:/width:/height:）。
    #   轮20 加 **CSS 属性负向前瞻**（并同步排除常见 CSS 值单位形态），使其由"噪声筛"变为"可用筛"。
    ("裸名称:端口", re.compile(
        r"\b(?!font-weight|font-size|font-family|line-height|letter-spacing|min-width|max-width"
        r"|min-height|max-height|border-radius|border-width|z-index|text-align|background-color"
        r"|width|height|margin|padding|border|top|left|right|bottom|gap|flex|grid|color|opacity"
        r"|transition|transform|scale|rotate|delay|duration|content|order|columns|rows)\b"
        r"[a-zA-Z][a-zA-Z0-9_\-]{2,}[:：][1-9]\d{3,4}\b", re.I)),
]
# 凭据形态（只查形态，不回显）
CRED_PATTERNS = [
    ("密钥前缀(sk-/ghp_/AKIA)", re.compile(r"\b(?:sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,})")),
    ("私钥头", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("赋值式凭据", re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password|passwd)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}")),
    ("Bearer 令牌", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}")),
    # ↓ 轮46 新增：承他席 EVT-P0-20261007-01（CAS 内 Supabase 活凭据随分片出网；其闸门 37 条规则不覆盖下列形态）
    #   本席闸门原有**同一盲区**（仅 sk-/ghp_/AKIA）⇒ 补齐 Supabase 与 JWT 两类形态
    ("Supabase anon 族(设计上可公开)", re.compile(r"\bsb_publishable_[A-Za-z0-9_\-]{8,}")),  # 承他席 -CORR：等价 anon、可公开内联；**定级看 RLS，不按泄露计**
    ("Supabase service/secret 族(真敏感)", re.compile(r"\bsb_secret_[A-Za-z0-9_\-]{8,}")),  # 仅此族为真敏感
    ("Supabase 项目主机(标识非密)", re.compile(r"\b[a-z0-9]{16,}\.supabase\.co\b")),  # 标识；与 anon key 同现属前端常态
    ("supabase.co 字面", re.compile(r"\bsupabase\.co\b")),
    ("JWT 形态(eyJ…)", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{6,}")),
    # ↓ 轮51 自课：**族前缀重述**亦属复述（承"复述即再披露"）——提示改锚点互引，而非判为泄露
    ("族前缀重述(宜改锚点互引)", re.compile(r"\b(?:sk-ws-|sb_publishable_|sb_secret_|ghp_|AKIA)")),
]
TEXT_EXT = {".md", ".otl", ".txt", ".json", ".jsonl", ".py", ".mjs", ".js", ".yml", ".yaml",
            ".sh", ".ps1", ".led", ".csv", ".ini", ".cfg", ".toml", ".html"}


def mask(v: str) -> str:
    v = v.strip()
    return (v[:2] + "***") if len(v) > 2 else "***"


def git(args, binary=False, timeout=300):
    p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, timeout=timeout)
    return (p.stdout if binary else p.stdout.decode("utf-8", "replace")), p.returncode


def scan_text(text: str, label: str, findings: list, nets: bool, creds: bool):
    for i, line in enumerate(text.splitlines(), 1):
        for cat, rx in (NET_PATTERNS if nets else []):
            for m in rx.finditer(line):
                findings.append((label, i, "网络标识", cat, mask(m.group(0))))
        for cat, rx in (CRED_PATTERNS if creds else []):
            for m in rx.finditer(line):
                findings.append((label, i, "凭据形态", cat, mask(m.group(0))))


def scan_repo(nets: bool, creds: bool):
    files, _ = git(["ls-files"])
    findings = []
    for f in files.split("\n"):
        if not f.strip() or f == "attest-hmac-sha3-512.json":
            continue
        if pathlib.Path(f).suffix.lower() not in TEXT_EXT:
            continue
        blob, code = git(["show", "HEAD:%s" % f], binary=True)
        if code != 0:
            continue
        try:
            txt = blob.decode("utf-8")
        except UnicodeDecodeError:
            continue
        scan_text(txt, f, findings, nets, creds)
    return findings


def scan_paths(paths, nets: bool, creds: bool):
    findings = []
    for p in paths:
        root = pathlib.Path(p)
        it = [root] if root.is_file() else root.rglob("*")
        for fp in it:
            if not fp.is_file() or fp.suffix.lower() not in TEXT_EXT:
                continue
            try:
                txt = fp.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            scan_text(txt, str(fp), findings, nets, creds)
    return findings



def log_scan_event(scope, hits):
    """全仓扫描后**自动记事件**（供成本记账自动计次）。仅在全仓模式调用；失败不影响扫描结果。"""
    try:
        import json as _j
        import subprocess as _sp
        _sp.run([sys.executable, str(pathlib.Path(__file__).with_name("ops_event.py")), "log",
                 "--action", "disclosure.scan", "--target", str(scope),
                 "--result", "hits=%d" % hits],
                capture_output=True, timeout=30)
    except Exception:  # noqa: BLE001
        pass


def basis_line(scope):
    """比对基准声明（承 DF-CONFLICT-...-RESOLUTION：冲突多源于基准不同，故须显式声明）。"""
    import datetime as _dt
    import subprocess as _sp
    try:
        head = _sp.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True, timeout=30).stdout.strip()
        n = _sp.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True, timeout=60)
        files = [x for x in (n.stdout or "").split("\n") if x.strip()]
    except Exception:  # noqa: BLE001
        head, files = "?", []
    return "★ 比对基准：范围=%s ｜ HEAD=%s ｜ 基准文件数=%d ｜ 采样时点=%s（+08）" % (
        scope, head, len(files), _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", nargs="*", default=None)
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--mine-only", action="store_true")
    ap.add_argument("--net-only", action="store_true")
    ap.add_argument("--cred-only", action="store_true")
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args()

    nets = not a.cred_only
    creds = not a.net_only

    if a.staged:
        out, _ = git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
        files = [x for x in out.split("\n") if x.strip()]
        findings = []
        for f in files:
            if pathlib.Path(f).suffix.lower() not in TEXT_EXT:
                continue
            blob, code = git(["show", ":%s" % f], binary=True)
            if code != 0:
                continue
            try:
                scan_text(blob.decode("utf-8"), f, findings, nets, creds)
            except UnicodeDecodeError:
                continue
        scope = "暂存区（提交前闸）"
    elif a.mine_only:
        findings = scan_paths([str(REPO / "deliverables")], nets, creds)
        scope = "deliverables/（含他席件，仅按路径粗筛）"
    elif a.paths:
        findings = scan_paths(a.paths, nets, creds)
        scope = "指定路径"
    else:
        findings = scan_repo(nets, creds)
        scope = "全仓（git ls-files @ HEAD）"

    print("★ 披露前扫描闸 —— 范围：%s ｜ 网络标识=%s ｜ 凭据形态=%s" % (scope, nets, creds))
    print("★ 纪律：本工具**不回显值**，仅示类别与掩码")
    print(basis_line(scope if "scope" in dir() else "见下"))
    print("")
    if not findings:
        print("| 结果 | 命中 |")
        print("|---|---|")
        print("| **干净** | **0** |")
        print("")
        print("VERDICT=CLEAN")
        return 0

    bycat = {}
    for f in findings:
        bycat[(f[2], f[3])] = bycat.get((f[2], f[3]), 0) + 1
    print("| 类别 | 形态 | 命中数 |")
    print("|---|---|---|")
    for (grp, cat), n in sorted(bycat.items(), key=lambda kv: -kv[1]):
        print("| %s | %s | %d |" % (grp, cat, n))
    print("")
    print("| 文件 | 行 | 类别 | 形态 | 掩码 |")
    print("|---|---|---|---|---|")
    for f, ln, grp, cat, mk in findings[:40]:
        print("| `%s` | %d | %s | %s | `%s` |" % (f, ln, grp, cat, mk))
    if len(findings) > 40:
        print("| … | … | … | … | （共 %d 条，余略） |" % (len(findings) - 40))
    print("")
    print("VERDICT=FINDINGS(%d)" % len(findings))
    print("处置提示：与判据无逻辑关联者改记**类别名**；确需身份绑定时值只入本地附件；**登记时勿复述值**。")
    return 0 if a.report_only else 1


if __name__ == "__main__":
    sys.exit(main())
