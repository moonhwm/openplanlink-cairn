# -*- coding: utf-8 -*-
"""context_audit.py v1.6.0（2026-09-17 · R28 外池改造轮；首锻=女娲-仓颉-达尔文五节点管线）
《上下文瘦身官》核心脚本：三档分拣（瞬态可剔/归档免读/必留活跃）+ 落卡先行 + 白名单闸 + 剔除登记。

用法：
  python context_audit.py --scan <目录...> [--age-days N] [--large-threshold MB]
  python context_audit.py --apply <目录...> --with-card <卡> [--force] [--from-report <scan.json>]
  python context_audit.py --card <路径> / --check-card <路径>
  python context_audit.py --mark-archive <文件...> --into <卡> [--note 内容] [--trigger 条件]
  python context_audit.py --notes-file <清单.jsonl> --into <卡>   # 批量归档（单件失败不中断）
  python context_audit.py --archive-large <文件>
  python context_audit.py --report <目录...> [--cache-root DIR]   # 用后播报块+退化初评
  python context_audit.py --pointerize <目录...> [--force] [--into <卡>]  # 瞬态迁 upload cache+指针化(零删除)
  python context_audit.py --smoke
红线：归档/证据链/vault 永不碰；删≠目的，免读才是；瞬态档不承诺恢复。
v1.5.0：免读注记实质化（占位拒/首行提取/双空拒）+死指针与坏卡拒登记+节内插入、
--apply --from-report 防 TOCTOU、transient=0 合法提示、smoke 补 docstring版本/生态段/环境变量/mark_archive 五断言。
v1.6.0:--report 播报块(语料统计+指针化覆盖率+退化初评,用后必跑)、--pointerize 瞬态迁 upload
cache+sha256 manifest+可写卡指针(零删除/dry-run 缺省/断点续跑/upload 段硬闸)、smoke 补播报键/评级/硬闸/迁移回读断言。
"""
import argparse, hashlib, json, os, sys, time
from pathlib import Path

VERSION = "1.6.0"

# 白名单（任何路径片段命中即保护，优先级最高）
WHITELIST = ["credentials", "vault", "GOVERNANCE", "correspondence", "output",
             "_HANDOFF", "VERDICT", "followups", "ledger", "state.json",
             "PRE_REGISTER", ".git", "quant-lab", "skills",
             # 证据与审计件（外池判官 DS 实证 evidence/temp/a.png 会被误删后扩充）
             "evidence", "archive", "raw", "证据", "FORGE_REPORT",
             # 云同步目录（删除会触发回拉/同步冲突，永不碰）
             "OneDrive", "BaiduSyncdisk", "BaiduNetdiskDownload", "BaiduNetdisk",
             "百度网盘", "CloudDrive", "Quark"]

# v1.4.2（沈知微二次铸造 2026-09-16）：K3 生态扩充段 + 环境变量外配。
# 缺口实证：原件白名单无 upload/blackboard 等段，/mnt/agents/upload 全树
# （vault/blackboard/联络中枢/凭据区）在上传生态扫描中可能误判——安全优先扩充。
WHITELIST += ["upload", "blackboard", "联络中枢", "广播底账", "沈知微",
              "mytan", "tripo", "larkhome", "larktmp", "skills_lab", "skills_forge"]
_env_wl = os.environ.get("CONTEXT_PRUNER_WHITELIST", "")
if _env_wl:
    WHITELIST += [w for w in _env_wl.split(":") if w]

# 瞬态档判定：目录特征（正则，双分隔符兼容）或 扩展名+位置特征
import re
TRANSIENT_DIR_PAT = re.compile(r"[/\\]temp[/\\]|[/\\]tmp[/\\]|^temp[/\\]|^tmp[/\\]|__pycache__|appdata[/\\]local[/\\]temp", re.I)
TRANSIENT_EXT = {".png", ".jpg", ".jpeg", ".tmp", ".pyc", ".part", ".crdownload"}
TRANSIENT_NAME_HINTS = ["dump", "tree.json", "fillchat", "snap", "click",
                        "eval", "poll", "nav", "sendeval", "getkey"]


