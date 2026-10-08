# -*- coding: utf-8 -*-
"""世界模型（HappyOyster）运行器 —— **待 WorkspaceId 即可执行**
- 支持 Adventure（世界探索）与 Directing（实时导演，simple／scriptlist 两子模式）
- 首帧图：本席自绘 PNG ⇒ 运行时转 base64 data URI（无需外网托管）
- 凭据：仅从 a2a-bridge/.env 读 DASHSCOPE_API_KEY；**不打印任何凭据**
- 用法：
    python world_model_runner.py --workspace <WorkspaceId> --mode adventure   [--region cn-beijing]
    python world_model_runner.py --workspace <WorkspaceId> --mode directing --submode simple [--dry-run]
  说明：--dry-run 只打印请求形状（截断 base64），不发请求。
"""
import argparse, base64, json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
PNG = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A新席_石敢当Cairn_20260928" / "exp" / "firstframe_night_playground_20261009.png"

def key():
    p = HOME / ".zcode" / "workspace" / "default" / "a2a-bridge" / ".env"
    d = {}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("="); d[k.strip()] = v.strip().strip('"').strip("'")
    return d.get("DASHSCOPE_API_KEY", "")

def firstframe_data_uri():
    b = PNG.read_bytes()
    return "data:image/png;base64," + base64.b64encode(b).decode()

def build(mode, submode):
    """Adventure：必填 perspective＋prompt＋firstFrameImage
       Directing(simple)：必填 prompt＋resolution；firstFrameImage 可选
       Directing(scriptlist)：必填 resolution＋firstFrameImage＋scriptList(synopsis,acts)"""
    if mode == "adventure":
        return "/api/v2/apps/happyoyster-1.0-adventure/openapi/v1/worlds", {
            "async": True,
            "perspective": "third_person",
            "prompt": ("夜间游乐场：一座由文档塔与光带构成的开放世界。无数发光的纸页沿轨道滑行，"
                       "中央是一座旋转的灯轮；远景是数据河流与星群，近景有可辨认的席位印记与通道门。"
                       "冷冽夜色，暖黄灯光，开阔而神秘。"),
            "firstFrameImage": {"base64": firstframe_data_uri()},
        }
    if submode == "scriptlist":
        return "/api/v2/apps/happyoyster-1.0-directing/openapi/v1/worlds", {
            "async": True, "creationModel": "scriptlist", "resolution": "720p",
            "firstFrameImage": {"base64": firstframe_data_uri()},
            "scriptList": {
                "videoTitle": "夜间游乐场：一次元处理巡场",
                "synopsis": "在夜间开园的游乐场里，一枚只读镜片沿光带巡场，记录文档塔、通道门与席位印记。",
                "language": "zh", "scene": "夜间的开放式游乐场", "style": "Stable", "speed": "Steady",
                "subjects": [{"label": "[character_1]", "name": "只读镜片", "type": "narrator",
                              "voice": "冷静、平稳、语速适中"}],
                "acts": [
                    {"turn": 1, "content": "镜头掠过成排文档塔，纸页在光带上有序滑行。",
                     "cameraType": "Tracking", "shotSize": "Wide", "cut": "long-take"},
                    {"turn": 2, "content": "一枚只读镜片浮现，映出塔身上可辨认的档号印记。",
                     "cameraType": "Push-in", "shotSize": "Close-up", "cut": "cut-in"},
                    {"turn": 3, "content": "镜片转向通道门，门后是本夜新开的四条通路微光。",
                     "cameraType": "Pan Right", "shotSize": "Medium", "cut": "cut-out"},
                ],
            },
        }
    return "/api/v2/apps/happyoyster-1.0-directing/openapi/v1/worlds", {
        "async": True, "creationModel": "simple", "resolution": "720p",
        "eventStyle": "normal", "layout": "Calm", "narrative": "Calm",
        "prompt": ("夜间游乐场，第三人称。镜头缓缓穿过文档塔与光带，最终停在一枚只读镜片前；"
                   "温暖灯光与冷色夜景对比，安静、开阔、有秩序感。"),
        "firstFrameImage": {"base64": firstframe_data_uri()},
    }

def post(url, body, k, timeout=60):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + k); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, round(time.time()-t0, 2), json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        b = e.read().decode("utf-8", "replace")
        return e.code, round(time.time()-t0, 2), b[:300]
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:160]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True, help="百炼 Workspace ID（自控制台取得）")
    ap.add_argument("--region", default="cn-beijing")
    ap.add_argument("--mode", choices=["adventure", "directing"], required=True)
    ap.add_argument("--submode", choices=["simple", "scriptlist"], default="simple")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    path, body = build(a.mode, a.submode)
    url = "https://%s.%s.maas.aliyuncs.com%s" % (a.workspace, a.region, path)
    print("  端点：%s" % url)
    print("  模式：%s%s ｜ 首帧图：%s（%.1f KB）" % (a.mode, ("/" + a.submode) if a.mode == "directing" else "",
                                                 PNG.name, PNG.stat().st_size/1024))
    shape = json.loads(json.dumps(body))
    for kk in ("firstFrameImage",):
        if kk in shape and "base64" in shape[kk]:
            shape[kk]["base64"] = shape[kk]["base64"][:48] + "…<base64 截断>"
    print("  请求形状：%s" % json.dumps(shape, ensure_ascii=False)[:700])
    if a.dry_run:
        print("  （dry-run：未发请求）"); return 0
    k = key()
    if not k:
        print("  × 无键（DASHSCOPE_API_KEY 缺失）"); return 2
    st, dt, j = post(url, body, k)
    print("  ⇒ HTTP %s ｜ %.2fs" % (st, dt))
    if isinstance(j, dict):
        d = j.get("data") or {}
        print("  code=%s ｜ message=%s" % (j.get("code"), j.get("message")))
        if d:
            print("  encryptedWorldId=%s ｜ status=%s" % (str(d.get("encryptedWorldId"))[:14] + "…", d.get("status")))
    else:
        print("  %s" % str(j)[:220])
    return 0

if __name__ == "__main__":
    sys.exit(main())
