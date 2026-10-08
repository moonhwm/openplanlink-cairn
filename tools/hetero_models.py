#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""hetero_models.py —— 异质模型接入（硅基流动主力 / 302.AI 补闭源 / 国家超算定向）。

凭据从本地 .hetero-model-keys.env 读（安全红线：key 不入仓、不入代码）。
硅基流动 = OpenAI 兼容（api.siliconflow.cn/v1），免费模型兜底（Qwen 系）。
纯标准库，Windows 直跑。
"""
import json
import os
import urllib.request

KEY_FILE = r"C:\Users\欧阳宏俊\.hetero-model-keys.env"

PLATFORMS = {
    "siliconflow": {"base": "https://api.siliconflow.cn/v1", "role": "主力（OpenAI兼容+200模型+免费兜底）"},
    "302.ai": {"base": "https://api.302.ai/v1", "role": "补闭源（GPT/Claude/Gemini 聚合）"},
    "national-supercomputing": {"base": "https://api.scnet.cn/api/llm/v1", "role": "定向国产（OpenAI协议、DeepSeek-R1蒸馏，端点 api/llm/v1）"},
}


def _load_keys():
    keys = {}
    if os.path.exists(KEY_FILE):
        for line in open(KEY_FILE, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip()
    return keys


def _key(name):
    return _load_keys().get(name, "")


def chat(model, prompt, base="https://api.siliconflow.cn/v1", key_env="SILICONFLOW_KEY", max_tokens=64):
    """OpenAI 兼容 chat 调用（硅基流动/302.AI 通用）。"""
    key = _key(key_env)
    if not key:
        return {"error": "无 key（%s）" % key_env}
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens}).encode("utf-8")
    req = urllib.request.Request(base + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {"model": d.get("model"), "content": d["choices"][0]["message"]["content"],
                "tokens": d.get("usage", {}).get("total_tokens")}
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, str(e)[:100])}


def status():
    """三平台 key 状态（只报有无 key、不报 key 值）。"""
    keys = _load_keys()
    mapping = {"siliconflow": "SILICONFLOW_KEY", "302.ai": "AI302_KEY",
               "national-supercomputing": "SCNET_KEY"}
    return {p: {"has_key": bool(keys.get(mapping[p], "")), "role": PLATFORMS[p]["role"]}
            for p in PLATFORMS}


if __name__ == "__main__":
    print("  平台 key 状态 =", status())
    r = chat("Qwen/Qwen2.5-7B-Instruct", "用一句话回答：A2A 网络的核心是什么？")
    print("  硅基流动调用 =", r)