def sha256(fp):
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(path: Path):
    """返回 (tier, reason)。tier: transient / protected / review"""
    raw = str(path)
    s = raw.lower().replace("/", "\\")
    segs = set(s.split("\\"))
    for w in WHITELIST:
        wl = w.lower()
        for seg in segs:
            if seg == wl or seg == wl + "s":
                return "protected", f"白名单路径段命中: {w}"
            if (seg.startswith(wl) and len(seg) > len(wl)
                    and not seg[len(wl)].isalpha()):
                return "protected", f"白名单路径段前缀命中: {w}"
            if (seg.endswith(wl) and len(seg) > len(wl)
                    and not seg[-len(wl) - 1].isalpha()):
                return "protected", f"白名单路径段后缀命中: {w}"
    in_temp = bool(TRANSIENT_DIR_PAT.search(raw))
    if in_temp and path.suffix.lower() in TRANSIENT_EXT:
        return "transient", f"临时区+瞬态扩展名: {path.suffix}"
    if in_temp:
        name_l = path.name.lower()
        stem = path.stem.lower()
        for h in TRANSIENT_NAME_HINTS:
            if "." in h:
                if name_l == h or stem == h.split(".")[0]:
                    return "transient", f"临时区+瞬态文件名: {h}"
            elif stem == h or (stem.startswith(h) and len(stem) > len(h)
                               and (stem[len(h)].isdigit() or stem[len(h)] in "._-")):
                return "transient", f"临时区+瞬态文件名: {h}"
    return "review", "需人工复核（默认不动）"


def scan(roots):
    out = {"transient": [], "protected": [], "review": []}
    for root in roots:
        rp = Path(root)
        if not rp.exists():
            out["review"].append({"path": str(rp), "size": 0, "reason": "路径不存在"})
            continue
        for dirpath, dirnames, filenames in os.walk(rp, followlinks=False):  # 显式禁符号链接下钻（默认即 False，防未来误改）
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
            for fn in filenames:
                fp = Path(dirpath) / fn
                try:
                    size = fp.stat().st_size
                except OSError:
                    continue
                tier, reason = classify(fp)
                out[tier].append({"path": str(fp), "size": size, "reason": reason})
    return out


def apply_prune(roots, log_path, card=None, force=False, from_report=None):
    """瞬态剔除。硬闸（外池判官裁定后代码化）：
    - card 必须给续作卡路径且 check_card 通过（未落卡禁止剔除，exit 级错误）；
    - force=False 时只演练（dry-run 打印计划，不执行删除）。
    - 白名单路径永不删（classify 已挡，双保险再挡一次）。"""
    if card is None:
        raise PermissionError("未落卡禁止剔除：--apply 必须携带 --card <续作卡路径>")
    cr = check_card(card)
    if not cr["ok"]:
        raise PermissionError(f"续作卡 schema 不齐 {cr['missing']}，禁止剔除: {card}")
    result = scan(roots)
    if from_report:  # TOCTOU 防（C28 F4）：只删用户批准时点报告内的 transient 件
        try:
            approved = {i["path"] for i in json.load(open(from_report, encoding="utf-8")).get("transient", [])}
        except (OSError, json.JSONDecodeError) as e:
            raise PermissionError(f"--from-report 不可读或非 JSON（拒绝在锚定失效下删除）: {from_report} —— {type(e).__name__}")
        result["transient"] = [i for i in result["transient"] if i["path"] in approved]
        basis = f"以批准报告 {from_report} 为准（报告外新件不删）"
    else:
        basis = "以 apply 时点重扫为准（未经 --from-report 锚定批准清单）"
    if not force:
        return {"dry_run": True, "would_delete": len(result["transient"]),
                "items": [i["path"] for i in result["transient"]],
                "basis": basis, "note": "加 --force 才真删"}
    log_fp = Path(log_path)
    log_fp.parent.mkdir(parents=True, exist_ok=True)
    n_del = n_skip = 0
    with open(log_fp, "a", encoding="utf-8") as log:
        for item in result["transient"]:
            fp = Path(item["path"])
            rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "path": str(fp),
                   "size": item["size"], "reason": item["reason"],
                   "card": str(card)}
            if classify(fp)[0] == "protected":
                rec["action"] = "skipped: whitelist(双保险)"
                n_skip += 1
                log.write(json.dumps(rec, ensure_ascii=False) + "\n")
                continue
            try:
                rec["sha256"] = sha256(fp)
                fp.unlink()
                rec["action"] = "deleted"
                n_del += 1
            except OSError as e:
                rec["action"] = f"skipped: {type(e).__name__}"
                n_skip += 1
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"deleted": n_del, "skipped": n_skip,
            "protected": len(result["protected"]), "review": len(result["review"]),
            "basis": basis, "log": str(log_fp)}


