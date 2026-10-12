# -*- coding: utf-8 -*-
"""计费面勘察：①账户余额 ②可购资源包/券 ③欠费状态（★ 凭据自 CSV 读取，零回显）
★ 目的：判"买何种抵扣券能解决哪一类不通"（429 额度／403 应用资格）
（引号一律用「」）
"""
import json, pathlib, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from aliyun_api import call  # noqa: E402

DESK = pathlib.Path.home()/"OneDrive"/"桌面"
def ak(fn):
    p = (DESK/fn).read_text(encoding="utf-8-sig", errors="replace").splitlines()[1].split(",")
    return p[0].strip(), p[1].strip()
MAIN = ak("AccessKey 阿里云百炼主账户.csv")
print("  凭据：主账户 AK …%s（值不外显）" % MAIN[0][-4:])

HOSTS = ["bssopenapi.aliyuncs.com", "business.aliyuncs.com", "bss.aliyuncs.com"]

def q(host, act, ver, extra, tag, tries=2):
    params = {"Action": act, "Version": ver}; params.update(extra)
    for i in range(tries):
        st, tx = call(MAIN[0], MAIN[1], host, params, timeout=35)
        if st != -1: break
        time.sleep(3)
    brief = ""
    try:
        j = json.loads(tx)
        for k in ("Data", "Code", "Message"):
            if k in j:
                v = j[k]
                brief = ("%s=%s" % (k, json.dumps(v, ensure_ascii=False)[:150])) if isinstance(v, (dict, list)) else ("%s=%s" % (k, v))
                if k == "Code": break
        if not brief: brief = json.dumps(j, ensure_ascii=False)[:170]
    except Exception:
        brief = tx[:150]
    print("   %-34s %-26s ⇒ HTTP %-5s ｜ %s" % (act, host.split(".")[0], st, brief))

print("\n  === ① 账户余额（三域名轮试）===")
for h in HOSTS:
    q(h, "QueryAccountBalance", "2017-12-14", {}, "余额")
print("\n  === ② 欠费/账期状态 ===")
q("bssopenapi.aliyuncs.com", "QueryAccountTransactions", "2017-12-14", {"PageSize": "5"}, "流水")
q("bssopenapi.aliyuncs.com", "DescribeResourcePackageProduct", "2017-12-14", {"ProductCode": "sfm"}, "资源包(sfm)")
q("bssopenapi.aliyuncs.com", "QueryProductList", "2017-12-14", {"PageSize": "20", "QueryTotalCount": "true"}, "产品清单")
print("\n  === ③ 百炼产品之物化标识（判产品码）===")
for code in ("sfm", "bailian", "dashscope", "lingji", "aimodel"):
    q("bssopenapi.aliyuncs.com", "QueryAvailableInstances", "2017-12-14", {"ProductCode": code}, "可用实例(%s)" % code, tries=1)
print("\n  ⇒ 注：若三域名皆不可达，本席即报「计费面不可达」（须控制台），不臆断余额")
