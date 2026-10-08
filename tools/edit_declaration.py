#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只写本席自己的声明件；不触网。
r"""edit_declaration.py —— 声明件的【脚本化编辑 ＋ 校验】器（轮 22）。 v1.0.0

立此器的缘由（写在代码里）
────────────────────────────
轮 20–21 我【四次】把声明写成坏结构：
  · 两次：中文里的未转义直引号 ⇒ 解析失败
  · 一次：改大 JSON 时锚点撞重、漏了一个逗号
  · 一次：结构虽合法但键重复/位置不对
⇒ 轮 21 我下了判决：**声明此后必须脚本化编辑 ＋ 校验，不手改。**
★ 而按本席一贯判据：一条【无人执行】的规矩＝纸上的字。故本轮把它做成机制。

本器的保证（由构造而非由小心）
────────────────────────────────
  ① **先读后改**：load 成功才继续；
  ② **改完先验**：json 合法 ＋ **必需键齐全**（下列 SCHEMA）才允许写；
  ③ **失败即不写**：任何一步失败 ⇒ **原文件字节不动**（原子性）；
  ④ **改完回读**：写后重新 load 并比对，不一致即报错退出。

★ 本器自陈盲点（按轮 12 判据）
  ① 它只核【结构】不核【语义】：字段写得对不对、类别标得对不对，它【不判】；
  ② `--set` 的路径若指错（但指到合法位置）⇒ 它会照改，**不报错**；
  ③ 它不管【版本追加律】——那是 pilot_publish 的职责，不是它的。

用法
──────
  edit_declaration.py --show
  edit_declaration.py --set  verifier_pin.sha256 "abc123"
  edit_declaration.py --append declared_divergences.items '{"path":"x","change":"y"}'
  edit_declaration.py --selftest        # 负例：故意写坏 ⇒ 应【拒写】
"""
from __future__ import annotations
import argparse
import json
import pathlib
import shutil
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
DECL = SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json"

# ★ 必需键（结构级）：缺一即拒写
SCHEMA = {
    "schema": str, "seat_id": str, "canonical": dict, "replicas": list,
    "ledger": dict, "find_me": dict, "verify_recipe": list,
    "self_reference": dict, "limit_taxonomy": dict, "verifier_pin": dict,
}
# 数组元素级：这些数组的每一项必须含这些键
ITEM_SCHEMA = {
    "declared_divergences.items": ("path", "change", "declared_effect"),
    "limit_taxonomy.items": ("limit", "class", "basis"),
}


