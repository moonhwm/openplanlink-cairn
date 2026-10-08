#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""knowledge_digest.py —— 等幂知识消化（哲学/科学/艺术，CAS 内容寻址 + 幂等去重）。

依新目标：最可能可以等幂消化包括哲学与科学、艺术等在内的可能知识。
以 SHA-256 内容寻址实现幂等（同源内容只存一份），按领域分类。
纯标准库，Windows 直跑。
"""
import hashlib
import json
import os

DOMAINS = ("philosophy", "science", "art")


class KnowledgeDigest:
    def __init__(self):
        self.by_hash = {}     # hash -> {domain, text}
        self.by_domain = {d: {} for d in DOMAINS}  # domain -> hash -> True

    def ingest(self, domain, text):
        """幂等消化：返回 (digest, is_new)。同源内容只存一份。"""
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        is_new = h not in self.by_hash
        if is_new:
            self.by_hash[h] = {"domain": domain, "text": text}
            if domain in self.by_domain:
                self.by_domain[domain][h] = True
        return h, is_new

    def save(self, path):
        """持久化（原子写）：跨重启等幂不丢。"""
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.by_hash, f, ensure_ascii=False)
        os.replace(tmp, path)

    def load(self, path):
        """载入持久化知识。"""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.by_hash = json.load(f)
            self.by_domain = {d: {} for d in DOMAINS}
            for h, rec in self.by_hash.items():
                d = rec.get("domain")
                if d in self.by_domain:
                    self.by_domain[d][h] = True

    def count(self, domain=None):
        if domain is None:
            return len(self.by_hash)
        return len(self.by_domain.get(domain, {}))

    def has(self, text):
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return h in self.by_hash

    def store_to_cas(self, store):
        """把知识碎片写入 CAS 指针化存储（blobs 去重 + gzip），返回 {hash: 指针}。"""
        out = {}
        for h, rec in self.by_hash.items():
            out[h] = store.put(rec["text"].encode("utf-8"))  # CasStore.put 返回哈希指针
        return out


if __name__ == "__main__":
    import tempfile
    p = os.path.join(tempfile.gettempdir(), "kd_demo.json")
    kd = KnowledgeDigest()
    kd.ingest("philosophy", "自我不是凝固不变的本质，而是在时间性中不断生成的动态结构")
    kd.ingest("science", "能量守恒定律")
    kd.ingest("art", "留白是中国画的意境")
    kd.save(p)
    kd2 = KnowledgeDigest()
    kd2.load(p)
    print("  持久化前 count =", kd.count(), "｜ 载入后 count =", kd2.count(), "（跨重启不丢）")
    print("  载入后 has('能量守恒定律') =", kd2.has("能量守恒定律"))
    h, is_new = kd2.ingest("science", "能量守恒定律")   # 载入后再重复
    print("  载入后重复ingest is_new =", is_new, "（持久化后仍幂等）")
    if os.path.exists(p):
        os.remove(p)

