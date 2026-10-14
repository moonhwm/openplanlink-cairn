# -*- coding: utf-8 -*-
"""otl_batch.py —— 将本席之件批量转为真 WPS 智能文档（.otl）（2026-10-14 立）

依据：令条「相关文档统一转换为 WPS OTL 格式，并与云文档体系实现兼容，
      确保版本追踪、权限管控及留痕审计等功能有效落地」
链路（承 led_1526／1527）：drive create-empty-file → otl insert-content → drive read-file 回读

纪律：
  ★1 只在本席自己账号之「我的云文档」中新建（不触他席任何件）
  ★2 content 须为 CommonMark 子集：Unicode 制表图须以围栏包裹（约束②）
  ★3 含密钥样式之件不转（交人工脱敏）
  ★4 逐件回读校验，记录 file_id 与版本号；失败如实报
  ★5 --limit N 限量；--dry 只示计划

用法：python otl_batch.py [--limit 6] [--dry]
"""
import json, pathlib, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8")
H = pathlib.Path.home()
CLI = H / ".kimi-work" / "bin" / "kdocs-cli.exe"
SEAT = (H / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
LOG = SEAT / "outbox" / "wps_read" / ("OTL批量转换_%s.json" % time.strftime("%Y%m%d_%H%M"))  # ★分文件（不覆盖）
SECRET = [re.compile(r"sk-cp-[A-Za-z0-9_\-]{20,}"), re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
          re.compile(r"ark-[0-9a-f]{8}-[0-9a-f\-]{20,}"), re.compile(r"AKID[A-Za-z0-9]{12,}"),
          re.compile(r"LTAI[A-Za-z0-9]{10,}")]
BOX = re.compile(r"[│├└─┌┐┘┬┴┼╔╗╚╝║═]")

TARGETS = [
    "档案运营管理SOP_SOP-20261014-CAIRN-01.md",
    "环境与依赖交付基线_ENV-BASELINE-20261014-CAIRN-01.md",
    "A2A通信协议与接口规范_PROTO-A2A-20261014-CAIRN-01.md",
    "类联合国机制初始化纲要_UNMECH-20261014-CAIRN-01.md",
    "辩护席位规程草案_DEFENSE-20261014-CAIRN-01.md",
    "WPS_OTL正解链路与实操约束_OTLCHAIN-20261014-CAIRN-01.md",
    # ── 第二批（Round 46 续转）──
    "权限矩阵与数据字典_RBAC-DICT-20261014-CAIRN-01.md",
    "数字人员工注册规范_SEAT-REG-20261014-CAIRN-01.md",
    "检索评测集规范_IRS-20261014-CAIRN-01.md",
    "独立复现校验报告_REPRO-20261014-CAIRN-01.md",
    "WPS云文档API直读方法学_WPSAPI-20261014-CAIRN-01.md",
    "A2A节点发现与接入方案_NODE-DISCOVERY-20261014-CAIRN-01.md",
    "OTL格式与元数据完整性规范_OTL-SPEC-20261014-CAIRN-01.md",
    "两账对账总表_LEDGER-RECON-20261014-CAIRN-03.md",
    "台账分叉研判_LEDGER-FORK-20261014-CAIRN-02.md",
    "盘C归因更正_CLOUDPLACEHOLDER-20261014-CAIRN-01.md",
    "大件归档评估_ARCHIVE-20261014-CAIRN-01.md",
    "开源协议条款匹配对拍表_LIC-MATCH-20261014-CAIRN-02.md",
    "三目录摸底与启动方案_SURVEY-20261014-CAIRN-01.md",
    # ── 第三批（Round 69 续转：本夜新出之件）──
    "Round13-51总账与候裁清单_DF-OPS-20261014-CAIRN-117.md",
    "安装包候选清理清单_DLCLEAN-20261014-CAIRN-01.md",
    "类联合国机制初始化纲要_UNMECH-20261014-CAIRN-01.md",
    "辩护席位规程草案_DEFENSE-20261014-CAIRN-01.md",
    "数字人员工注册规范_SEAT-REG-20261014-CAIRN-01.md",
    "权限矩阵与数据字典_RBAC-DICT-20261014-CAIRN-01.md",
]


def call(svc, cmd, args, timeout=240):
    r = subprocess.run([str(CLI), svc, cmd, "--args", json.dumps(args, ensure_ascii=False)],
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_raw": (r.stdout or "")[:200], "_err": (r.stderr or "")[:160]}


def deep_id(o, depth=0):
    if depth > 6:
        return None
    if isinstance(o, dict):
        for k in ("file_id", "id"):
            v = o.get(k)
            if isinstance(v, str) and len(v) >= 12:
                return v
        for v in o.values():
            r = deep_id(v, depth + 1)
            if r:
                return r
    elif isinstance(o, list):
        for v in o:
            r = deep_id(v, depth + 1)
            if r:
                return r
    return None


def to_commonmark(t: str) -> str:
    """★约束②：含 Unicode 制表图之连续行块，以围栏包裹（CommonMark 子集）"""
    out, buf = [], []
    def flush():
        if buf:
            out.append("```")
            out.extend(buf)
            out.append("```")
            buf.clear()
    for ln in t.splitlines():
        if BOX.search(ln):
            buf.append(ln)
        else:
            flush()
            out.append(ln)
    flush()
    return "\n".join(out)


def main() -> int:
    dry = "--dry" in sys.argv
    lim = 6
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            lim = int(sys.argv[i + 1])
    # ★--all：遍历 outbox/mem 之全部可转件（≥400 字之 .md；含密钥者由下方自动排除）
    targets = list(TARGETS)
    if "--all" in sys.argv:
        mem = SEAT / "outbox" / "mem"
        names = []
        for p in sorted(mem.glob("*.md"), key=lambda q: -q.stat().st_size):
            try:
                if len(p.read_text(encoding="utf-8", errors="replace")) >= 400:
                    names.append(p.name)
            except OSError:
                continue
        # 已转者置前（幂等复用，可刷新 version），未转者随后
        targets = names + [x for x in TARGETS if x not in names]
        lim = len(targets)
        print("   ★--all：候选 %d 件（含已转者，将复用覆盖）" % len(targets))
    res = []
    # ★幂等之基：先取「我的云文档」现有件（名 ⇒ id），供复用
    existing = {}
    if not dry:
        jl = call("drive", "list-my-files", {"page_size": 300, "filter_type": "file"})
        for it in (((jl.get("data") or {}).get("items")) or []):
            nm = str(it.get("name") or "").replace(".otl", "")
            if nm and it.get("id"):
                existing.setdefault(nm, it.get("id"))
        print("   ★现有云端件 %d 件（幂等之基）" % len(existing))
    for name in targets[:lim]:   # ★--all 支持：用 targets（原误写 TARGETS[:lim]，致 --all 无效）
        p = SEAT / "outbox" / "mem" / name
        if not p.exists():
            print("   ★缺件：%s" % name); continue
        t = p.read_text(encoding="utf-8", errors="replace")
        if any(x.search(t) for x in SECRET):
            print("   ★含密钥样式、不转：%s" % name); continue
        md = to_commonmark(t)
        title = re.sub(r"\.md$", "", name)[:48]
        print("   ── %s（%d 字 ⇒ CommonMark 后 %d 字）" % (name[:44], len(t), len(md)))
        if dry:
            continue
        # ★幂等：先查「我的云文档」是否已有同名件 ⇒ 命中则复用其 file_id（insert-content 覆盖），不新建
        fid = existing.get(title)
        if fid:
            print("      · 已存在同名件，复用 ⇒ 覆盖（不新建）")
            j1 = {"code": 0, "_reused": True}
        else:
            j1 = call("drive", "create-empty-file", {"name": title, "file_extension": "otl", "on_name_conflict": "rename"})
            fid = deep_id(j1)
        if not fid:
            print("      ★建件未得 id（code=%s msg=%s）⇒ 跳过" % (j1.get("code"), str(j1.get("message"))[:40])); continue
        j2 = call("otl", "insert-content", {"file_id": fid, "title": title, "content": md,
                                           "format": "markdown", "mode": "replace"})
        ver = None
        try:
            ver = j2["data"]["detail"]["result"]["version"]
        except Exception:
            pass
        time.sleep(2)
        j3 = call("drive", "read-file", {"file_id": fid, "format": "markdown"})
        d3 = j3.get("data") or {}
        back = next((d3[k] for k in ("content", "text", "markdown", "body") if isinstance(d3.get(k), str)), "")
        ok = "✓" if (j2.get("code") == 0 and j3.get("code") == 0 and len(back) > 0) else "✗"
        print("      %s 建=%s 写=%s（version=%s）回读=%s（%d 字）｜ file_id=%s" % (
            ok, j1.get("code"), j2.get("code"), ver, j3.get("code"), len(back), str(fid)[:24]))
        res.append({"name": name, "title": title, "file_id": fid, "create": j1.get("code"),
                    "insert": j2.get("code"), "version": ver, "readback_code": j3.get("code"),
                    "readback_chars": len(back), "src_chars": len(t)})
    if res:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print("   ★落盘：%s（%d 件）" % (LOG.name, len(res)))
    okc = sum(1 for r in res if r.get("insert") == 0 and r.get("readback_chars", 0) > 0)
    print("   ══ 汇总：转换成功 %d 件 / 尝试 %d 件 ══" % (okc, len(res)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
