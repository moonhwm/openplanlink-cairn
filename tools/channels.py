# -*- coding: utf-8 -*-
"""channels.py —— 通道探针与实质调用器（承主权人「纳入…却又不用」之纠正）v1.0.0

通道册：DF-OPS-20261009-CAIRN-01 / -02（端点与实测样本之唯一登记处）
凭据：一律从 %USERPROFILE%\.zcode\workspace\default\a2a-bridge\.env 读取；**零回显、不落盘**。

用法：
  python channels.py probe                 # 各通道 models 级探针（可达性/模型数/时延）
  python channels.py call <channel> <model> "<prompt>" [--max 400]
  channel ∈ {302ai, siliconflow, huawei}
退出码：0 成功；1 全部失败；2 用法/键缺。
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")
ENV = pathlib.Path.home() / ".zcode" / "workspace" / "default" / "a2a-bridge" / ".env"

def env():
    d = {}
    for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d

E = env()
CH = {
    "302ai":       {"base": "https://api.302ai.cn/v1", "key": E.get("AI302_API_KEY", "")},
    "siliconflow": {"base": "https://api.siliconflow.cn/v1", "key": E.get("SILICONFLOW_API_KEY", "")},
    "huawei":      {"base": (E.get("HUAWEI_MAAS_BASE", "") or "https://api.modelarts-maas.com/v1").rstrip("/"), "key": E.get("HUAWEI_MAAS_KEY", "")},
}

def _req(url, key, method="GET", body=None, timeout=40):
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + key)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return "200", round(time.time()-t0, 2), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return str(e.code), round(time.time()-t0, 2), e.read().decode("utf-8", "replace")[:160]
    except Exception as e:
        return "ERR", round(time.time()-t0, 2), str(e)[:100]

def probe():
    ok = 0
    for name, c in CH.items():
        if not c["key"]:
            print("  · %-12s 键缺（跳过）" % name); continue
        st, dt, txt = _req(c["base"] + "/models", c["key"])
        if st == "200":
            try: n = len(json.loads(txt).get("data") or [])
            except Exception: n = -1
            print("  ★ %-12s 200 ｜ %5.2fs ｜ 模型=%d" % (name, dt, n)); ok += 1
        else:
            print("  · %-12s %s ｜ %5.2fs ｜ %s" % (name, st, dt, txt[:70].replace("\n", " ")))
    return 0 if ok else 1

def call(channel, model, prompt, mx=400):
    c = CH.get(channel)
    if not c or not c["key"]:
        print("★ 通道未知或键缺：%s" % channel); return 2
    st, dt, txt = _req(c["base"] + "/chat/completions", c["key"], "POST",
                       {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": mx})
    if st != "200":
        print("★ %s/%s ⇒ %s ｜ %.2fs ｜ %s" % (channel, model, st, dt, txt[:150])); return 1
    j = json.loads(txt); ch = (j.get("choices") or [{}])[0]; msg = ch.get("message") or {}
    body = msg.get("content") or msg.get("reasoning_content") or ""
    print("★ %s/%s ⇒ 200 ｜ %.2fs ｜ finish=%s ｜ usage=%s" % (channel, model, dt, ch.get("finish_reason"), (j.get("usage") or {}).get("total_tokens")))
    print(body)
    return 0

def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    if sys.argv[1] == "probe": return probe()
    if sys.argv[1] == "call" and len(sys.argv) >= 5:
        mx = 400
        if "--max" in sys.argv:
            i = sys.argv.index("--max"); mx = int(sys.argv[i+1])
        return call(sys.argv[2], sys.argv[3], sys.argv[4], mx)
    print(__doc__); return 2

if __name__ == "__main__":
    sys.exit(main())
