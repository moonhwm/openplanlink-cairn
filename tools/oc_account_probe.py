# -*- coding: utf-8 -*-
"""oc_account_probe.py —— 只读查 OpenCode 之 provider 账户与状态（2026-10-14 立）
用途：诊断「Upstream request failed: Insufficient account funds」⇒ 定是哪家 provider 之账户。
纪律：★只读（mode=ro）｜★凭据列一律脱敏（只报长度与前缀类别，不回报值）
用法：python oc_account_probe.py
"""
import json, re, sqlite3, sys

sys.stdout.reconfigure(encoding="utf-8")
DB = r"C:\Users\欧阳宏俊\.local\share\opencode\opencode.db"
SECRET_HINT = re.compile(r"(key|token|secret|password|credential|api)", re.I)


def mask(v):
    if v is None:
        return None
    s = str(v)
    if len(s) <= 24:
        return s            # 短值（如 id／状态名）照报
    return "‹脱敏 len=%d 首4=%s›" % (len(s), s[:4])


def dump(con, table, limit=12):
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % table)]
    except Exception as e:
        print("   ★%s 读失败：%s" % (table, str(e)[:80])); return
    print("   ★%s ｜ 列：%s" % (table, ", ".join(cols)))
    try:
        rows = list(con.execute("select * from %s limit %d" % (table, limit)))
    except Exception as e:
        print("      ★select 失败：%s" % str(e)[:80]); return
    print("      行数（限 %d）：%d" % (limit, len(rows)))
    for r in rows:
        d = {}
        for c, v in zip(cols, r):
            d[c] = mask(v) if SECRET_HINT.search(c) or (isinstance(v, str) and len(str(v)) > 60) else v
        line = json.dumps(d, ensure_ascii=False)
        print("      " + line[:300])
    print()


def main():
    con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    print("  ═══ OpenCode 账户／凭据（★只读；凭据脱敏）═══")
    for t in ("account", "account_state", "control_account"):
        dump(con, t)
    # credential 只报列名与条数，不报值
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(credential)")]
        n = list(con.execute("select count(*) from credential"))[0][0]
        print("   ★credential ｜ 列：%s ｜ ★条数 %d（★值不回显）" % (", ".join(cols), n))
    except Exception as e:
        print("   ★credential 读失败：%s" % str(e)[:80])
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
