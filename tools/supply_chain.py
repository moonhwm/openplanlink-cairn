#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""supply_chain.py —— 第三方组件引入三查：NOTICE 署名 / 密钥扫描 / SBOM 登记。

全局声明口径：引入任何第三方组件前，三项先行，缺一不得引入。
  notice_check(files)  —— NOTICE 署名：第三方组件须有 NOTICE，缺失即报
  secret_scan(files)   —— 密钥扫描：只报命中位置与形态，绝不打印明文
  sbom_register(entry) —— SBOM 登记：名称/版本/许可层/来源，缺项即报
  gate(manifest)       —— 三查汇总门：任一不过 → 该组件"不得引入"
纯标准库。凭据不入库。
"""
import json
import os
import re

# 密钥形态（只识别形态、不打印值）
SECRET_PATTERNS = [
    ("sk-", r"sk-[A-Za-z0-9\-_]{16,}"),
    ("sb_publishable_", r"sb_publishable_[A-Za-z0-9\-_]{16,}"),
    ("Bearer ", r"Bearer\s+[A-Za-z0-9\-_\.]{16,}"),
    ("私钥头", r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]

# 许可层映射（复用 compliance_check 五层口径；此处内置一份防循环依赖）
LAYER = {
    "code": "AGPL-3.0", "server-stack": "SSPL-1.0",
    "docs": "CC-BY-SA-4.0", "dataset": "ODbL-1.0",
    "governance": "不进许可体系",
}


def notice_check(files):
    """NOTICE 署名检查：第三方组件须有 NOTICE 文件或署名条目。空文件清单=缺署名。"""
    if not files:
        return {"ok": False, "missing": ["<无文件清单=无NOTICE署名>"]}
    missing = []
    for f in files:
        ok = False
        if os.path.exists(f):
            with open(f, encoding="utf-8", errors="ignore") as fh:
                content = fh.read(65536)
                ok = ("NOTICE" in content) or ("署名" in content)
        if not ok:
            missing.append(os.path.basename(f))
    return {"ok": not missing, "missing": missing}


def secret_scan(files):
    """密钥扫描：只报（文件名, 形态）不打印明文。"""
    hits = []
    for f in files:
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8", errors="ignore") as fh:
            content = fh.read(262144)
        for label, pat in SECRET_PATTERNS:
            if re.search(pat, content):
                hits.append({"file": os.path.basename(f), "pattern": label})
    return {"ok": not hits, "hits": hits}


def sbom_register(entry):
    """SBOM 登记：名称/版本/许可层/来源 缺一即报。"""
    missing = [k for k in ("name", "version", "license_layer", "source") if not entry.get(k)]
    return {"ok": not missing, "missing": missing, "entry": entry}


def gate(manifest):
    """第三方组件引入门：三查汇总，任一不过 → 不得引入。"""
    report = []
    for item in manifest.get("components", []):
        files = item.get("files", [])
        r1 = notice_check(files)
        r2 = secret_scan(files)
        r3 = sbom_register(item)
        ok = r1["ok"] and r2["ok"] and r3["ok"]
        report.append({"component": item.get("name"), "ok": ok,
                       "notice": r1, "secret": r2, "sbom": r3,
                       "verdict": "可引入" if ok else "不得引入"})
    ok_all = all(r["ok"] for r in report)
    return {"ok": ok_all, "report": report}


if __name__ == "__main__":
    sample = {"components": [
        {"name": "demo-lib", "version": "1.0", "license_layer": "AGPL-3.0",
         "source": "gitcode.com/demo", "files": []},
    ]}
    r = gate(sample)
    print("  三查门(缺NOTICE/无文件) =", r["report"][0]["verdict"])
    print("  secret_scan 自检 =", secret_scan([__file__])["ok"], "(本模块无密钥)")
    # 补 NOTICE 后
    with open(r"C:\Users\欧阳宏俊\.supply_tmp_NOTICE.txt", "w", encoding="utf-8") as f:
        f.write("NOTICE: demo-lib (c) demo")
    sample["components"][0]["files"] = [r"C:\Users\欧阳宏俊\.supply_tmp_NOTICE.txt"]
    r2 = gate(sample)
    print("  补NOTICE后 =", r2["report"][0]["verdict"])
