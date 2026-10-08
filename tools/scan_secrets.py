#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
scan_secrets.py —— 石敢当席「凭据扫描闸」   v1.2.0

v1.2.0 一处（来由：**盲推题2′ #12**，本席独立复核后采纳）
  ⑦ 增【覆盖率报告】——v1.0–v1.1 只报「命中」，不报「覆盖了哪些件、跳过哪些件」，
     无覆盖清单与跳过原因，**无法证明没漏**。命中数与覆盖率是两件事：
     `0 命中 + 80% 覆盖率` **不等于**干净。现每次目录扫描后输出：
     文件总数／已扫／跳过／覆盖率／件型分布／跳过明细。
     ★纪律：**跳过项 ≠ 干净**；跳过即未覆盖，**须人工签核**。
  ★并修：本 docstring 因含 `\s`、`\-` 等转义序列触发 SyntaxWarning（本席自查发现），
     改为原始字符串（★本行首版误写了字面量三引号，反把 docstring 提前闭合、
     致文件当场语法失败——已删。教训：**讲修补的文档，自己先得能被解析**）。

v1.1.1 两处（来由：自主运维 P5 出件自扫，**自己的闸咬了自己的文档**）
  ⑤ `cos-signature` 原为 `[Xx]-[Cc]os-[Ss]ignature` —— 只匹配【头名】、不含任何值，
     故**无熵、无值也报**。实证：本席自己的三份文档只因【提到这个头名】就被报成凭据。
     ⇒ 改为必须带值：`…signature\s*[:=]\s*[A-Za-z0-9%+/=_.\-]{12,}`。
  ⑥ `conn-string-creds` 加【占位符排除】——本席规则表文档里写着
     `postgres://user:pass@host/db` 这一**占位示例**，v1.1 首版把 `pass` 当真凭据报了。
     ⇒ 占位符（pass/password/pwd/secret/xxx/placeholder/example）不报。
  ★ 影响实测：outbox **5 → 1**（四假阳性全消），而底稿**32 → 32**、单件**16 → 16**
     ——**修假阳性没放走真货**，这是修完必须验的那一条。
  ★ 残余 1 处经人工核为【文档自咬】（规则表 v1.0 自己举例的 `sk-ws-…` 文本），
     非凭据。不为它加脆弱启发式——**置信度分级列为 v1.2 项**，当前靠
     「机检不得单独定论、须人工交叉对照」的口径处置。

v1.1.0 四处（来由：第1批复算件的比对表 + 盲推题2′的独立推导，两路同指）
  ① 增连接串正则 `://user:pass@` —— v1.0 只抓 URL 参数里的签名，不抓 `://` 里的
     `user:pass`（这是**真缺口**：数据库连接串嵌的密码我全看不见）。
  ② TEXT_EXT 补 `.toml` —— 实测 v1.0 的清单里没有它。
  ③ 增单件模式 —— v1.0 只有目录模式，`scan_secrets.py <文件>` 直接报「不是目录」；
     而"只查一个文件"恰是最常用的动作。两种模式共用 `_scan_entry`，防逻辑漂移。
  ④ 强制 UTF-8 stdout —— v1.0 在 GBK 控制台下中文全乱码（实测），
     而本工具的结论正是要给人读的，乱码等于没输出。

来由
────
2026-09-29 本席受件时把一份内嵌**明文阿里云百炼密钥**的 docx 抄入 OneDrive 同步面
（见台账 SECURITY_FINDING / TOOL_GAP）。复盘结论：**"凭据不入同步面"光靠纪律不够，
必须有扫描闸**——纪律早写在章程里，工具层没兜住。本工具即为补闸。

它干什么
────────
递归扫描指定目录（或单个文件）下的**文本文件**，按模式表找疑似凭据；
命中只报【文件 + 行号 + 模式名 + 前 6 字符掩码】，★**永不打印完整值**。

红线（写在代码里）
──────────────────
1. 命中值一律掩码（前 6 字符 + ***），**任何输出路径都不得泄出完整凭据**。
2. 只读扫描，不改动被扫文件（脱敏由调用方显式决定，本工具不擅自改人文件）。
3. 二进制/超大文件跳过并登记，不硬解。
4. 自扫豁免：跳过本文件自身（含自测用的合成样本）。
5. ★**"通过"只等于"未命中已知模式"，不等于"件内无密钥"**——这条鸿沟靠覆盖率
   报告与人工交叉对照收窄，**无法靠加规则消除**（盲推题2′的结论，本席照准）。

