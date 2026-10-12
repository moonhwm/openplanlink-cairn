# -*- coding: utf-8 -*-
"""kj38.py —— 由备份恢复 directing_approx_run.py，再以「整行替换」修落盘名（2026-10-13）
缘由：kj37 之两处改动中，第二处（落盘名）以片段替换改坏了 r"..." 原始字符串 ⇒ SyntaxError（L80）。
      ★自纠三十三：改原始字符串内之文件名须整体重写该行。
本补丁：
  ① 由 exp/_patch_backup_<日期>/directing_approx_run.py 恢复（★确保干净起点）
  ② 重放第一处（chat() 改 302＋百炼回退）
  ③ 以「整行替换」修落盘名：★把整个 p = pathlib.Path(...) 行换为动态日期版
  ④ 编译 + 印认 + 实跑（★在输出中确认走 302）
（中文串一律用「」）
"""
import pathlib, re, shutil, sys, time, py_compile, subprocess

SEAT = pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
P = SEAT/"exp"/"directing_approx_run.py"
BAK = SEAT/"exp"/("_patch_backup_%s" % time.strftime("%Y%m%d"))/P.name

if BAK.exists():
    shutil.copy2(BAK, P)
    print("  ✓ 已由备份恢复（%s）" % BAK.parent.name)
else:
    print("  ★备份不在 ⇒ 用当前文件（继续）")

t = P.read_text(encoding="utf-8")

NEW_CHAT = '''RL = "https://api.302ai.cn/v1/chat/completions"      # ★302.AI（承 -1439：三模块全通）
K2 = env.get("AI302_API_KEY", "")
DS = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"   # ★百炼（备用；已欠费）


def _once(url, key, model, prompt, mx, to):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": mx}
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + key); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
            ch = (j.get("choices") or [{}])[0]
            return str((ch.get("message") or {}).get("content") or "").strip(), round(time.time()-t0, 2), (j.get("usage") or {})
    except urllib.error.HTTPError as e:
        return "", round(time.time()-t0, 2), "HTTP %s %s" % (e.code, e.read().decode("utf-8","replace")[:120])
    except Exception as e:
        return "", round(time.time()-t0, 2), str(e)[:100]


def chat(model, prompt, mx=900, to=120):
    """★先 302.AI（gpt-5），失败则回退百炼（原模型）"""
    if K2:
        out, dt, tk = _once(RL, K2, "gpt-5", prompt, mx, to)
        if out:
            print("    ★承 302.AI（gpt-5）")
            return out, dt, tk
        print("    ★302.AI 未成（%s）⇒ 回退百炼 %s" % (str(tk)[:60], model))
    return _once(DS, K, model, prompt, mx, to)
'''
n = 0
m = re.search(r'def chat\(model, prompt, mx=900, to=120\):.*?\n\n', t, re.S)
if m and "302.AI 未成" not in t:
    t = t[:m.start()] + NEW_CHAT + "\n" + t[m.end():]
    n += 1

# ★整行替换落盘名（★自纠三十三：不动 r"..." 之内片段，改整行）
pat = re.compile(r'^(\s*)p = pathlib\.Path\(r".*?\)\s*$', re.M)
NEWLINE = ('    p = pathlib.Path(r"C:\\Users\\欧阳宏俊\\WPSDrive\\29969771\\WPS云盘\\月之暗面的Plasma游乐场'
           '\\A2A共同体_共享交换区") / ("directing_approx_%s.json" % time.strftime("%Y%m%d"))')
if pat.search(t):
    # ★自纠三十四：re.sub 之 replacement 含 Windows 路径（\U 等）会被当逃逸 ⇒ ★用函数式替换
    t = pat.sub(lambda _m: NEWLINE, t, count=1)
    n += 1

bak2 = SEAT/"exp"/("_patch_backup_%s" % time.strftime("%Y%m%d"))
bak2.mkdir(parents=True, exist_ok=True)
shutil.copy2(P, bak2/(P.stem + "_pre_kj38.py"))
P.write_text(t, encoding="utf-8", newline="\n")
print("  ✓ 已改 %d 处（备份 pre_kj38）" % n)

try:
    py_compile.compile(str(P), doraise=True)
    print("   ★编译 ✓")
except Exception as ex:
    print("   ★编译 ✗：")
    for l in str(ex).splitlines()[:6]:
        print("      " + l[:110])
    sys.exit(1)

lines = P.read_text(encoding="utf-8").splitlines()
for i, l in enumerate(lines, 1):
    if "302.AI 未成" in l or "directing_approx_%s" in l or l.strip().startswith("RL = "):
        print("   ★L%-4d ｜ %s" % (i, l.strip()[:94]))

print("  ═══ 实跑（★应见「承 302.AI（gpt-5）」）═══")
r = subprocess.run([sys.executable, str(P)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
print((r.stdout or "")[:1600])
if r.returncode != 0:
    print("   ★rc=%s ｜ %s" % (r.returncode, (r.stderr or "")[:200]))
