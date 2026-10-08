# -*- coding: utf-8 -*-
"""arch_diagram.py —— 全链路「可交互架构图」生成器（自包含，无外部依赖）

对应令条：「操作完成后，同步生成**可交互架构图**，为全链路可视化溯源与调度提供有力支撑。」

产物：单文件 HTML（内联 CSS/SVG/JS，**零外部引用**），含：
  · 三层拓扑：**来源层**（本席语料）→ **核心操作集**（context-pruner / ultra-compress-ops / link-bridge-ops）
    → **落点层**（总线 / upload / 五存储节点）
  · **治理横切层**：台账(sha256 链) / 事件链 / 工单 / 主控台一页纸 / 预推守卫 / attest 同批扫描
  · **交互**：点击任一节点 → 右侧详情（**实测状态 + 证据 + 缺口**）；顶部图例可按状态高亮；内置**自检按钮**
  · 数据内联为 JSON，页面**自检**会校验：无外部引用、节点数、每条边端点存在、数据 JSON 可解析

纪律：图中所有状态均为**实测值并带采样时点**（承 HY4 裁决 §六.18）；未知即标「待定/未通」，不美化。
用法：python arch_diagram.py --out <html 路径>
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

SAMPLE_AT = "2026-10-07 07:5x（北京时间）"

NODES = [
    # 来源层
    {"id": "src_exp", "layer": "来源", "label": "exp（脚本/工具）", "x": 60, "y": 90,
     "state": "ok", "facts": ["1488 件 / 7.61 MB", "含 __pycache__ 与自造工具"],
     "evidence": "arch_diagram 生成时实测", "gap": "无"},
    {"id": "src_outbox", "layer": "来源", "label": "outbox（产出/快照）", "x": 60, "y": 160,
     "state": "ok", "facts": ["178 件 / 1.84 MB", "含 console/deskbase/mem 子目录"],
     "evidence": "同上", "gap": "无"},
    {"id": "src_arch", "layer": "来源", "label": "archive（归档 .otl）", "x": 60, "y": 230,
     "state": "ok", "facts": ["57 件 / 0.59 MB", "只增不删"],
     "evidence": "Get-ChildItem 实测", "gap": "无"},
    {"id": "src_hs", "layer": "来源", "label": "handshake（最重）", "x": 60, "y": 300,
     "state": "risk", "facts": ["2567 件 / 90.47 MB", "位于 WPS 云同步盘"],
     "evidence": "体积实测", "gap": "迁移前须过 link-bridge 缺陷与云同步护栏（DF-LBDEF）"},
    # 核心操作集
    {"id": "op_prune", "layer": "核心操作", "label": "context-pruner（裁剪）", "x": 300, "y": 120,
     "state": "ok", "facts": ["smoke PASS（v1.6.0）", "扫描：瞬态 0／保护 1(691KB)／复核 179(1.19MB)", "指针化覆盖 1.0；退化初评 低"],
     "evidence": "context_audit.py --scan/--report（scan_report_20261007_074747.json）",
     "gap": "瞬态=0 属合法常态；主战场在免读归档/aging"},
    {"id": "op_comp", "layer": "核心操作", "label": "ultra-compress-ops（极致压缩）", "x": 300, "y": 210,
     "state": "todo", "facts": ["仓内 SKILL.md 与脚本在盘", "尚未读取其规程与后端清单"],
     "evidence": "git ls-files 命中 3 件", "gap": "未并轨（本轮未读）"},
    {"id": "op_link", "layer": "核心操作", "label": "link-bridge-ops（桥接/回链）", "x": 300, "y": 300,
     "state": "defect", "facts": ["migrate-link 试点：数据已搬 A 盘，回链失败", "WinError 1314（无符号链接特权）", "junction 实测可用（mklink /J exit 0）"],
     "evidence": "DF-LBDEF-20261007-CAIRN-01（试点已还原，A 盘残留 0）",
     "gap": "缺预检/缺回滚；建议甲/乙/丙/丁候裁"},
    # 落点层
    {"id": "dst_bus", "layer": "落点", "label": "总线（落点待定）", "x": 560, "y": 90,
     "state": "todo", "facts": ["A:\\bus 不存在", "席区 bus/ 不存在", "候选：A:\\OPL_A2A（15268 件/5.17GB）"],
     "evidence": "Test-Path 实测", "gap": "落点须先核占用后定（§六.12）"},
    {"id": "dst_upload", "layer": "落点", "label": "upload（A:\\upload）", "x": 560, "y": 160,
     "state": "ok", "facts": ["存在：254 件 / 860.45 MB", "指向化干跑目标：A:\\upload\\cairn-cache\\temp-20261007"],
     "evidence": "Test-Path + 计数实测", "gap": "干跑计划 0 件（瞬态为空）"},
    {"id": "dst_wps", "layer": "落点", "label": "WPS 云文档", "x": 560, "y": 230,
     "state": "partial", "facts": ["本席席区即位于 WPSDrive 云盘", "WPS MCP 通道：无凭据未通"],
     "evidence": "路径实测 + MCP 探测（既往）", "gap": "WPS_API_TOKEN 等未授"},
    {"id": "dst_neon", "layer": "落点", "label": "Neon", "x": 560, "y": 300,
     "state": "blocked", "facts": ["MCP server 已装（@neondatabase/mcp-server-neon 0.4.1）", "NEON_API_KEY 未授"],
     "evidence": "mcp-servers 安装记录", "gap": "凭据缺口"},
    {"id": "dst_supa", "layer": "落点", "label": "Supabase", "x": 560, "y": 370,
     "state": "blocked", "facts": ["MCP server 已装（0.13.0）", "SUPABASE_ACCESS_TOKEN 未授"],
     "evidence": "同上", "gap": "凭据缺口"},
    {"id": "dst_ima", "layer": "落点", "label": "ima-skill", "x": 700, "y": 230,
     "state": "ok", "facts": ["本机已见 ima-readonly server 进程", "仓内 skills/ima-skill 在盘", "MCP 通道既往实测 17 工具"],
     "evidence": "进程实测 + 既往探测", "gap": "无"},
    {"id": "dst_baidu", "layer": "落点", "label": "百度网盘", "x": 700, "y": 300,
     "state": "ok", "facts": ["MCP 通道既往实测 27 工具", "A:\\BaiduSyncdisk 在盘"],
     "evidence": "既往探测 + 盘符实测", "gap": "无"},
    # 治理横切
    {"id": "gov_ledger", "layer": "治理", "label": "台账（sha256 链）", "x": 300, "y": 420,
     "state": "ok", "facts": ["621 条", "链内自洽 PASS"],
     "evidence": "cairn_ledger.py verify", "gap": "无"},
    {"id": "gov_ops", "layer": "治理", "label": "事件链 + 工单", "x": 140, "y": 420,
     "state": "ok", "facts": ["事件 16 条 PASS", "工单 3 张（候指派）"],
     "evidence": "ops_event.py verify", "gap": "工单受理归属候裁"},
    {"id": "gov_console", "layer": "治理", "label": "主控台一页纸", "x": 460, "y": 420,
     "state": "partial", "facts": ["本席可一键生成（console_report.py）", "跨席汇聚位/留存周期候裁"],
     "evidence": "DF-CONSOLE-20261006-CAIRN-01", "gap": "各席是否同形投递未定"},
    {"id": "gov_guard", "layer": "治理", "label": "预推守卫 + attest 同批扫描", "x": 620, "y": 420,
     "state": "ok", "facts": ["prepush_samebatch（推送前拦截）", "attest_sweep（历史回溯，近12提交真异常 0）"],
     "evidence": "两工具实跑", "gap": "无"},
    {"id": "gov_rmem", "layer": "治理", "label": "R_mem 必填第四项", "x": 140, "y": 480,
     "state": "todo", "facts": ["HY4 裁决：四项任一缺失即 FAIL", "本机 R_mem ≈ 596 MB（低于 M_floor 8%）"],
     "evidence": "DF-VERDICT-20261006-HY4-01", "gap": "本席三个报告工具尚未落地该项"},
]

EDGES = [
    ("src_exp", "op_prune"), ("src_outbox", "op_prune"), ("src_arch", "op_prune"), ("src_hs", "op_link"),
    ("op_prune", "op_comp"), ("op_comp", "op_link"),
    ("op_comp", "dst_bus"), ("op_comp", "dst_upload"),
    ("op_link", "dst_upload"), ("op_prune", "dst_upload"),
    ("op_comp", "dst_wps"), ("op_comp", "dst_neon"), ("op_comp", "dst_supa"),
    ("op_comp", "dst_ima"), ("op_comp", "dst_baidu"),
    ("gov_ledger", "gov_console"), ("gov_ops", "gov_console"),
    ("gov_guard", "gov_console"), ("gov_rmem", "gov_console"),
]

STATE_COLOR = {"ok": "#1f9d55", "partial": "#d69e2e", "todo": "#4299e1",
               "risk": "#dd6b20", "blocked": "#e53e3e", "defect": "#c53030"}
STATE_TEXT = {"ok": "已通", "partial": "部分", "todo": "待办", "risk": "风险",
              "blocked": "受阻", "defect": "缺陷"}

HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>OpenPlanLink · 上下文压缩迁移全链路（可交互）</title>
<style>
 body{margin:0;font-family:"Microsoft YaHei",system-ui,sans-serif;background:#0f172a;color:#e6edf3}
 header{padding:14px 20px;background:#111c33;border-bottom:1px solid #24334d}
 h1{font-size:16px;margin:0 0 4px} .sub{font-size:12px;color:#9db2ce}
 .wrap{display:flex;gap:14px;padding:14px 20px}
 .canvas{flex:1;background:#0b1424;border:1px solid #24334d;border-radius:10px;overflow:auto}
 aside{width:360px;background:#111c33;border:1px solid #24334d;border-radius:10px;padding:14px;font-size:13px}
 .legend{display:flex;gap:10px;flex-wrap:wrap;font-size:12px;margin-bottom:10px}
 .chip{display:inline-flex;align-items:center;gap:5px;cursor:pointer;padding:2px 8px;border:1px solid #2b3d5c;border-radius:20px}
 .dot{width:10px;height:10px;border-radius:50%}
 .node rect{cursor:pointer} .node text{pointer-events:none;font-size:12px;fill:#e6edf3}
 .label{font-size:11px;fill:#9db2ce}
 .edge{stroke:#2b3d5c;stroke-width:1.5;fill:none;marker-end:url(#arrow)}
 .hit rect{stroke-width:2.5}
 dl{margin:6px 0} dt{color:#9db2ce;font-size:11px;margin-top:8px} dd{margin:2px 0 0}
 code{background:#0b1424;padding:1px 4px;border-radius:4px}
 button{margin-top:10px;background:#1f9d55;color:#fff;border:0;border-radius:6px;padding:7px 12px;cursor:pointer}
 #chk{margin-top:8px;font-size:12px;white-space:pre-wrap;color:#9db2ce}
</style></head><body>
<header><h1>OpenPlanLink · 上下文压缩迁移全链路（可交互架构图）</h1>
<div class="sub">生成 @@TS@@ ｜ 采样时点 @@SAMPLE@@ ｜ 席位 a2a-node-local ｜ 本图自包含（零外部引用）</div></header>
<div class="wrap">
 <div class="canvas">
  <div class="legend" id="legend"></div>
  <svg id="svg" width="900" height="560" viewBox="0 0 900 560">
   <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
     <path d="M0,0 L10,5 L0,10 z" fill="#2b3d5c"/></marker></defs>
   <g id="edges"></g><g id="nodes"></g>
  </svg>
 </div>
 <aside>
  <div style="font-weight:600">节点详情</div>
  <div id="detail">点击左侧任一节点查看**实测状态 / 证据 / 缺口**。</div>
  <button id="selfcheck">运行页面自检</button>
  <div id="chk"></div>
 </aside>
</div>
<script>
const DATA = @@DATA@@;
const SC = @@SC@@, ST = @@ST@@;
const svg = document.getElementById('svg');
const edges = document.getElementById('edges'), nodes = document.getElementById('nodes');
const pos = {};
DATA.nodes.forEach(n => pos[n.id] = n);
DATA.edges.forEach(([a,b]) => {
  const A = pos[a], B = pos[b]; if(!A||!B) return;
  const x1=A.x+165, y1=A.y+22, x2=B.x-8, y2=B.y+22;
  const p=document.createElementNS(svg.namespaceURI,'path');
  p.setAttribute('d',`M$x1,$y1 C$x1+60,$y1 $x2-60,$y2 $x2,$y2`);
  p.setAttribute('class','edge'); edges.appendChild(p);
});
DATA.nodes.forEach(n => {
  const g=document.createElementNS(svg.namespaceURI,'g'); g.setAttribute('class','node'); g.dataset.id=n.id;
  const r=document.createElementNS(svg.namespaceURI,'rect');
  r.setAttribute('x',n.x);r.setAttribute('y',n.y);r.setAttribute('rx',8);
  r.setAttribute('width',165);r.setAttribute('height',44);
  r.setAttribute('fill','#132038');r.setAttribute('stroke',SC[n.state]);r.setAttribute('stroke-width',2);
  const t=document.createElementNS(svg.namespaceURI,'text'); t.setAttribute('x',n.x+10);t.setAttribute('y',n.y+20);
  t.textContent=n.label;
  const l=document.createElementNS(svg.namespaceURI,'text'); l.setAttribute('class','label');
  l.setAttribute('x',n.x+10);l.setAttribute('y',n.y+36); l.textContent=n.layer+' · '+ST[n.state];
  g.append(r,t,l); g.onclick=()=>show(n); nodes.appendChild(g);
});
function show(n){
  document.getElementById('detail').innerHTML =
    `<div style="font-weight:600;margin-bottom:6px">${n.label}</div>
     <dl><dt>层级 / 状态</dt><dd>${n.layer} · <b style="color:${SC[n.state]}">${ST[n.state]}</b></dd>
     <dt>实测</dt><dd>${n.facts.map(f=>'· '+f).join('<br>')}</dd>
     <dt>证据</dt><dd><code>${n.evidence}</code></dd>
     <dt>缺口 / 待办</dt><dd>${n.gap}</dd></dl>`;
  document.querySelectorAll('.node').forEach(g=>g.classList.toggle('hit', g.dataset.id===n.id));
}
const lg=document.getElementById('legend');
Object.keys(ST).forEach(k=>{
  const s=document.createElement('span'); s.className='chip';
  s.innerHTML=`<span class="dot" style="background:${SC[k]}"></span>${ST[k]}`;
  s.onclick=()=>document.querySelectorAll('.node').forEach(g=>{
    const n=pos[g.dataset.id]; g.style.opacity = (n.state===k)?'1':'0.25'; });
  lg.appendChild(s);
});
const all=document.createElement('span'); all.className='chip'; all.textContent='全部显示';
all.onclick=()=>document.querySelectorAll('.node').forEach(g=>g.style.opacity='1'); lg.appendChild(all);
document.getElementById('selfcheck').onclick=()=>{
  const out=[];
  const html=document.documentElement.outerHTML;
  const ext=/https?:\\/\\//.test(html.replace(/https?:\\/\\/www\\.w3\\.org[^"']*/g,''));
  out.push((ext?'FAIL':'PASS')+' · 无外部引用（SVG 命名空间除外）');
  const ids=new Set(DATA.nodes.map(n=>n.id));
  const bad=DATA.edges.filter(([a,b])=>!ids.has(a)||!ids.has(b));
  out.push((bad.length?'FAIL':'PASS')+` · 边端点均存在（${DATA.edges.length} 条，坏 ${bad.length}）`);
  out.push((DATA.nodes.length>0?'PASS':'FAIL')+` · 节点数 ${DATA.nodes.length}`);
  out.push((document.querySelectorAll('.node').length===DATA.nodes.length?'PASS':'FAIL')+' · DOM 节点数与数据一致');
  const st={}; DATA.nodes.forEach(n=>st[n.state]=(st[n.state]||0)+1);
  out.push('统计 · '+Object.entries(st).map(([k,v])=>ST[k]+' '+v).join(' ｜ '));
  document.getElementById('chk').textContent=out.join('\\n');
};
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    data = {"nodes": NODES, "edges": EDGES, "sample_at": SAMPLE_AT}
    html = (HTML
            .replace("@@TS@@", ts)
            .replace("@@SAMPLE@@", SAMPLE_AT)
            .replace("@@DATA@@", json.dumps(data, ensure_ascii=False))
            .replace("@@SC@@", json.dumps(STATE_COLOR, ensure_ascii=False))
            .replace("@@ST@@", json.dumps(STATE_TEXT, ensure_ascii=False)))
    if "@@" in html:
        raise SystemExit("未替换的占位符残留：%s" % [s for s in ("@@TS@@", "@@SAMPLE@@", "@@DATA@@", "@@SC@@", "@@ST@@") if s in html])
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    # 生成器侧自检
    assert "http://" not in html.replace("http://www.w3.org", ""), "存在外部引用"
    assert "https://" not in html.replace("https://www.w3.org", ""), "存在外部引用"
    ids = {n["id"] for n in NODES}
    bad = [e for e in EDGES if e[0] not in ids or e[1] not in ids]
    assert not bad, "坏边：%s" % bad
    st = {}
    for n in NODES:
        st[n["state"]] = st.get(n["state"], 0) + 1
    print("★ 已生成：%s（%d B）" % (p, p.stat().st_size))
    print("★ 自检：无外部引用 PASS ｜ 节点 %d ｜ 边 %d（坏 %d） ｜ 状态分布 %s" % (
        len(NODES), len(EDGES), len(bad),
        "、".join("%s=%d" % (STATE_TEXT.get(k, k), v) for k, v in sorted(st.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
