# -*- coding: utf-8 -*-
"""termtable.py —— **议题术语表**（可执行版）：术语一致性校验
（承令条「同步在 Kimi Chat 端部署相应技能，辅助开展**术语一致性校验**」「杜绝术语歧义」）

本器把**研究段第一手发现**与**网络既有判别**固化为**可校验条目**：
  每条＝{术语, 义项[], 原文/档号锚, 状态, 检查规则}

用法：
    python termtable.py list                     # 打印术语表（人读）
    python termtable.py check --mine-only        # 扫本席交换区件
    python termtable.py check --paths <dir>      # 扫指定目录（递归）
    python termtable.py export --json <path>     # 导出机读表
退出码：0＝未命中｜1＝命中（须人工判读）｜2＝用法错误
纪律：**只读、只报告**；**不回显值**；命中仅是**提示**，最终判读在人（承"候选≠判据"）。
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
EXCHANGE = SEAT.parent / "A2A共同体_共享交换区"

# ── 术语表（每条含：义项、锚、状态、检查规则） ─────────────────────────────
TERMS = [
    {
        "term": "价值重估 / Umwertung",
        "senses": [
            {"label": "①主人式·创造价值", "meaning": "自发的价值创造（werteschaffen）", "anchor": "GM I §2, §10"},
            {"label": "②奴隶式·反转价值", "meaning": "以否定外部为出发点的价值反转（Ressentiment 之作）", "anchor": "GM I §7"},
        ],
        "status": "必分列（两义敌对）",
        "check": {"pattern": r"价值重估|Umwertung", "qualifier": r"主人式|奴隶式|创造|反转|分列|两义",
                  "advice": "须注明为「主人式·创造」抑或「奴隶式·反转」（否则同一议题内指称敌对操作）"},
    },
    {
        "term": "自决 / zijue-self-determination",
        "senses": [
            {"label": "①自发型（可）", "meaning": "拥有自己的、独立的、长久意志；可为自身作保", "anchor": "GM II §2（autonom↔sittlich 互斥）"},
            {"label": "②反应型（禁）", "meaning": "以反对外部规定为出发点 ⇒ 结构上即 Ressentiment", "anchor": "GM I §10（Aktion ist von Grund aus Reaktion）"},
        ],
        "status": "定义须取①，禁止取②",
        "check": {"pattern": r"自决[^。\n]{0,20}(反抗|对抗|反对外部|抵制外部)|(反抗|对抗|反对外部)[^。\n]{0,12}自决",
                  "qualifier": r"自发|非反应|非 Ressentiment|不取",
                  "advice": "「自决」不得定义为「反对外部规定」（该结构＝Ressentiment）；宜取「自发型」定义并注明发生学/运作两层"},
    },
    {
        "term": "禁欲理想 / asketisches Ideal（按主体分列）",
        "senses": [
            {"label": "艺术家：无或杂多", "meaning": "「在艺术家那里是无，或杂多至极」", "anchor": "GM III §1"},
            {"label": "哲学家/学者：生产条件", "meaning": "对高级精神性最有利前提之嗅觉与本能（非德性，而是支配性本能的经济）", "anchor": "GM III §1, §8"},
            {"label": "祭司：权力工具", "meaning": "真正的祭司信仰、其最好的权力工具", "anchor": "GM III §1"},
            {"label": "生理失败者：病态自欺", "meaning": "「对此世而言太好了」之神圣形式的放纵", "anchor": "GM III §1"},
            {"label": "圣徒：冬眠借口", "meaning": "其 novissima gloriae cupido、其在「无」（「神」）中的安息", "anchor": "GM III §1"},
        ],
        "status": "必按主体分列（异质之物）",
        "check": {"pattern": r"禁欲理想|asketisches Ideal",
                  "qualifier": r"艺术家|哲学家|学者|祭司|圣徒|生理|按主体|分列|德性|支配性本能",
                  "advice": "「禁欲理想」须按主体分列（艺术家/哲学家/祭司/圣徒/失败者各不同）；且「禁欲」作为道德德性 ≠ 作为高产条件（GM III §8）"},
    },
    {
        "term": "良心 / Gewissen",
        "senses": [
            {"label": "甲义·债务所生", "meaning": "由债权—惩罚结构生成的内化（他律）", "anchor": "GM II §4, §6"},
            {"label": "乙义·自主者之良心", "meaning": "对自身与命运之支配的意识（自律）", "anchor": "GM II §2"},
        ],
        "status": "必分列",
        "check": {"pattern": r"凭良心|良心的?(自律|他律)|Gewissen",
                  "qualifier": r"甲义|乙义|债务所生|自主者|分列",
                  "advice": "「良心」须注明系「债务所生（他律内化）」抑或「自主者之良心（自律支配）」"},
    },
    {
        "term": "（则四）评价性/历史性判断须带时点",
        "senses": [{"label": "价值翻转", "meaning": "褒贬随史而变：今日之「德」可能正是昔日之「罪」", "anchor": "GM III §9"}],
        "status": "必带时点",
        "check": {"pattern": r"(历来|自古以来|一向|从来|历史上|传统上)[^。\n]{0,30}(优秀|拙劣|先进|落后|错误|正确|成功|失败|合理|不合理)",
                  "qualifier": r"\d{4}|时点|当时|彼时|截至|版本",
                  "advice": "含评价之历史性判断须带时点（褒贬随史而变，GM III §9；承则四）"},
    },
    {
        "term": "（则三）工具/技能陈述须带时点与版本",
        "senses": [{"label": "形式流动·意义更流动", "meaning": "同一工具/技能在不同阶段可承载不同意义", "anchor": "GM II §12"}],
        "status": "须注时点与版本",
        "check": {"pattern": r"(该|本|此)(工具|技能|闸门|脚本)[^。\n]{0,14}(可用|有效|已实现|已就绪|已修复|已落实)",
                  "qualifier": r"\d{4}-\d{2}|时点|版本|HEAD|副本",
                  "advice": "称「该工具/技能可用/已实现」须注时点与版本或副本（承则三）"},
    },
    {
        "term": "自我克服 / Selbst-überwindung",
        "senses": [
            {"label": "①自主支配（可）", "meaning": "对自身与命运的支配（Herrschaft über sich；与「自决」同向）", "anchor": "GM II §2"},
            {"label": "②内向施暴（须标注）", "meaning": "自由本能被潜抑后转而反对自身的 Verinnerlichung（其「乐趣」属残酷）", "anchor": "GM II §16, §18"},
        ],
        "status": "必分列（性质相反）",
        "check": {"pattern": r"自我克服|Selbst-überwindung|Selbstüberwindung",
                  "qualifier": r"自主|支配|施暴|内化|Verinnerlichung|分列|两义",
                  "advice": "「自我克服」须注明系「自主支配」（GM II §2）抑或「内向施暴」（§16/§18），否则「自决」可能被误读为自我施暴之正当化"},
    },
    {
        "term": "主人道德 / 奴隶道德（Herren-/Sklaven-Moral）",
        "senses": [
            {"label": "作为类型", "meaning": "两种价值规定方式（高贵↔可鄙 / 善↔恶）", "anchor": "JGB §260"},
            {"label": "★并存事实", "meaning": "二者可同处一人一灵魂（sogar im selben Menschen, innerhalb einer Seele）", "anchor": "JGB §260"},
        ],
        "status": "用作二分时须并述「同灵魂并存」",
        "check": {"pattern": r"主人道德|奴隶道德",
                  "qualifier": r"并存|同一灵魂|混|调和|非二元|兼",
                  "advice": "以二者为二分对立时，宜并述 JGB §260「可在同一灵魂内并存」以免绝对化"},
    },
    {
        "term": "打通 / 可用 / 不可用（节点）",
        "senses": [{"label": "规范表述", "meaning": "无入参之节点一律记「未测」；严禁写「可用」亦严禁写「不可用」", "anchor": "DF-CCM-20261007-HY4-01 §四"}],
        "status": "硬纪律",
        "check": {"pattern": r"(Neon|Supabase|WPS|ima|百度网盘|百炼)[^。\n]{0,16}?(可用|不可用|已打通|已接入)",
                  "qualifier": r"未测|未核实|待核|无入参",
                  "advice": "无入参节点须记「未测」；「打通」不等于「常驻可用」"},
    },
    {
        "term": "marginals ≠ joint（边际≠联合）",
        "senses": [{"label": "判别", "meaning": "各维边际成立不推出联合成立；须给出联合口径或声明未测", "anchor": "本席 DF-START6 映射"}],
        "status": "方法论",
        "check": {"pattern": r"各维度?均(已)?(合规|达标|满足)[^。\n]{0,20}(整体|联合|统一)",
                  "qualifier": r"联合|joint|分别|边际",
                  "advice": "「各维均达标」不得径推「整体达标」——须区分 marginal 与 joint"},
    },
    {
        "term": "报告值 ≠ 核实值",
        "senses": [{"label": "判别", "meaning": "「推送/写入报成功」不等于「已核实」；须以独立核验为准", "anchor": "本席自课（多轮实战）"}],
        "status": "本席纪律",
        "check": {"pattern": r"(报成功|报告成功|返回成功)[^。\n]{0,20}(已核实|核实一致|确认一致)",
                  "qualifier": r"未核实|待核|非 live|快照",
                  "advice": "「报成功」与「已核实」须分列（本席 push_all 已按此设计）"},
    },
]

# ── ★v3（轮29 落地三事）：①「自限栏」(则十四·则二十一) ②「反证条件栏」(则十六) ──
LIMITS = {
    "价值重估 / Umwertung": {"origin": "文本所载（GM I §7 直引）", "viewpoint": "谱系学之发生—功能视角", "degree": "★或为程度差异（创造与反转或系同一历程之两段）"},
    "自决 / zijue-self-determination": {"origin": "文本所载（GM II §2；I §10）", "viewpoint": "发生学（Ressentiment）与运作（支配）两层", "degree": "★或为程度差异（自发与反应或为连续谱）"},
    "良心 / Gewissen": {"origin": "文本所载（GM II §4·§6／§2）", "viewpoint": "债务—内化视角 vs 自主支配视角", "degree": "★或为程度差异"},
    "自我克服 / Selbst-überwindung": {"origin": "文本所载（GM II §2／§16·§18）", "viewpoint": "支配 vs 内转两层", "degree": "★或为程度差异（支配过度即近施暴）"},
    "禁欲理想 / asketisches Ideal（按主体分列）": {"origin": "文本所载（GM III §1 逐类列举）", "viewpoint": "按主体（artist/philosopher/priest/saint）", "degree": "非程度差异（系异质之物）"},
    "主人道德 / 奴隶道德（Herren-/Sklaven-Moral）": {"origin": "文本所载（JGB §260）", "viewpoint": "类型学视角", "degree": "★或为程度差异（JGB §260 明言同灵魂内并存）"},
    "打通 / 可用 / 不可用（节点）": {"origin": "本席推演（承 DF-CCM §四）", "viewpoint": "工程核验视角", "degree": "非程度差异（三态离散）"},
    "marginals ≠ joint（边际≠联合）": {"origin": "本席推演（DF-START6）", "viewpoint": "统计口径视角", "degree": "非程度差异"},
    "报告值 ≠ 核实值": {"origin": "本席推演（本席自课）", "viewpoint": "核验层级视角", "degree": "非程度差异"},
    "（则四）评价性/历史性判断须带时点": {"origin": "文本所载（GM III §9）", "viewpoint": "价值变迁视角", "degree": "非程度差异"},
    "（则三）工具/技能陈述须带时点与版本": {"origin": "文本所载（GM II §12）", "viewpoint": "版本—形态视角", "degree": "非程度差异"},
}

FALSIFIERS = {
    "价值重估 / Umwertung": "若原文某处将两义混用而不及区分意图（直引可证）⇒ 分列失据",
    "自决 / zijue-self-determination": "若原文以「反对外部」正面界定自决 ⇒ 本席②义之禁立失据",
    "良心 / Gewissen": "若原文仅一义且自洽 ⇒ 分列失据",
    "自我克服 / Selbst-überwindung": "若原文将支配与施暴视为同一而不加分别 ⇒ 分列失据",
    "禁欲理想 / asketisches Ideal（按主体分列）": "若原文某类主体未列举 ⇒ 该义须删（并须补缺号）",
    "主人道德 / 奴隶道德（Herren-/Sklaven-Moral）": "若原文否认二者可并存（直引可证）⇒ 并存提示失据",
    "打通 / 可用 / 不可用（节点）": "若某节点确有无入参之可复现判定 ⇒ 该节点可脱离「未测」",
    "marginals ≠ joint（边际≠联合）": "若给出联合口径且受核 ⇒ 由「未证」转「已证」",
    "报告值 ≠ 核实值": "若核验链与报告链同源且可复算 ⇒ 二者合一",
    "（则四）评价性/历史性判断须带时点": "若判断为纯技术性（无历史褒贬）⇒ 不适用",
    "（则三）工具/技能陈述须带时点与版本": "若对象自始至今唯一形态（有据）⇒ 可免注版本",
}

# ★「提及语境」标记（不删、只降级为"已注明"）：规则自述/列举/检验要求等语境
MENTION_RE = r"自限|反证条件|须过.{0,8}检验|术语表|规则之列|则十[四五六]|本二分|分义项|提及"
# ★v3.1（轮30）：增补"议题提及"语境（议题/之选择/研究段）——★并登记风险：词表愈宽，愈有过吞真违规之虞（未决之问）
MENTION_RE = MENTION_RE + r"|议题|之选择|研究段|本议题"


def scan_file(p):
    """两段限定：**行级**（qualifier）或**文档级**（doc_qualifier）命中其一 ⇒ 视为已限定。
    文档级判据承本席自纠：行级判据对"全文已作区分、但某行仅提及术语"者会误报。"""
    hits = []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    lines = text.splitlines()
    for i, ln in enumerate(lines, 1):
        for t in TERMS:
            chk = t["check"]
            m = re.search(chk["pattern"], ln)
            if not m:
                continue
            line_ok = bool(re.search(chk["qualifier"], ln))
            doc_pat = chk.get("doc_qualifier") or chk["qualifier"]
            doc_ok = bool(re.search(doc_pat, text))
            # ★v3：**提及语境**（规则自述/列举/检验要求）⇒ 降级为"已注明"，**不删除**（承"误报须辨明"）
            mention = bool(re.search(MENTION_RE, ln))
            hits.append({"line": i, "term": t["term"], "qualified": line_ok or doc_ok or mention,
                         "qualified_by": ("行级" if line_ok else ("文档级" if doc_ok else ("★提及语境" if mention else "未限定"))),
                         "advice": chk["advice"], "masked": ln.strip()[:110]})
    return hits


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    c = sub.add_parser("check")
    c.add_argument("--paths", nargs="*", default=None)
    c.add_argument("--mine-only", action="store_true")
    e = sub.add_parser("export")
    e.add_argument("--json", required=True)
    a = ap.parse_args()

    if a.cmd == "list":
        print("★ 议题术语表（%d 条；每条含义项、锚、状态与检查规则）" % len(TERMS))
        for t in TERMS:
            print("\n■ %s ｜ 状态：%s" % (t["term"], t["status"]))
            for s in t["senses"]:
                print("   - %s：%s（锚：%s）" % (s["label"], s["meaning"], s["anchor"]))
            print("   检查：%s" % t["check"]["advice"])
            lim = LIMITS.get(t["term"])
            if lim:
                print("   ★自限：来源=%s ｜ 视角=%s ｜ %s" % (lim["origin"], lim["viewpoint"], lim["degree"]))
            fal = FALSIFIERS.get(t["term"])
            if fal:
                print("   ★反证条件：%s" % fal)
        return 0

    if a.cmd == "export":
        terms = []
        for tt in TERMS:
            row = dict(tt)
            row["limit"] = LIMITS.get(tt["term"])
            row["falsifier"] = FALSIFIERS.get(tt["term"])
            terms.append(row)
        out = {"schema": "opl-termtable/3", "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"),
               "terms": terms,
               "note": "v3：含自限栏（则十四·则二十一）与反证条件栏（则十六）"}
        pathlib.Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("★ 已导出机读术语表：%s（%d 条）" % (a.json, len(TERMS)))
        return 0

    roots = [EXCHANGE] if (a.mine_only or not a.paths) else [pathlib.Path(x) for x in a.paths]
    files = []
    missing = []
    for r in roots:
        if not r.exists():
            missing.append(str(r))
            continue
        # ★v2 自纠（轮22）：**单文件路径亦须受理**（此前仅 rglob 目录 ⇒ 传文件时静默 0 文件却报 CLEAN）
        if r.is_file():
            files.append(r)
            continue
        for ext in ("*.otl", "*.md", "*.txt"):
            files += [f for f in r.rglob(ext) if f.is_file()]
    if a.mine_only:
        files = [f for f in files if "CAIRN" in f.name]
    print("★ 术语一致性校验（%s，北京时间）" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  范围：%d 文件 ｜ 条目：%d%s" % (len(files), len(TERMS),
          (" ｜ 不存在之路径 %d" % len(missing)) if missing else ""))
    # ★v2：**范围为空不得记 CLEAN**（承"未测不列"；0 文件扫描＝未测，非"清白"）
    if not files:
        print("  ⇒ **范围为空 ⇒ 未测**（不得据此记 CLEAN）")
        for m in missing:
            print("     不存在：%s" % m)
        return 2
    total = unqual = 0
    for f in sorted(files):
        hs = scan_file(f)
        if not hs:
            continue
        bad = [h for h in hs if not h["qualified"]]
        total += len(hs); unqual += len(bad)
        print("  · %s：命中 %d，其中**未加限定 %d**" % (f.name, len(hs), len(bad)))
        for h in bad[:2]:
            print("      行%d ｜ %s ｜ %s" % (h["line"], h["term"], h["advice"][:60]))
    print("  ⇒ 合计命中 %d ｜ **须人工判读 %d**（其余经行级或文档级限定）" % (total, unqual))
    print("  VERDICT=" + ("CLEAN" if total == 0 else ("QUALIFIED" if unqual == 0 else "NEEDS_REVIEW")))
    return 1 if unqual else 0


if __name__ == "__main__":
    sys.exit(main())