零第三方依赖。
"""
from __future__ import annotations
import hashlib
import pathlib
import re
import sys

# ★ 强制 UTF-8 输出（v1.1 第④处）：GBK 控制台下中文全乱码，而结论是要给人读的。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SELF = pathlib.Path(__file__).resolve()

PATTERNS = [
    # ★ 词边界 (?<![A-Za-z0-9]) 不可省：首版缺它，把技能名 desk-load-orchestrator
    #   里的 "sk-loa…" 咬成密钥（L1116 假阳性实证在案）。
    ("aliyun-bailian/sk-ws", re.compile(r"(?<![A-Za-z0-9])sk-ws-[A-Za-z0-9_\-]{8,}")),
    # ★ 点分段形态：首版两条 sk- 模式都因点号断裂而漏报真密钥（L1138 假阴性实证在案）。
    ("dotted-sk-key",        re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{2,}(?:\.[A-Za-z0-9_\-]{2,}){2,}")),
    ("openai-style-sk",      re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{16,}")),
    ("anthropic-sk-ant",     re.compile(r"(?<![A-Za-z0-9])sk-ant-[A-Za-z0-9_\-]{16,}")),
    ("github-pat",           re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{20,}")),
    ("aliyun-akid",          re.compile(r"(?<![A-Za-z0-9])AKID[0-9A-Za-z]{12,}")),
    ("aws-akia",             re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}")),
    ("private-key-block",    re.compile(r"BEGIN [A-Z ]{0,20}PRIVATE KEY")),
    ("ssh-pubkey",           re.compile(r"ssh-(rsa|ed25519|dss)\s+AAAA[A-Za-z0-9+/=]{20,}")),
    # ★ v1.1.1 修正（来由：P5 出件自扫逮到自己的假阳性）：本模式原为 `[Xx]-[Cc]os-[Ss]ignature`
    #   ——它只匹配【头名】，不含任何值，故无熵、无值也报。实证：本席自己的三份文档
    #   （规则表 v1.0、回执、进度）只因【提到这个头名】就被报成凭据命中。
    #   头名不是凭据。⇒ 改为【必须带值】才报。
    ("cos-signature",        re.compile(r"[Xx]-[Cc]os-[Ss]ignature\s*[:=]\s*[A-Za-z0-9%+/=_.\-]{12,}")),
    ("url-signature-param",  re.compile(r"[?&](Signature|sign|signature|q-signature|q-ak)=[A-Za-z0-9%+/=_.\-]{12,}")),
    # ★ v1.1 第①处·连接串内嵌凭据：`scheme://user:pass@host`。
    #   来由：第1批复算件比对表指为缺口，盲推题2′亦独立指出「非标准格式的凭证」——
    #   两路同指。v1.0 只抓 URL 参数里的签名，对 `postgres://u:p@h/db` 完全无感。
    #   ★ v1.1.1 加占位符排除：本席自己的规则表文档里写着 `postgres://user:pass@host/db`
    #   这一【占位示例】，首版把 `pass` 当真凭据报了（假阳性）。占位符不是凭据。
    ("conn-string-creds",    re.compile(r"://[^/\s:@]+:(?!(?:pass|password|passwd|pwd|secret|xxx+|your[-_]?password|placeholder|example)\b)[^/\s@]{3,}@")),
    ("bearer-token",         re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}")),
    ("supabase-jwt",         re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    ("assign-secret",        re.compile(r"(?i)\b(api[_-]?key|apikey|secret|passwd|password|token)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}")),
]

TEXT_EXT = {".md", ".txt", ".json", ".jsonl", ".py", ".js", ".ts", ".yml", ".yaml",
            ".ini", ".cfg", ".conf", ".csv", ".xml", ".html", ".ps1", ".sh", ".env", "",
            ".toml"}   # ★ v1.1 第②处：v1.0 清单里没有它（实测确认）
# ★ 容器件：首版把它们当"非文本后缀"整件跳过 —— 于是【装在 docx/pptx/zip 里的凭据
#   我的闸根本看不见】。这是盲区，不是保守。现加深度扫描：解开容器，逐条目扫。
CONTAINER_EXT = {".docx", ".pptx", ".xlsx", ".zip", ".docm", ".pptm"}
BIG = 8 * 1024 * 1024
BIG_CONTAINER = 64 * 1024 * 1024


def scan_container(p: pathlib.Path, label: str, hits: list):
    """深度扫描：解开 zip 类容器，对内部可解码为文本的条目逐条扫描。"""
    import zipfile
    try:
        z = zipfile.ZipFile(p)
    except Exception as e:
        hits.append({"file": label, "line": 0, "pattern": "容器不可解",
                     "masked": "(%s)" % type(e).__name__, "len": 0})
        return 0
    n = 0
    for info in z.infolist():
        if info.is_dir() or info.file_size > BIG:
            continue
        try:
            data = z.read(info)
        except Exception:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("utf-16")
            except UnicodeDecodeError:
                continue
        n += 1
        scan_text(text, "%s!%s" % (label, info.filename), hits)
    return n


def mask(s: str) -> str:
    """按值长分档掩码。

    ★ v1.2 采纳项（**盲推题2′ #6**）：原为固定 `s[:6] + "***"`——对**短值暴露比例过高**，
    实证：12 位密钥**露出半截（50%）**，而"12 位"恰是很多服务端密钥的长度。
    本席原设计默认"密钥都长"，**这个默认没有依据**。

    分档（保长度信息由调用方另报 `len`，此处不再加长输出）：
      值长 ≤ 8   → 全遮蔽
      值长 ≤ 20  → 只留前 2 字符
      值长 > 20  → 留前 6 字符（与旧行为一致，便于历史比对）
    """
    n = len(s)
    keep = 0 if n <= 8 else (2 if n <= 20 else 6)
    return (s[:keep] + "***") if keep else "***"


# ═══ v1.3 熵基线（★盲推题2′ #1 采纳项）═══════════════════════════════════
# 来由：v1.0–v1.2 只按【形态库】匹配（sk-、AKIA、Bearer、AKID…）。盲推原话：
#   「规则绑定『密钥形态』库，**凡不在库内的随机串都不触发**。」
#   这是本席反复声明「不在域」的**最大一处**——今天把它移进「**在域·低置信**」。
# ★ 纪律（不可让）：**熵高 ≠ 密钥**。base64 图片、UUID、随机 ID、压缩流都会命中。
#   故本检测【一律标低置信】，只进人工交叉对照队列（本席 v1.0 已立「机检不得单独定论」）。
ENTROPY_MIN_LEN = 24
ENTROPY_MIN_BITS = 4.5
# 阈值为何取 4.5：**纯 hex 的理论熵上限恰为 4.0**（16 个符号）⇒ 十六进制摘要
#   自然被排除；base64／随机字母数字约 5.5–6.0 ⇒ 命中。4.5 即两者的分界线。
ENTROPY_TOKEN = re.compile(r"[A-Za-z0-9+/=_\-]{%d,}" % ENTROPY_MIN_LEN)


def shannon(s: str) -> float:
    """香农熵（bit/char）。"""
    import math
    from collections import Counter
    n = len(s)
    return -sum((v / n) * math.log2(v / n) for v in Counter(s).values())


def scan_entropy(line: str, lineno: int, label: str, hits: list, covered=()):
    """熵基线：补「无前缀、无固定形态」的自由文本密钥。

    ★ 去重（v1.3 实测后补）：若某个熵 token 的**字符区间已被高置信命中覆盖**，
    则不再重复报——否则同一个 ssh 公钥会被「ssh-pubkey」与「entropy-blob」各报一次，
    低置信队列被自己的重复项淹没，**真正的新信号反而看不见**。
    """
    for m in ENTROPY_TOKEN.finditer(line):
        s = m.group(0)
        if not (any(c.isdigit() for c in s) and any(c.isalpha() for c in s)):
            continue                      # 纯数字/纯字母串日常物太多，不收
        a, b = m.span()
        if any(not (b <= ca or a >= cb) for ca, cb in covered):
            continue                      # 已被高置信覆盖，不重复报
        e = shannon(s)
        if e < ENTROPY_MIN_BITS:
            continue
        hits.append({"file": label, "line": lineno,
                     "pattern": "entropy-blob(低置信)", "masked": mask(s),
                     "len": len(s), "entropy": round(e, 2)})


# ★ v1.3.2 第二类占位符（有标准可依）：**RFC 2606 保留的举例域名**。
#   来由：镜像 `gitlab-cli-guide/.../commands.md` 的 `https://…@gitlab.example.com/…`
#   被本席 `conn-string-creds` 当真凭据报了——而 example.com 本就【专供文档举例】。
#   ★ 判据放在**行级**而非值级：本席连接串模式的匹配止于 `@`，**域名不在匹配值里**，
#     只看值查不出域名——这是"匹配范围"与"判据范围"不重合的典型坑。
EXAMPLE_DOMAINS = re.compile(
    r"(?i)\b(example\.(com|org|net)|localhost|127\.0\.0\.1|0\.0\.0\.0|your[-_]?(domain|host)|foo\.bar)")


def _looks_like_placeholder(v: str) -> bool:
    """填充式占位符判定：**尾部 8 位全为同一字符**。

    来由（v1.3.2，有实证）：OpenPlanLink 镜像的 vendored 脚本里写着
    `SECRET_ID = "AKIDxxxxxxxxxxxxxxxx"  # TODO: 你的 SecretId`——本席的 `aliyun-akid`
    模式把它当真凭据报了。本席在**不打印该值**的前提下做了结构诊断（报结构、不报值），
    确认其尾部字符集 = {x}，即**同一字符重复填充**。

    ★ 为何阈值取 8：真密钥（62 字符集）尾部 8 位全同的概率约 (1/62)^7 ≈ 0，可忽略。
    ★ 为何【不丢弃】：丢弃 = 制造盲区；**降级为低置信**既压噪声又留证据。
    """
    return len(v) >= 8 and len(set(v[-8:])) == 1


def scan_text(text: str, label: str, hits: list):
    for i, line in enumerate(text.splitlines(), 1):
        covered = []
        line_is_example = bool(EXAMPLE_DOMAINS.search(line))
        for name, pat in PATTERNS:
            for m in pat.finditer(line):
                covered.append(m.span())
                val = m.group(0)
                if _looks_like_placeholder(val):
                    tag = "(占位符·低置信)"
                elif line_is_example:
                    tag = "(示例域·低置信)"
                else:
                    tag = ""
                hits.append({"file": label, "line": i, "pattern": name + tag,
                             "masked": mask(val), "len": len(val)})
        scan_entropy(line, i, label, hits, covered)


def _scan_entry(p: pathlib.Path, label: str, hits: list, skipped: list) -> int:
    """扫单个条目；返回 1＝已扫，0＝跳过。

    ★ 抽出来由（v1.1 第③处）：v1.0 只有目录模式，`scan_secrets.py <文件>` 直接报
    「不是目录」——而"只查一个文件"恰是最常用的动作。目录模式与单件模式共用本函数，
    防止两条路径的逻辑漂移：**同一件在两个入口得到不同结论，是扫描器最羞耻的缺陷**。
    """
    if p.resolve() == SELF:
        return 0
    ext = p.suffix.lower()
    if ext not in TEXT_EXT and ext not in CONTAINER_EXT:
        # ★ 未知后缀【不再一律跳过】：先试严格 UTF-8 解码，能解码就扫。
        #   来由：.regen-new 这类"改了名的文本件"会被后缀白名单整件漏掉——
        #   换名即逃逸，是扫描器最容易自我欺骗的一条路。
        if p.stat().st_size <= BIG:
            try:
                scan_text(p.read_text(encoding="utf-8", errors="strict"),
                          label + "〔未知后缀·按文本扫〕", hits)
                return 1
            except (UnicodeDecodeError, OSError):
                pass
        skipped.append((label, "非文本非容器后缀（试解码亦失败）"))
        return 0
    if ext in CONTAINER_EXT:
        if p.stat().st_size > BIG_CONTAINER:
            skipped.append((label, "容器超 %d MB" % (BIG_CONTAINER // (1 << 20))))
            return 0
        scan_container(p, label, hits)
        return 1
    try:
        if p.stat().st_size > BIG:
            skipped.append((label, "超 %d MB" % (BIG // (1 << 20))))
            return 0
        text = p.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError) as e:
        skipped.append((label, "非 UTF-8／不可读：%s" % type(e).__name__))
        return 0
    scan_text(text, label, hits)
    return 1


def scan_dir(root: pathlib.Path):
    hits, skipped, scanned = [], [], 0
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        scanned += _scan_entry(p, str(p.relative_to(root)), hits, skipped)
    return hits, skipped, scanned


def scan_single(p: pathlib.Path):
    """单件扫描（v1.1 第③处新增）。"""
    hits, skipped, scanned = [], [], 0
    scanned += _scan_entry(p, p.name, hits, skipped)
    return hits, skipped, scanned


def selftest() -> bool:
    """阴阳自检：合成样本必命中；干净文本必不命中。合成样本运行时拼接，不落字面量。"""
    ok = True
    fake = "sk" + "-ws-" + ("A1b2C3d4E5f6G7h8" * 2)
    hits = []
    scan_text("nothing here\nkey=%s\ndone" % fake, "<selftest>", hits)
    if not hits:
        print("[SELFTEST] 阴性失败：合成凭据未被检出"); ok = False
    else:
        for h in hits:
            if fake in h["masked"] or len(h["masked"]) > 20:
                print("[SELFTEST] ★掩码失败：命中值可能泄出完整凭据"); ok = False
    hits2 = []
    scan_text("这是一段干净的中文说明，含 sk 两个字母但没有密钥形态。", "<selftest>", hits2)
    if [h for h in hits2 if h["pattern"] == "aliyun-bailian/sk-ws"]:
        print("[SELFTEST] 阳性失败：干净文本被误报为凭据"); ok = False

    # ★ v1.1：新加的模式【自己也要过阴阳两例】——加了模式却不知它会咬什么，等于没加。
    #   阳性例：连接串里嵌的密码必须被咬到。
    hits3 = []
    scan_text("db=postgres://appuser:%s@db.internal:5432/prod" % ("Pw9" * 5),
              "<selftest>", hits3)
    if not [h for h in hits3 if h["pattern"] == "conn-string-creds"]:
        print("[SELFTEST] ★阴性失败：连接串内嵌凭据未被检出（conn-string-creds 哑火）"); ok = False
    else:
        for h in hits3:
            if "Pw9" in h["masked"] and h["masked"].count("Pw9") > 1:
                print("[SELFTEST] ★掩码失败：连接串密码可能泄出"); ok = False
    #   阴性例：普通 URL（无 `user:pass@`）不得被误报。
    hits4 = []
    scan_text("见 https://example.com/a/b 与 http://host:8080/path 两处文档",
              "<selftest>", hits4)
    if [h for h in hits4 if h["pattern"] == "conn-string-creds"]:
        print("[SELFTEST] ★阳性失败：普通 URL 被误报为连接串凭据（误报会淹没真信号）"); ok = False

    # ★ v1.1.1 新增两例（来由：P5 出件自扫逮到本席自己的两处假阳性）——
    #   ①【占位示例】不是凭据：规则表文档里写着 `postgres://user:pass@host/db`，首版把它报了。
    hits5 = []
    scan_text("示例：postgres://user:pass@host/db 与 mysql://root:password@127.0.0.1/x",
              "<selftest>", hits5)
    if [h for h in hits5 if h["pattern"] == "conn-string-creds"]:
        print("[SELFTEST] ★阳性失败：占位示例被当成真凭据（文档会被自己咬）"); ok = False
    #   ②【头名】不是凭据：`X-Cos-Signature` 只是头名，无值不该报。
    hits6 = []
    scan_text("请求头 X-Cos-Signature 用于校验；另有 X-Cos-Signature 说明。",
              "<selftest>", hits6)
    if [h for h in hits6 if h["pattern"] == "cos-signature"]:
        print("[SELFTEST] ★阳性失败：头名（无值）被当成凭据"); ok = False
    #   ③ 但【头名带值】必须仍命中（防矫枉过正把真货也放走）。
    hits7 = []
    scan_text("X-Cos-Signature: %s" % ("aB3dE5fG7hI9jK1" * 2), "<selftest>", hits7)
    if not [h for h in hits7 if h["pattern"] == "cos-signature"]:
        print("[SELFTEST] ★阴性失败：头名带值未被检出（矫枉过正）"); ok = False

    # ★ v1.2 新增一例（盲推 #6）：短值不得露出半截。
    fake_short = "sk-ws-" + ("Ab3" * 4)          # 共 17 字符
    if len(mask(fake_short)) > 5 and mask(fake_short).count("Ab3") > 0:
        print("[SELFTEST] ★掩码失败：短值露出过多（%s）" % mask(fake_short)); ok = False
    if mask("abc") != "***":
        print("[SELFTEST] ★掩码失败：超短值未被全遮蔽"); ok = False

    # ★ v1.3 两例（盲推 #1 熵基线）：
    #   阳性＝随机形态串须被【低置信】捕获；阴性＝**纯 hex 摘要不得被误收**（阈值校准的断言）。
    blob = "aB3dE5fG7hI9jK1mN3pQ5rS7tU9vW1xY"
    hb = []
    scan_entropy(blob, 1, "<selftest>", hb)
    if not hb:
        print("[SELFTEST] ★阴性失败：随机串未被熵基线捕获（v1.3 哑火）"); ok = False
    elif "低置信" not in hb[0]["pattern"]:
        print("[SELFTEST] ★分级失败：熵命中未标低置信（会与高置信并列误导）"); ok = False
    hexd = "9f2c7a1e4b6d8f0a2c4e6b8d0f2a4c6e8b0d2f4a6c8e0b2d4f6a8c0e2b4d6f8a"
    hh = []
    scan_entropy(hexd, 1, "<selftest>", hh)
    if hh:
        print("[SELFTEST] ★阳性失败：纯 hex 摘要被熵基线误收（阈值未把 hex 分出去）"); ok = False

    # ★ v1.3.2 两例（填充式占位符）：占位符【不得】被当高置信，但【也不得消失】。
    hp = []
    scan_text('SECRET_ID = "AKIDxxxxxxxxxxxxxxxx"  # TODO: 你的 SecretId', "<selftest>", hp)
    got = [h for h in hp if h["pattern"].startswith("aliyun-akid")]
    if not got:
        print("[SELFTEST] ★失败：占位符被整条丢弃（丢弃=制造盲区）"); ok = False
    elif "低置信" not in got[0]["pattern"]:
        print("[SELFTEST] ★失败：填充式占位符未被降级为低置信"); ok = False
    hr = []
    scan_text('SECRET_ID = "AKID6A1d7VrU8gw1tYzKapy22sb7R"', "<selftest>", hr)
    real = [h for h in hr if h["pattern"].startswith("aliyun-akid")]
    if not real or "低置信" in real[0]["pattern"]:
        print("[SELFTEST] ★失败：真形态 AKID 被误降级（矫枉过正）"); ok = False

    print("[SELFTEST] %s" % ("PASS（十二项自检均正确）" if ok else "FAIL"))
    return ok


COARSE = re.compile(r"[A-Za-z0-9_\-+=/]{16,}")


def mask_line(line: str) -> str:
    """把一行里所有命中的凭据子串替换为掩码，返回可安全打印的行。

    ★ 两层保险：①按模式表精确掩码；②二次兜底——凡 ≥16 字符的连续
    [A-Za-z0-9_-+=/] 且含至少一位数字的长 token，一律掩码。
    兜底是为防"模式外形态"（例如密钥里混入点号）导致掩码失效而原样打印。
    """
    out = line
    for _name, pat in PATTERNS:
        out = pat.sub(lambda m: mask(m.group(0)), out)

    def coarse(m):
        s = m.group(0)
        return mask(s) if any(ch.isdigit() for ch in s) else s

    out = COARSE.sub(coarse, out)
    return out.rstrip()


def cmd_line(args):
    """安全查看某文件的若干行：命中处就地掩码后再打印（绝不打印原文）。"""
    if len(args) < 2:
        print("用法：scan_secrets.py --line <文件> <行号>[,<行号>…]")
        return 2
    p = pathlib.Path(args[0])
    if not p.is_file():
        print("[ERR] 不是文件：%s" % p); return 2
    nums = []
    for part in args[1].split(","):
        part = part.strip()
        if part:
            nums.append(int(part))
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    for n in nums:
        if 1 <= n <= len(lines):
            print("L%-6d %s" % (n, mask_line(lines[n - 1])))
        else:
            print("L%-6d (超出范围，共 %d 行)" % (n, len(lines)))
    return 0


def cmd_why(args):
    """查出「到底是哪条模式咬的」——用于甄别假阳性/假阴性，输出仍为掩码。"""
    if len(args) < 2:
        print("用法：scan_secrets.py --why <文件> <行号>")
        return 2
    p = pathlib.Path(args[0])
    if not p.is_file():
        print("[ERR] 不是文件：%s" % p); return 2
    n = int(args[1])
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    if not (1 <= n <= len(lines)):
        print("[ERR] 行号超范围（共 %d 行）" % len(lines)); return 2
    line = lines[n - 1]
    print("L%d 长度=%d 字符" % (n, len(line)))
    hit = False
    for name, pat in PATTERNS:
        for m in pat.finditer(line):
            hit = True
            print("  模式命中 %-22s %s (len=%d)" % (name, mask(m.group(0)), len(m.group(0))))
    for m in COARSE.finditer(line):
        s = m.group(0)
        if any(c.isdigit() for c in s):
            hit = True
            print("  兜底命中 %-22s %s (len=%d)" % ("coarse-fallback", mask(s), len(s)))
    if not hit:
        print("  无任何模式命中 —— 若此行确含凭据，即为★假阴性，须补模式")
    return 0


REDACT_MARK = "[REDACTED-BY-CAIRN]"


def cmd_redact(args):
    """就地脱敏：把命中的凭据子串替换为标记，报【改前/改后】sha256 供台账留痕。

    纪律：①只替换命中片段，其余一字不动；②可指定单一模式名（默认全部凭据类模式）；
          ③永不打印被替换内容；④改前/改后哈希必报——脱敏也是修订，须留痕。
    ★ `--dry`：只算不写。报「将替换几处、改后哈希会变成什么」——
      使批准方在动手之前就知道确切的后果（本席 2026-09-29 立）。
    """
    dry = "--dry" in args
    rest = [a for a in args if a != "--dry"]
    if not rest:
        print("用法：scan_secrets.py --redact <文件> [模式名] [--dry]")
        return 2
    p = pathlib.Path(rest[0])
    if not p.is_file():
        print("[ERR] 不是文件：%s" % p)
        return 2
    only = rest[1] if len(rest) > 1 else None
    raw = p.read_bytes()
    before = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        print("[REFUSE] 非 UTF-8 文本件，本模式只处理文本底稿；二进制件请走容器流程。")
        return 1

    total = 0
    per = []
    for name, pat in PATTERNS:
        if only and name != only:
            continue
        text, k = pat.subn(REDACT_MARK, text)
        if k:
            per.append("%s×%d" % (name, k))
            total += k
    if not total:
        print("[NOOP] 无命中%s。sha256=%s" % ("（干跑）" if dry else "，未改动", before))
        return 0

    would = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if dry:
        # ★ 残留复扫：把「替换后的文本」再扫一遍。
        #   为何必须有这一步：替换按模式表顺序进行，前一条模式的标记可能吃掉后一条模式的匹配
        #   （实证：aliyun-akid 先替换，&q-ak=<AKID> 便不再满足 url-signature-param 的 {12,}，
        #   致每行两个签名参数只计一次替换）。⇒【只报替换数是不够的，必须报残留数】。
        residual = []
        for pname, ppat in PATTERNS:
            for m in ppat.finditer(text):
                residual.append((pname, m.group(0)))
        print("[DRY-RUN] 未写入任何字节（只算不写）")
        print("   将替换处数：%d ｜ %s" % (total, "、".join(per)))
        print("   改前 sha256 = %s" % before)
        print("   改后 sha256 = %s   ← 批准后执行即得此值，可事前核对" % would)
        print("   范围：%s" % (only or "全部凭据类模式"))
        if residual:
            kinds = "、".join(sorted(set(n for n, _ in residual)))
            tag = "（单模式干跑：未选中的模式命中属预期，不计为残留）" if only else "★替换【不足】，须补"
            print("   残留复扫：仍有 %d 处命中（%s）%s" % (len(residual), kinds, tag))
        else:
            print("   残留复扫：★0 处 —— 全部凭据值已被覆盖")
        print("   残留明细（掩码）：%s" % ("；".join("%s=%s" % (n, mask(v)) for n, v in residual[:6]) or "无"))
        return 0

    p.write_text(text, encoding="utf-8", newline="")
    after = hashlib.sha256(p.read_bytes()).hexdigest()
    print("[OK] 已就地脱敏（仅替换命中片段，其余未动）")
    print("   替换处数：%d ｜ %s" % (total, "、".join(per)))
    print("   改前 sha256 = %s   ← 须写入台账" % before)
    print("   改后 sha256 = %s" % after)
    return 0


def coverage_block(root: pathlib.Path, scanned: int, skipped: list):
    """★ v1.2 采纳项 —— 覆盖率报告。

    来由（**盲推题2′ #12**，本席独立复核后采纳）：
      「只报『命中』，不报『扫描覆盖了哪些件、跳过了哪些件』，无覆盖清单与跳过原因，
        **无法证明没漏**。」
    本席 v1.0–v1.1 一直只报命中——**命中数与覆盖率是两件事**：
      `0 命中 + 80% 覆盖率` **不等于**「干净」，它等于「80% 的部分干净，20% 我不知道」。

    纪律（写进代码）：**跳过项 ≠ 干净**。跳过即未覆盖，**须人工签核**。
    """
    total, ext_all = 0, {}
    for p in root.rglob("*"):
        if not p.is_file() or p.resolve() == SELF:
            continue
        total += 1
        e = p.suffix.lower() or "(无后缀)"
        ext_all[e] = ext_all.get(e, 0) + 1
    cov = (100.0 * scanned / total) if total else 100.0
    print("   --- 覆盖率报告（★盲推 #12 采纳项）---")
    print("   文件总数=%d ｜ 已扫=%d ｜ 跳过=%d ｜ 覆盖率=%.1f%%"
          % (total, scanned, len(skipped), cov))
    top = sorted(ext_all.items(), key=lambda kv: -kv[1])[:12]
    print("   件型分布：%s" % "、".join("%s×%d" % (k, v) for k, v in top))
    if skipped:
        print("   ★跳过 %d 件【不等于干净】：跳过即未覆盖，须人工签核——" % len(skipped))
        for s, why in skipped[:20]:
            print("      - %-48s %s" % (s[:48], why))
    else:
        print("   ★跳过 0 件 —— 全覆盖（覆盖率声明与命中声明俱备）")


def main():
    args = sys.argv[1:]
    if not args:
        print("用法：scan_secrets.py <目录|文件> [<目录|文件>…]   # v1.1 起文件亦可")
        print("      scan_secrets.py --selftest")
        print("      scan_secrets.py --line <文件> <行号>[,<行号>…]   # 掩码后安全查看")
        print("      scan_secrets.py --why  <文件> <行号>             # 查哪条模式咬的")
        print("      scan_secrets.py --redact <文件> [模式名] [--dry]   # 脱敏／干跑（只算不写）")
        return 2
    if args[0] == "--selftest":
        return 0 if selftest() else 1
    if args[0] == "--line":
        return cmd_line(args[1:])
    if args[0] == "--why":
        return cmd_why(args[1:])
    if args[0] == "--redact":
        return cmd_redact(args[1:])

    total = 0
    for a in args:
        root = pathlib.Path(a)
        if root.is_file():
            print("═══ 扫描（单件）：%s ═══" % root)
            hits, skipped, scanned = scan_single(root)
        elif root.is_dir():
            print("═══ 扫描：%s ═══" % root)
            hits, skipped, scanned = scan_dir(root)
        else:
            print("[ERR] 既不是文件也不是目录：%s" % root); return 2
        total += len(hits)
        print("文本文件已扫：%d ｜ 跳过：%d ｜ ★命中：%d" % (scanned, len(skipped), len(hits)))
        _lo = [h for h in hits if "低置信" in h["pattern"]]
        if _lo:
            # ★ v1.3 置信度分级（盲推 #7）：低置信单列，**不许与高置信并列误导**。
            print("   ★置信度分级：高置信 %d 处 ｜ 低置信 %d 处"
                  "（低置信仅进人工交叉对照队列，**不单独定论**）" % (len(hits) - len(_lo), len(_lo)))
        for h in hits:
            # ★ v1.3.1 修：原为 h["file"][:46] 截断——**长路径/嵌套件被截断后命中不可定位**，
            #   本席实查时据此找错了文件（把别的件的 L14 当成 cross-session 的 L14）。
            #   **路径不可定位 = 命中等于没报。** 改为完整路径。
            print("  ★ %s L%-5d %-22s %s (len=%d)" % (
                h["file"], h["line"], h["pattern"], h["masked"], h["len"]))
        if skipped:
            print("  跳过明细（前 8 条）：")
            for s, why in skipped[:8]:
                print("    - %-50s %s" % (s[:50], why))
        if root.is_dir():
            coverage_block(root, scanned, skipped)
    print("\n【结论】命中 %d 处。★掩码输出，完整值一律不打印。" % total)
    print("★覆盖率声明与命中声明必须同时给出——只有命中数、没有覆盖率，就【无法证明没漏】。")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