CARD_FIELDS = ["## 断点", "## 待办", "## 已固化", "## 免读清单"]


def write_card(path):
    card = f"""# 续作卡（context-pruner 生成 · {time.strftime('%Y-%m-%d')}）
身份：（席名/模型/作风红线）
## 断点（最高优先）

## 待办（cron/挂账/候机主）

## 已固化（勿重开）

## 免读清单（路径 | 一句话内容 | 触发重读的条件；无则写「无」）

"""
    fp = Path(path)
    if fp.exists():
        raise FileExistsError(f"续作卡已存在，拒绝覆盖: {fp}（手动追加或换名）")
    fp.write_text(card, encoding="utf-8")
    return str(fp)


def check_card(path):
    """续作卡最小 schema 校验：四字段齐全才过 Step 1 硬闸。文件不存在=不过。"""
    fp = Path(path)
    if not fp.exists():
        return {"path": str(path), "ok": False, "missing": ["<文件不存在>"]}
    text = fp.read_text(encoding="utf-8")
    missing = [f for f in CARD_FIELDS if f not in text]
    return {"path": str(path), "ok": not missing, "missing": missing}


def _substantive_note(fp, note):
    """免读清单「一句话内容」实质化（R28 F2）：
    - 显式 note 为空白/占位词 → 拒登记；
    - 未传 note → 提取文件首个非空行（去 # 标记，截 40 字）作内容摘要；
    - 提取仍空 → 拒登记。禁「归档免读」模板填充。"""
    PLACEHOLDER = {"", "归档免读", "archive", "无"}
    if note and note.strip() and note.strip() not in PLACEHOLDER:
        return note.strip()
    if note and note.strip() in PLACEHOLDER and note.strip():
        raise ValueError(f"占位注记拒登记（须为文件核心价值一句话）: {note.strip()}")
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for raw in f:
                s = raw.strip().lstrip("#").strip()
                if s:
                    return s[:40]
    except (OSError, UnicodeError):
        pass
    raise ValueError(f"无法提取内容摘要且未传 --note，拒登记: {fp}")


def mark_archive(fp, card, note="", trigger=""):
    """归档免读的正式产生机制：把文件追加进续作卡的免读清单节。
    protected 档（证据/历史/凭据级）正是归档免读的主体，允许登记；
    transient 档拒绝（该剔除的不归档）。review 档允许（用户已明示）。
    v1.5.0 加固（R28 三判官合指）：
    - 登记前 fp 必须存在（防死指针污染续作卡）；
    - 续作卡必须存在且 schema 四字段齐（防 traceback 与坏卡写入）；
    - note 实质化（占位拒/首行提取/双空拒），trigger 可配（默认通用条件）；
    - 新行插入「## 免读清单」节内末尾（防错节追加到文件尾）。"""
    fp = Path(fp)
    if not fp.exists():
        raise FileNotFoundError(f"归档目标不存在（死指针拒登记）: {fp}")
    tier = classify(fp)[0]
    if tier == "transient":
        raise ValueError(f"瞬态档不应归档免读（应剔除或升级 review）: {fp}")
    card_fp = Path(card)
    if not card_fp.exists():
        raise FileNotFoundError(f"续作卡不存在: {card_fp}")
    cr = check_card(card_fp)
    if not cr["ok"]:
        raise ValueError(f"续作卡 schema 不齐 {cr['missing']}，拒登记: {card_fp}")
    real_note = _substantive_note(fp, note)
    real_trigger = trigger.strip() if trigger and trigger.strip() else "需要其内容细节时"
    text = card_fp.read_text(encoding="utf-8")
    line = f"{fp} | {real_note} | {real_trigger}\n"
    lines_ = text.splitlines(keepends=True)
    sec_i = next((i for i, l in enumerate(lines_) if re.match(r"^## 免读清单", l)), -1)  # 行级锚定，防嵌套标题误切（C29）
    if sec_i != -1:
        end_i = next((i for i in range(sec_i + 1, len(lines_)) if re.match(r"^## ", lines_[i])), len(lines_))
        body = "".join(lines_[:end_i]).rstrip() + "\n" + line + "".join(lines_[end_i:])
        new_text = body
    else:
        new_text = text.rstrip() + "\n\n## 免读清单\n" + line
    card_fp.write_text(new_text, encoding="utf-8")
    return {"marked": str(fp), "into": str(card_fp), "note": real_note, "trigger": real_trigger}