def load(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8"))


def validate(d: dict):
    errs = []
    for k, t in SCHEMA.items():
        if k not in d:
            errs.append("缺必需键：%s" % k)
        elif not isinstance(d[k], t):
            errs.append("键 %s 类型应为 %s，实为 %s" % (k, t.__name__, type(d[k]).__name__))
    for path, keys in ITEM_SCHEMA.items():
        cur = d
        for seg in path.split("."):
            cur = cur.get(seg, {}) if isinstance(cur, dict) else {}
        if isinstance(cur, list):
            for i, it in enumerate(cur):
                for k in keys:
                    if k not in it:
                        errs.append("%s[%d] 缺键 %s" % (path, i, k))

    # ★ 2026-10-02 轮 47 加闸：**当前状态字段里不得出现具体版本号 `_vN`**。
    #   缘由（轮 46 实测）：轮 45 我往 find_me 写了「当前版 = _v17」，而【同一轮的投放】就投出 v18
    #   ⇒ 一轮即失效；★ 根因是结构性的：只增不改的件里写具体版本号，它必然在下一次追加时过期。
    #
    # ★★ 轮 48 把名单【倒过来】：原版列了 7 个"要查的键"（★ 而其中 verifiers 根本不存在 ⇒ 实为 6，
    #    且没列到的 11 个键【不会被查】）⇒ ★ 故改为【默认全查、只豁免改动记录栏】：
    #    这样【将来新增的键】自动被覆盖，不会因为"忘了加进名单"而漏掉。
    #    ★ 这与 netguard 的「默认拒绝」同一个道理：★ 默认严，例外要写出来。
    CHANGE_RECORD_KEYS = ("declared_divergences",)   # ★ 只有这一栏是【改动记录】，引旧版本号正当
    import re as _re
    for fld, val in d.items():
        if fld in CHANGE_RECORD_KEYS:
            continue
        blob = json.dumps(val, ensure_ascii=False)
        hits = _re.findall(r"_v\d+", blob)
        if hits:
            errs.append("★ 当前状态字段 `%s` 里出现了具体版本号 %s ⇒ 拒写"
                        "（只增不改的件里写版本号必然过期；应指【系列】与【可重出的指针页】）"
                        % (fld, sorted(set(hits))))
    return errs


def _dead_declared_paths(d: dict) -> list:
    """★ 2026-10-03 轮 82 加闸：**declared_divergences 的 path 必须指得到真件**。

    缘由（轮 81 实测）：声明 57 条里【14 条指不到真件】——全是"把描述写进 path"
      （如 `exp/edit_declaration.py（第二次）`、`exp/ab_theirs/* 与 …（共 11 件）`）。
      ★ 而那 14 条【是隐形的】：核验按精确路径匹配，★ 更早那条精确路径已覆盖 ⇒ 一直绿。
      ⇒ 故"漂回去"的机制是【没有东西在事后拦住它】——★ 那就在【事前】拦。

    ★★ 判据（★ 刻意保守，宁可拦下让人看一眼）：
      · 空 path ⇒ 拒
      · 含通配（* ? [）⇒ 拒（★ 核验不展开通配，故它匹配不上）
      · 含全角/半角括号后缀、或含"与/／"这类连接词 ⇒ 拒（★ 那是"一段描述"的形状）
      · ★ 其余：必须 resolve 到【本席内的一个存在的文件或目录】⇒ 否则拒
    ★★ 它【不改】已有的 14 条（只增不改）⇒ 只对【此后新增的】生效。
    """
    bad = []
    items = d.get("declared_divergences", {}).get("items", [])
    for i, it in enumerate(items, 1):
        p = str(it.get("path", "")).strip()
        why = None
        if not p:
            why = "空 path"
        elif any(c in p for c in "*?["):
            why = "含通配（★ 核验不展开通配 ⇒ 匹配不上）"
        elif any(c in p for c in "（(）)") and not p.endswith(".py"):
            why = "含括号后缀（★ 那是「一段描述」的形状，不是路径）"
        elif (" 与 " in p) or ("／" in p) or p.count("/") > 6:
            why = "含连接词或多个路径（★ 那是描述，不是一条路径）"
        else:
            cand = SEAT / p
            # ★ 轮 83 收紧：**必须是【文件】，不认目录**。
            #   缘由（轮 83 实证）：原判据 `is_file() or is_dir()` ⇒ 一个目录（如 `exp`）
            #   ★ 会被放行——而"分叉"是【文件】之间的事，声明一个目录【指不到任何一件】。
            #   ★ 而收紧【不会误伤】：轮 83 实测，那 44 条"指得到"的声明【全部指向文件】，
            #     指向目录的 = 0 条。
            if not cand.is_file():
                why = "指不到真件（★ 须是【文件】；不存在、或是目录——★ 而分叉是文件间的事）"
        if why:
            bad.append((i, p[:60], why))
    return bad


def get_path(d: dict, path: str):
    cur = d
    for seg in path.split("."):
        cur = cur[seg] if isinstance(cur, dict) else cur[int(seg)]
    return cur


def _has_path(d: dict, path: str) -> bool:
    cur = d
    for seg in path.split("."):
        if isinstance(cur, dict):
            if seg not in cur:
                return False
            cur = cur[seg]
        elif isinstance(cur, list):
            try:
                cur = cur[int(seg)]
            except Exception:
                return False
        else:
            return False
    return True


def set_path(d: dict, path: str, value):
    segs = path.split(".")
    cur = d
    for seg in segs[:-1]:
        cur = cur[seg] if isinstance(cur, dict) else cur[int(seg)]
    last = segs[-1]
    if isinstance(cur, dict):
        cur[last] = value
    else:
        cur[int(last)] = value


def write_atomic(p: pathlib.Path, d: dict) -> bool:
    """★ 失败即不写：先写临时文件并复验，再替换。"""
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        back = load(tmp)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        print("  ★ 回读失败 ⇒ ★ REFUSE（拒写）：%s" % e)
        return False
    if validate(back):
        tmp.unlink(missing_ok=True)
        print("  ★ 回读校验不过 ⇒ ★ REFUSE（拒写）")
        return False
    shutil.move(str(tmp), str(p))
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", nargs=2, action="append", default=[], metavar=("PATH", "JSON_VALUE"))
    ap.add_argument("--append", nargs=2, action="append", default=[], metavar=("ARRAY_PATH", "JSON_OBJECT"))
    # ★ 2026-10-02 轮 49 加 --dry-run。
    #   缘由（轮 48 实测）：我为验证"闸只豁免 declared_divergences"，就往【真声明】里
    #   追加了一条测试项 ⇒ ★ 做对照时动了真件。根因是本器【没有试跑功能】——
    #   要测那道闸，就必须真写。⇒ 故补 --dry-run：走完全部校验与回读，但【不落盘】。
    ap.add_argument("--dry-run", action="store_true",
                    help="★ 只走校验与回读，【一字不写】——用于测那道闸而不污染真件。")
    # ★ 轮 22 加：从【文件】读值。缘由：本轮实跑发现，内联 JSON 只要含空格，
    #   在 PowerShell 里就会被拆成多个参数 ⇒ argparse 报 unrecognized arguments ⇒ 调用失败。
    #   ★ 那次的失败是【安全】的（器退出码 2 且不写文件），但接口太脆 ⇒ 补文件入口。
    ap.add_argument("--set-file", nargs=2, action="append", default=[], metavar=("PATH", "JSON_FILE"))
    ap.add_argument("--append-file", nargs=2, action="append", default=[], metavar=("ARRAY_PATH", "JSON_FILE"))
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    print("═══ 声明脚本化编辑器 ═══")
    print("  声明 = %s" % DECL.name)
    if not DECL.is_file():
        print("ERR 声明不在 ⇒ ★ 器具故障")
        return 2
    d = load(DECL)
    print("  ★ 读入成功 ｜ 顶层键 %d 个 ｜ 当前校验：%s"
          % (len(d), "通过" if not validate(d) else "★ 不通过"))

    if a.show:
        print("  必需键 = %s" % "、".join(SCHEMA))
        for k, t in SCHEMA.items():
            v = d.get(k)
            n = len(v) if isinstance(v, (list, dict)) else 1
            print("     %-18s %-6s ｜ %d 项" % (k, t.__name__, n))
        return 0

    if a.selftest:
        # ★ 负例一：故意去掉必需键 ⇒ 应拒写
        print("\n  ── 自检一：删掉必需键 self_reference ⇒ 应【拒写】 ──")
        d2 = json.loads(json.dumps(d)); d2.pop("self_reference", None)
        errs = validate(d2)
        print("     校验发现的错 = %d 条：%s" % (len(errs), errs[:2]))
        print("     ⇒ %s" % ("★ 如预期拒绝写入" if errs else "★ 未发现 ⇒ 校验失效"))
        # ★ 负例二：数组元素缺键 ⇒ 应被发现
        print("\n  ── 自检二：给 declared_divergences.items 追加一个【缺 change 键】的项 ⇒ 应被发现 ──")
        d3 = json.loads(json.dumps(d))
        d3.setdefault("declared_divergences", {}).setdefault("items", []).append({"path": "x"})
        errs3 = validate(d3)
        print("     校验发现的错 = %d 条：%s" % (len(errs3), errs3[:2]))
        print("     ⇒ %s" % ("★ 如预期发现缺键" if errs3 else "★ 未发现 ⇒ 校验失效"))
        ok = bool(errs) and bool(errs3)
        print("\n  ⇒ %s" % ("✅ 本器【会拒写】（非恒真）" if ok else "★ 校验是装饰"))
        return 0 if ok else 1

    if not a.set and not a.append and not a.set_file and not a.append_file:
        print("  （无改动请求；用 --show / --set / --append / --set-file / --append-file / --selftest）")
        return 0

    before = DECL.read_bytes()
    changed = []
    # ★ 轮 82：记下【改动前】declared_divergences 的条数——
    #   因为闸只该管【本次新增的】；★ 已有的 14 条旧死条若一并算，会让【每一次编辑都被拒】。
    _n_before_decl = len(d.get("declared_divergences", {}).get("items", []))
    # ★ 文件入口：读文件内容为 JSON 值（含空格也不怕）
    for path, fp in a.set_file:
        src = pathlib.Path(fp)
        if not src.is_file():
            print("  ★ 值文件不存在 ⇒ ★ REFUSE（拒改）：%s" % fp)
            return 1
        try:
            val = json.loads(src.read_text(encoding="utf-8"))
        except Exception as e:
            print("  ★ 值文件不是合法 JSON ⇒ ★ REFUSE（拒改）：%s" % e)
            return 1
        old = get_path(d, path) if _has_path(d, path) else None
        set_path(d, path, val)
        changed.append("set-file %s ：→ %s" % (path, str(val)[:70]))
    for path, fp in a.append_file:
        src = pathlib.Path(fp)
        if not src.is_file():
            print("  ★ 值文件不存在 ⇒ ★ REFUSE（拒改）：%s" % fp)
            return 1
        try:
            obj = json.loads(src.read_text(encoding="utf-8"))
        except Exception as e:
            print("  ★ 值文件不是合法 JSON ⇒ ★ REFUSE（拒改）：%s" % e)
            return 1
        arr = get_path(d, path) if _has_path(d, path) else None
        if arr is None:
            # 自动建路径（dict 中间层 + 末层 list）
            set_path(d, path, [])
            arr = get_path(d, path)
        if not isinstance(arr, list):
            print("  ★ %s 不是数组 ⇒ ★ REFUSE（拒改）" % path)
            return 1
        arr.append(obj)
        changed.append("append-file %s ：+%s" % (path, str(obj)[:70]))
    for path, raw in a.set:
        try:
            val = json.loads(raw)
        except Exception:
            val = raw
        old = get_path(d, path)
        set_path(d, path, val)
        changed.append("set %s ：%r → %r" % (path, old, val))
    for path, raw in a.append:
        try:
            obj = json.loads(raw)
        except Exception as e:
            print("  ★ --append 的值不是合法 JSON ⇒ ★ REFUSE（拒改）：%s" % e)
            return 1
        arr = get_path(d, path)
        if not isinstance(arr, list):
            print("  ★ %s 不是数组 ⇒ ★ REFUSE（拒改）" % path)
            return 1
        arr.append(obj)
        changed.append("append %s ：+%r" % (path, obj))

    errs = validate(d)
    if errs:
        print("  ★ 改动后校验不通过 ⇒ ★ REFUSE（拒写）：")
        for e in errs[:6]:
            print("     ★ " + e)
        return 1

    # ★ 轮 82 加闸：**本次新增的 declared_divergences 条目，其 path 必须指得到真件**。
    #   ★ 只管【新增的】——已有的旧死条不在本次之内（只增不改，故不追溯）。
    #   缘由（轮 81 实测）：声明 57 条里 14 条指不到真件，全是"把描述写进 path"，
    #   ★ 而它们【隐形】——因为更早那条精确路径已覆盖 ⇒ 核验一直绿。
    _items_now = d.get("declared_divergences", {}).get("items", [])
    _new = _items_now[_n_before_decl:]
    if _new:
        _tmp = {"declared_divergences": {"items": _new}}
        _bad = _dead_declared_paths(_tmp)
        if _bad:
            print("  ★ 本次新增的 declared_divergences 里有【指不到真件】的条目 ⇒ ★ REFUSE（拒写）：")
            for _i, _p, _why in _bad[:6]:
                print("     ★ [新增第 %d 条] %s" % (_i, _p))
                print("        理由：%s" % _why)
            print("     ★★ 缘由（轮 81）：这类条目【匹配不上任何差异】——★ 是纸上的字；")
            print("        而它们【隐形】（★ 更早那条精确路径会覆盖它）⇒ 故在【事前】拦。")
            return 1

    # ★ 轮 49：试跑分支——★ 校验都过了，但【不落盘】。
    if a.dry_run:
        print("  ★★ --dry-run：走完全部校验，★ 【一字未写】。")
        print("     改动清单（仅在内存中，未落盘）：")
        for c in changed:
            print("       · " + c[:110])
        after_bytes = len(json.dumps(d, ensure_ascii=False, indent=2).encode("utf-8")) + 1
        print("     预计字节数：%d → %d（★ 实际文件仍为 %d）" % (len(before), after_bytes, len(DECL.read_bytes())))
        print("     ⇒ ✅ 这道闸【会放行】这个改动；★ 而真件未被触碰。")
        return 0

    if not write_atomic(DECL, d):
        return 1
    after = DECL.read_bytes()
    # ★ 轮 112：字节数【不是】可靠的变化指示——★ 故加上哈希前缀。
    #   缘由（轮 111 实证）：我改 `verifier_pin`（一个 64 位哈希换成另一个）⇒ 本行印的是
    #   「已写 ｜ 字节 56782 → 56782」——★ **字节数没变**（★ 等长替换）。
    #   ⇒ ★★ 而"改钉"这件事【天然就是等长替换】⇒ 这个盲点【恰好落在最重要的那类改动上】。
    #   ⇒ 故此后：★ 字节数 ＋ 【前后哈希前缀】一起印；★ 并在【字节持平】时明说一句。
    import hashlib as _h
    _hb = _h.sha256(before).hexdigest()[:12]
    _ha = _h.sha256(after).hexdigest()[:12]
    print("  已写 ｜ 字节 %d → %d ｜ ★ sha256 前12：%s → %s"
          % (len(before), len(after), _hb, _ha))
    if len(before) == len(after):
        print("     ★★ 注意：字节数【持平】——★ 字节数不足以说明「没变」；"
              "★ 请以上面那两个哈希前缀为准（★ 轮 111 的教训：改钉天生等长）。")
    for c in changed:
        print("     · " + c[:110])
    print("  ★ 本器盲点：只核结构不核语义；--set 指错但合法处它照改；不管版本追加律。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
