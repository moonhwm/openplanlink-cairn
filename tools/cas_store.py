#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""cas_store.py —— 指针化存储（内容寻址 CAS + SQLite 元数据）。

满足"技能录入"要求：⑤高度指针化映射（载荷按 SHA-256 内容寻址、结构/元数据入 SQLite，
指针=哈希，天然去重）；⑥预留对象存储接口（blobs 目录可整体换 MinIO/S3，指针不变）。
纯标准库（hashlib+sqlite3+os），Windows 直跑。压缩(zstd)留作后续优化。
"""
import gzip
import hashlib
import os
import sqlite3
import time


class CasStore:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.blobs = os.path.join(self.root, "blobs")
        self.dbpath = os.path.join(self.root, "index.sqlite")
        os.makedirs(self.blobs, exist_ok=True)
        self._db = sqlite3.connect(self.dbpath)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS objects(hash TEXT PRIMARY KEY, size INTEGER, mtime REAL, refs INTEGER DEFAULT 1)")

    def put(self, data: bytes) -> str:
        """写入内容，返回哈希指针；相同内容只存一份（去重）。"""
        h = hashlib.sha256(data).hexdigest()
        rel = os.path.join(h[:2], h)          # 分片目录，避免单目录过大
        path = os.path.join(self.blobs, rel)
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(gzip.compress(data, compresslevel=6))   # 高效压缩：zstd 可替换此层
            self._db.execute("INSERT OR IGNORE INTO objects(hash,size,mtime) VALUES(?,?,?)",
                             (h, len(data), time.time()))
        else:
            self._db.execute("UPDATE objects SET refs=refs+1 WHERE hash=?", (h,))
        self._db.commit()
        return h

    def get(self, h: str) -> bytes:
        """按哈希指针取回内容（自动解压）。"""
        rel = os.path.join(h[:2], h)
        with open(os.path.join(self.blobs, rel), "rb") as f:
            return gzip.decompress(f.read())

    def exists(self, h: str) -> bool:
        return os.path.exists(os.path.join(self.blobs, h[:2], h))

    def stats(self) -> dict:
        n = self._db.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
        size = self._db.execute("SELECT COALESCE(SUM(size),0) FROM objects").fetchone()[0]
        return {"objects": n, "bytes": size, "blobs_dir": self.blobs}


if __name__ == "__main__":
    import tempfile
    store = CasStore(os.path.join(tempfile.gettempdir(), "cas_demo"))
    a = store.put("同一份内容".encode("utf-8"))
    b = store.put("同一份内容".encode("utf-8"))   # 相同内容
    c = store.put("不同内容".encode("utf-8"))
    print("  指针a=%s… b=%s…（a==b 去重=%s）" % (a[:12], b[:12], a == b))
    print("  get(a) =", store.get(a).decode("utf-8"))
    print("  stats =", store.stats(), "（3次put但objects=2 → 去重生效）")