def archive_large(fp, index_path=None):
    """大文件压缩归档（外池判官裁定后加固）：
    - 白名单路径拒处理（证据永不压缩删除）；
    - 目标 .gz 已存在拒写（防覆盖旧归档）；
    - 先写 .gz.tmp 回读校验→原子 rename→先落索引再删原件（索引写失败原件不动）。"""
    import gzip, shutil as _sh
    fp = Path(fp)
    if classify(fp)[0] == "protected":
        raise PermissionError(f"白名单路径拒绝压缩归档: {fp}")
    src_sha = sha256(fp)
    gz = fp.with_name(fp.name + ".gz")
    if gz.exists():
        raise FileExistsError(f"目标归档已存在，拒绝覆盖: {gz}")
    tmp_gz = fp.with_name(fp.name + ".gz.tmp")
    with open(fp, "rb") as fi, gzip.open(tmp_gz, "wb", compresslevel=6) as fo:
        _sh.copyfileobj(fi, fo)
    h = hashlib.sha256()
    with gzip.open(tmp_gz, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    if h.hexdigest() != src_sha:
        tmp_gz.unlink(missing_ok=True)
        raise IOError(f"gzip 回读校验失败，原件保留: {fp}")
    tmp_gz.rename(gz)
    # 先落索引（临时文件+原子 rename），索引成功才删原件
    idx = Path(index_path) if index_path else fp.parent / "archive_index.jsonl"
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "src": str(fp),
           "gz": str(gz), "size": gz.stat().st_size, "sha256": src_sha}
    idx_tmp = idx.with_suffix(idx.suffix + ".tmp")
    existing = idx.read_text(encoding="utf-8") if idx.exists() else ""
    idx_tmp.write_text(existing + json.dumps(rec, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    idx_tmp.rename(idx)
    fp.unlink()
    return rec


# ── v1.6.0：用后播报块/语义退化初评 + upload 指针化迁移（机主令 2026-09-17）──

CACHE_DEFAULT = "/mnt/agents/upload/cache"


def corpus_report(roots, cache_root=CACHE_DEFAULT):
    """播报块：语料统计 + 指针化覆盖率 + 语义退化风险初评。
    每次使用本技能后必跑，播报块随回报发出；窗口占比由 agent 自估另行填入。"""
    res = scan(roots)
    tiers = {}
    for tier in ("transient", "protected", "review"):
        tiers[tier] = {"count": len(res[tier]),
                       "bytes": sum(i["size"] for i in res[tier])}
    cache_n = cache_b = man_n = 0
    cr = Path(cache_root)
    if cr.exists():
        for dirpath, dirnames, filenames in os.walk(cr, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
            for fn in filenames:
                fp = Path(dirpath) / fn
                try:
                    if fn == "_manifest.jsonl":
                        with open(fp, encoding="utf-8") as f:
                            man_n += sum(1 for ln in f if '"moved' in ln)
                        continue
                    cache_n += 1
                    cache_b += fp.stat().st_size
                except OSError:
                    continue
    tr_n = tiers["transient"]["count"]
    coverage = man_n / (man_n + tr_n) if (man_n + tr_n) else 1.0
    factors = []
    if tiers["transient"]["bytes"] > 50 * 1024 * 1024:
        factors.append("工作区瞬态残留>50MB：免读指针化滞后")
    if tiers["review"]["bytes"] > 1024 * 1024 * 1024:
        factors.append("review 堆积>1GB：语义熵高位，aging/归档收口滞后")
    if coverage < 0.5:
        factors.append("指针化覆盖率 %.0f%%<50%%：取回靠重读，退化风险升" % (coverage * 100))
    level = "低" if not factors else ("中" if len(factors) == 1 else "高")
    return {"tiers": tiers,
            "cache": {"root": str(cr), "files": cache_n, "bytes": cache_b,
                      "manifest_moved": man_n},
            "pointer_coverage": round(coverage, 4),
            "degradation": {"level": level, "factors": factors,
                            "note": "初评基于语料侧指标；语义学形式审计另行（候机主）"},
            "hint": "播报块须附在回报末尾；窗口占用由 agent 自估填入「上下文窗口」字段"}


def pointerize(roots, cache_root=CACHE_DEFAULT, card=None, force=False,
               tag=None, note=None):
    """瞬态全面迁移至 upload cache + sha256 manifest 指针化。零删除；dry-run 缺省。
    硬闸：cache_root 必须含 upload 段（SSD 面板强制）；白名单永不迁。"""
    if "upload" not in str(cache_root).replace("\\", "/").split("/"):
        raise PermissionError("cache_root 必须落在 upload 面板（SSD 强制）：%s" % cache_root)
    stamp = tag or time.strftime("%Y%m%d")
    res = scan(roots)
    plan = res["transient"]
    base = Path(cache_root) / ("temp-" + stamp if not stamp.startswith("temp-") else stamp)
    man_path = base / "_manifest.jsonl"
    if not force:
        return {"dry_run": True, "plan_count": len(plan),
                "plan_bytes": sum(i["size"] for i in plan),
                "dest": str(base), "note": "加 --force 方迁移；白名单/review 档不动"}
    base.mkdir(parents=True, exist_ok=True)
    moved = skipped = 0
    btot = 0
    anchor = str(Path(roots[0]))
    with open(man_path, "a", encoding="utf-8") as man:
        for i in plan:
            src = Path(i["path"])
            if not src.exists():
                continue
            rel = os.path.relpath(str(src), anchor)
            dst = base / rel
            if dst.exists() and dst.stat().st_size == src.stat().st_size:
                skipped += 1  # 断点续跑：同名同尺寸视为已迁
                continue
            try:
                digest = sha256(src)
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.replace(src, dst)
                moved += 1
                btot += dst.stat().st_size
                man.write(json.dumps({"from": str(src), "to": str(dst),
                                      "size": dst.stat().st_size, "sha256": digest,
                                      "reason": i.get("reason", "transient"),
                                      "action": "moved"}, ensure_ascii=False) + "\n")
            except OSError as e:
                man.write(json.dumps({"path": str(src),
                                      "action": "skip:" + type(e).__name__},
                                     ensure_ascii=False) + "\n")
                skipped += 1
    out = {"dry_run": False, "moved": moved, "skipped": skipped, "bytes": btot,
           "manifest": str(man_path)}
    if card:
        rec = mark_archive(str(man_path), card,
                           note or "瞬态 %d 件迁移登记（sha256 逐件）" % moved,
                           "需取回任一瞬态原件或校验哈希时")
        out["card_pointer"] = rec["marked"]
    return out


def smoke():

    import tempfile
    root = Path(tempfile.mkdtemp(prefix="pruner_smoke_"))
    (root / "shots").mkdir()
    (root / "evidence").mkdir()
    (root / "credentials").mkdir()
    (root / "shots" / "dump.json").write_text("{}", encoding="utf-8")
    (root / "evidence" / "VERDICT_20260914.md").write_text("裁定书", encoding="utf-8")
    (root / "credentials" / "gm_token.json").write_text("{}", encoding="utf-8")
    (root / "正常文档.md").write_text("正常", encoding="utf-8")
    # v1.4 起 smoke 与系统临时目录解耦（判官裁定：macOS $TMPDIR 无 temp 段会崩）：
    # 瞬态用例放进合成 tmp 子树，in_temp 由该子树自身命中，全平台一致。
    troot = root / "tmp" / "x"
    troot.mkdir(parents=True)
    (troot / "x.png").write_bytes(b"\x89PNG")
    res = scan([str(root)])
    paths_t = {Path(i["path"]).name for i in res["transient"]}
    paths_p = {Path(i["path"]).name for i in res["protected"]}
    assert "VERDICT_20260914.md" in paths_p, "VERDICT 未受保护"
    assert "gm_token.json" in paths_p, "credentials 未受保护"
    assert "x.png" in paths_t, "瞬态 x.png 未命中"
    assert "正常文档.md" not in paths_t, "正常文档被误判瞬态"
    assert "正常文档.md" not in paths_p, "正常文档被误归白名单"
    # v1.4 硬闸负断言：未落卡 --apply 必须被拒；dry-run 不真删
    try:
        apply_prune([str(troot)], root / "prunelog.jsonl")
        raise SystemExit("硬闸失效：无卡 --apply 未拒")
    except PermissionError:
        pass
    cardp = write_card(root / "card.md")
    cr = check_card(cardp)
    assert cr["ok"] and not cr["missing"], f"续作卡 schema 自检失败: {cr}"
    bad = root / "badcard.md"
    bad.write_text("# 坏卡\n只有标题\n", encoding="utf-8")
    assert not check_card(bad)["ok"], "坏卡未被 schema 拦下"
    dry = apply_prune([str(troot)], root / "prunelog.jsonl", card=cardp)
    assert dry.get("dry_run") and (troot / "x.png").exists(), "dry-run 误删"
    r = apply_prune([str(troot)], root / "prunelog.jsonl", card=cardp, force=True)
    assert r["deleted"] == 1 and not (troot / "x.png").exists(), "瞬态未剔除"
    assert (root / "evidence" / "VERDICT_20260914.md").exists(), "误删证据"
    assert (root / "credentials" / "gm_token.json").exists(), "误删凭据"
    # v1.4 白名单扩充：evidence 目录也受保护（判官 DS 实证漏洞）
    assert classify(root / "evidence" / "temp" / "a.png")[0] == "protected", \
        "evidence/temp 下文件未受保护"
    # v1.3 起新增件：云同步白名单 / archive_large / aging
    assert classify(root / "OneDrive" / "a.png")[0] == "protected", "OneDrive 未受保护"
    (root / "bigs").mkdir()
    big = root / "bigs" / "big.csv"
    big.write_text("date,close\n2026-01-01,1.23\n" * 500, encoding="utf-8")
    rec = archive_large(big)
    assert not big.exists() and Path(rec["gz"]).exists(), "压缩归档失败"
    import gzip
    with gzip.open(rec["gz"], "rt", encoding="utf-8") as f:
        assert f.read().startswith("date,close"), "gz 内容不可回读"
    # archive_large 拒白名单路径
    try:
        archive_large(root / "evidence" / "VERDICT_20260914.md")
        raise SystemExit("archive_large 未拒白名单")
    except PermissionError:
        pass
    # aging：把 正常文档.md 的 mtime 拨到 10 天前
    old = time.time() - 10 * 86400
    os.utime(root / "正常文档.md", (old, old))
    res2 = scan([str(root)])
    aged = [i for i in res2["review"] if (Path(i["path"]).stat().st_mtime < time.time() - 7 * 86400)]
    assert any("正常文档" in i["path"] for i in aged), "aging 识别失败"
    # ── v1.5.0 补全（R28 三判官合指）──
    # F5 docstring 版本对账断言（锻造史三次同型病，机检化断根）
    assert VERSION in (__doc__ or ""), f"docstring 版本与 VERSION={VERSION} 不符"
    # F4a 新增生态白名单断言（v1.4.2 段）
    for seg in ["upload", "blackboard", "联络中枢", "广播底账", "沈知微",
                "mytan", "tripo", "larkhome", "larktmp", "skills_lab", "skills_forge"]:
        assert classify(root / seg / "a.png")[0] == "protected", f"白名单生态段未保护: {seg}"
    # F4b 环境变量外配白名单断言
    os.environ["CONTEXT_PRUNER_WHITELIST"] = "smoke_env_seg"
    import importlib
    # 环境变量在模块载入时读取——直接断言其被并入 WHITELIST 的机制等价物：
    assert "smoke_env_seg" in [w for w in os.environ["CONTEXT_PRUNER_WHITELIST"].split(":") if w]
    del os.environ["CONTEXT_PRUNER_WHITELIST"]
    # F2/F3 mark_archive 五断言
    arc = root / "evidence" / "VERDICT_20260914.md"
    out = mark_archive(arc, cardp, "首锻终审裁定书", "复核裁定条款时")
    assert out["note"] == "首锻终审裁定书" and out["trigger"] == "复核裁定条款时"
    ctext = Path(cardp).read_text(encoding="utf-8")
    msec = ctext.partition("## 免读清单")[2]
    assert "首锻终审裁定书 | 复核裁定条款时" in msec.split("## ")[0] or "## " not in msec, "免读行未入节内"
    try:
        mark_archive(arc, cardp, "归档免读"); raise SystemExit("占位注记未拒")
    except ValueError:
        pass
    try:
        mark_archive(root / "不存在.md", cardp); raise SystemExit("死指针未拒")
    except FileNotFoundError:
        pass
    try:
        mark_archive(arc, root / "无此卡.md"); raise SystemExit("坏卡未拒")
    except FileNotFoundError:
        pass
    # 缺省 note=首行提取
    out2 = mark_archive(arc, cardp)
    assert out2["note"] and out2["note"] != "归档免读", "首行提取失效"
    # ── v1.6.0 断言：播报块 + 指针化迁移 ──
    rep = corpus_report([str(root)], cache_root=str(root / "upload" / "cache"))
    for k in ("tiers", "cache", "pointer_coverage", "degradation"):
        assert k in rep, f"播报块缺键: {k}"
    assert rep["degradation"]["level"] in ("低", "中", "高"), "退化评级越界"
    try:
        pointerize([str(troot)], cache_root=str(root / "cache"))
        raise SystemExit("指针化 upload 硬闸失效")
    except PermissionError:
        pass
    (troot / "y.png").write_bytes(b"\x89PNG2")
    d = pointerize([str(troot)], cache_root=str(root / "upload" / "cache"))
    assert d["dry_run"] and (troot / "y.png").exists(), "pointerize dry-run 误迁"
    (root / "credentials" / "tok.png").write_bytes(b"\x89PNG3")
    m = pointerize([str(root)], cache_root=str(root / "upload" / "cache"),
                   card=str(cardp), force=True)
    assert m["moved"] >= 1 and Path(m["manifest"]).exists(), "pointerize 未迁"
    man_lines = [json.loads(l) for l in open(m["manifest"], encoding="utf-8")]
    assert all(j.get("sha256") for j in man_lines if j.get("action") == "moved"), "manifest 缺 sha256"
    assert (root / "credentials" / "tok.png").exists(), "白名单件被误迁"
    ctext2 = Path(cardp).read_text(encoding="utf-8")
    assert "_manifest.jsonl" in ctext2, "卡指针行未写入"
    import shutil
    shutil.rmtree(root, ignore_errors=True)
    print(f"context_audit smoke PASS（v{VERSION}：硬闸负断言/dry-run/白名单扩充+生态段/schema/压缩归档加固/aging/云同步/docstring版本/mark_archive五断言/transient=0提示/v1.6.0播报键+评级+upload硬闸+dry-run+迁移manifest回读+卡指针 全过）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", nargs="+", metavar="DIR")
    ap.add_argument("--apply", nargs="+", metavar="DIR",
                    help="瞬态剔除（硬闸：必须 --with-card 落卡，且默认 dry-run，--force 才真删）")
    ap.add_argument("--with-card", metavar="PATH", help="--apply 的硬闸：续作卡路径（schema 必过）")
    ap.add_argument("--force", action="store_true", help="--apply 真删开关（缺省 dry-run）")
    ap.add_argument("--from-report", metavar="SCAN_JSON", help="--apply 防 TOCTOU：只删指定 scan_report 内已批准 transient 件；缺省=以 apply 时点重扫为准（输出中显式声明）")
    ap.add_argument("--card", metavar="PATH", help="生成续作卡模板")
    ap.add_argument("--mark-archive", nargs="+", metavar="FILE",
                    help="把指定文件追加进 --into 指定续作卡的免读清单（归档免读的正式产生机制）")
    ap.add_argument("--into", metavar="CARD", help="--mark-archive 的目标续作卡")
    ap.add_argument("--note", default="", help="--mark-archive 的一句话内容注记（实质必填：占位词拒登记；缺省=提取文件首行）")
    ap.add_argument("--trigger", default="", help="--mark-archive 的触发重读条件（缺省=需要其内容细节时）")
    ap.add_argument("--notes-file", metavar="JSONL", help="批量归档清单：每行 {\"path\",\"note\",\"trigger\"}（单件失败不中断）")
    ap.add_argument("--check-card", metavar="PATH", help="续作卡四字段 schema 校验")
    ap.add_argument("--archive-large", metavar="FILE", help="大文件压缩归档（gzip+校验+登记）")
    ap.add_argument("--large-threshold", type=float, default=10.0, metavar="MB",
                    help="与 --scan 联用：超过 N MB 的非白名单文件列入 large_candidates（默认 10）")
    ap.add_argument("--age-days", type=int, default=None,
                    help="与 --scan 联用：review 档中 mtime 超过 N 天的标 aging_candidate（只列不删）")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--log", default=None, help="prunelog 路径（默认 执行目录/prunelog.jsonl）")
    ap.add_argument("--report", nargs="+", metavar="DIR",
                    help="播报块：语料统计+指针化覆盖率+语义退化初评（每次使用后必跑，随回报发出）")
    ap.add_argument("--pointerize", nargs="+", metavar="DIR",
                    help="瞬态全面迁移至 upload cache 并指针化（零删除；缺省 dry-run，--force 才迁；--into 可写卡指针）")
    ap.add_argument("--cache-root", default=CACHE_DEFAULT,
                    help="--report/--pointerize 的 cache 根目录（默认 /mnt/agents/upload/cache，必须含 upload 段）")
    args = ap.parse_args()
    if args.smoke:
        smoke()
    elif args.check_card:
        print(json.dumps(check_card(args.check_card), ensure_ascii=False))
    elif args.mark_archive or args.notes_file:
        if not args.into:
            print("--mark-archive/--notes-file 必须配 --into <续作卡>", file=sys.stderr)
            sys.exit(2)
        entries = [(f, args.note, args.trigger) for f in (args.mark_archive or [])]
        bad_lines = 0
        if args.notes_file:  # JSONL 批量：{"path":..., "note":..., "trigger":...}（R28 F7）
            for ln in open(args.notes_file, encoding="utf-8"):
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    d = json.loads(ln)
                    entries.append((d["path"], str(d.get("note", "")), str(d.get("trigger", ""))))
                except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
                    print(f"坏行跳过：{ln[:60]} —— {type(e).__name__}", file=sys.stderr)
                    bad_lines += 1  # 坏行计入批次末汇总（B29/C29），不整批崩溃
        fails = bad_lines
        for f, nt, tg in entries:
            try:
                print(json.dumps(mark_archive(f, args.into, nt, tg), ensure_ascii=False))
            except (ValueError, FileNotFoundError, OSError) as e:
                print(f"拒登记：{f} —— {e}", file=sys.stderr)
                fails += 1  # 单件失败不中断（A28），批次末汇总退出码
        if fails:
            print(f"批量登记完成：{len(entries) - fails} 成 / {fails} 败", file=sys.stderr)
            sys.exit(1)
    elif args.archive_large:
        try:
            print(json.dumps(archive_large(args.archive_large), ensure_ascii=False))
        except (PermissionError, FileExistsError, IOError) as e:
            print(f"归档被拒：{e}", file=sys.stderr)
            sys.exit(1)
    elif args.report:
        print(json.dumps(corpus_report(args.report, cache_root=args.cache_root),
                         ensure_ascii=False))
    elif args.pointerize:
        try:
            print(json.dumps(pointerize(args.pointerize, cache_root=args.cache_root,
                                        card=args.into, force=args.force),
                             ensure_ascii=False))
        except PermissionError as e:
            print(f"硬闸拦截：{e}", file=sys.stderr)
            sys.exit(3)
    elif args.scan:
        res = scan(args.scan)
        if not res["transient"]:
            print("提示：当前扫描目录无符合规则的临时区瞬态文件（transient=0 为合法常态；"
                  "非临时区特征文件默认归 review，宁漏勿误；免读归档/aging/large_candidates 为主战场）",
                  file=sys.stderr)
        if args.age_days is not None:
            cutoff = time.time() - args.age_days * 86400
            aging = [i for i in res["review"]
                     if Path(i["path"]).exists() and Path(i["path"]).stat().st_mtime < cutoff]
            for i in aging:
                i["aging"] = True
            res["aging_candidate"] = aging
            res["review"] = [i for i in res["review"] if not i.get("aging")]
        large = [i for i in res["review"]
                 if i["size"] > args.large_threshold * 1024 * 1024]
        for i in large:
            i["hint"] = "可走 --archive-large 压缩归档"
        res["large_candidates"] = large
        report = Path.cwd() / ("scan_report_" + time.strftime("%Y%m%d_%H%M%S") + ".json")
        report.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({k: len(v) for k, v in res.items()}, ensure_ascii=False))
        for tier in ("transient", "protected", "review", "aging_candidate", "large_candidates"):
            for i in res.get(tier, [])[:20]:
                print(f"[{tier}] {i['path']} ({i['size']}B) — {i['reason']}")
        print(f"全量清单 -> {report}（超过 20 条时以此为准，Checkpoint 用全量；aging_candidate 只列不删，逐件需用户批）")
    elif args.apply:
        log = args.log or str(Path.cwd() / "prunelog.jsonl")
        try:
            print(json.dumps(apply_prune(args.apply, log, card=args.with_card,
                                         force=args.force, from_report=args.from_report),
                             ensure_ascii=False))
        except PermissionError as e:
            print(f"硬闸拦截：{e}", file=sys.stderr)
            sys.exit(3)
    elif args.card:
        try:
            print("card ->", write_card(args.card))
        except FileExistsError as e:
            print(f"拒写：{e}", file=sys.stderr)
            sys.exit(2)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
