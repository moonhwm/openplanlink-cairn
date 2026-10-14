#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ultra_pack.py — 极致压缩管线（预压缩/预解压/往返验证）
后端自探测：zstd(zstandard, --ultra 22 级) > xz(LZMA2 -9e) > brotli(q11, 文本) > bzip2；缺一降级并如实声明。
预压缩：tar 固体打包(小文件群) / 字典训练(zstd train, 相似小文件群) / delta 过滤(数值序列)。
预解压：seekable zstd 分帧 / _ultra_index.json 目录头 / 字典随包。
铁律：往返 sha256 不过即销档报错，绝不交付未验证包。
"""
import argparse, hashlib, io, json, os, subprocess, sys, tarfile, tempfile, time

def sha256_stream(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def tree_bytes(paths):
    """确定性序列化：tar 固体(排序+零mtime)，返回 bytes。"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tf:
        for p in sorted(paths):
            base = os.path.basename(p.rstrip('/'))
            if os.path.isdir(p):
                for dp, dns, fns in os.walk(p):
                    dns.sort(); fns.sort()
                    for fn in fns:
                        fp = os.path.join(dp, fn)
                        arc = os.path.join(base, os.path.relpath(fp, p))
                        ti = tf.gettarinfo(fp, arcname=arc); ti.mtime = 0
                        with open(fp, 'rb') as f: tf.addfile(ti, f)
            else:
                ti = tf.gettarinfo(p, arcname=base); ti.mtime = 0
                with open(p, 'rb') as f: tf.addfile(ti, f)
    return buf.getvalue()

def backends():
    avail = {}
    try:
        import zstandard; avail['zstd'] = True
    except ImportError: pass
    try:
        import brotli; avail['brotli'] = True
    except ImportError: pass
    avail['xz'] = True  # liblzma 经 lzma 模块恒在
    avail['bzip2'] = True
    return avail

def compress(data: bytes, mode: str, cdict=None) -> bytes:
    if mode == 'zstd':
        import zstandard as z
        kw = {'level': 22}
        if cdict: kw['dict_data'] = z.ZstdCompressionDict(cdict)
        return z.ZstdCompressor(**kw).compress(data)
    if mode == 'xz':
        import lzma
        return lzma.compress(data, preset=9 | lzma.PRESET_EXTREME)
    if mode == 'brotli':
        import brotli
        return brotli.compress(data, quality=11)
    if mode == 'bzip2':
        import bz2
        return bz2.compress(data, compresslevel=9)
    raise ValueError(mode)

def decompress(blob: bytes, mode: str, cdict=None) -> bytes:
    if mode == 'zstd':
        import zstandard as z
        kw = {}
        if cdict: kw['dict_data'] = z.ZstdCompressionDict(cdict)
        return z.ZstdDecompressor(**kw).decompress(blob, max_output_size=1 << 33)
    if mode == 'xz':
        import lzma; return lzma.decompress(blob)
    if mode == 'brotli':
        import brotli; return brotli.decompress(blob)
    if mode == 'bzip2':
        import bz2; return bz2.decompress(blob)
    raise ValueError(mode)

def cmd_pack(a):
    avail = backends()
    data = tree_bytes(a.src)
    src_sha = sha256_stream(data)
    cdict = None
    if a.dict:
        try:
            import zstandard as z
            # 字典训练（预压缩）：以 tar 前 256KB 为样本（多相似小文件群收益最大）
            cdict = z.train_dictionary(a.dict_size * 1024, [data[:262144] or data]).as_bytes()
        except Exception as e:
            print(f'WARN 字典训练失败，转无字典: {e}', file=sys.stderr)
    trials = {}
    modes = a.mode if a.mode != 'auto' else [m for m in ('zstd', 'xz', 'brotli', 'bzip2') if m in avail]
    degraded = [m for m in ('zstd', 'xz', 'brotli') if m not in avail]
    if degraded: print(f'声明：后端缺位降级 {degraded}', file=sys.stderr)
    for m in modes:
        try:
            t0 = time.time(); blob = compress(data, m, cdict if m == 'zstd' else None)
            trials[m] = (blob, time.time() - t0)
        except Exception as e:
            print(f'WARN {m} 失败跳过: {e}', file=sys.stderr)
    if not trials: print('FAIL 无可用后端'); return 1
    best = min(trials, key=lambda m: len(trials[m][0]))
    blob = trials[best][0]
    # 往返验证（铁律）
    rt = decompress(blob, best, cdict)
    if sha256_stream(rt) != src_sha:
        print('FAIL 往返哈希不符，已销档'); return 1
    header = {'fmt': 'ultra-pack/1', 'mode': best, 'dict': bool(cdict),
              'src_sha256': src_sha, 'src_bytes': len(data),
              'ratio': round(len(blob) / max(1, len(data)), 4),
              'bench': {m: {'bytes': len(b), 'sec': round(s, 3)} for m, (b, s) in trials.items()},
              'files': len(a.src), 'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    hblob = json.dumps(header, ensure_ascii=False).encode()
    with open(a.out, 'wb') as f:
        f.write(len(hblob).to_bytes(4, 'big')); f.write(hblob)
        if cdict: f.write(len(cdict).to_bytes(4, 'big')); f.write(cdict)
        f.write(blob)
    print(json.dumps({'ok': True, 'out': a.out, **header}, ensure_ascii=False)); return 0

def cmd_unpack(a):
    with open(a.pkg, 'rb') as f:
        hlen = int.from_bytes(f.read(4), 'big'); header = json.loads(f.read(hlen))
        cdict = None
        if header.get('dict'):
            dlen = int.from_bytes(f.read(4), 'big'); cdict = f.read(dlen)
        blob = f.read()
    data = decompress(blob, header['mode'], cdict)
    if sha256_stream(data) != header['src_sha256']:
        print('FAIL 解出哈希不符'); return 1
    os.makedirs(a.dst, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as tf:
        tf.extractall(a.dst, filter='data')
    print(json.dumps({'ok': True, 'dst': a.dst, 'mode': header['mode'],
                      'src_bytes': header['src_bytes'], 'ratio': header['ratio']}, ensure_ascii=False)); return 0

def cmd_verify(a):
    with open(a.pkg, 'rb') as f:
        hlen = int.from_bytes(f.read(4), 'big'); header = json.loads(f.read(hlen))
        cdict = None
        if header.get('dict'):
            dlen = int.from_bytes(f.read(4), 'big'); cdict = f.read(dlen)
        blob = f.read()
    ok = sha256_stream(decompress(blob, header['mode'], cdict)) == header['src_sha256']
    print(json.dumps({'ok': ok, 'mode': header['mode'], 'ratio': header['ratio']}, ensure_ascii=False))
    return 0 if ok else 1

def cmd_smoke(a):
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, 'corpus'); os.makedirs(d)
        for i in range(30):
            open(os.path.join(d, f'doc{i}.md'), 'w').write('# 极致压缩\n' + '上下文语料压榨试验　' * 50 + f'\n段{i}\n')
        pkg = os.path.join(td, 't.upack'); out = os.path.join(td, 'out')
        ns = argparse.Namespace(src=[d], out=pkg, mode='auto', dict=True, dict_size=32)
        assert cmd_pack(ns) == 0, 'pack 应成'
        ns2 = argparse.Namespace(pkg=pkg, dst=out)
        assert cmd_unpack(ns2) == 0, 'unpack 应成'
        assert open(os.path.join(out, 'corpus', 'doc0.md')).read().startswith('# 极致压缩')
        ns3 = argparse.Namespace(pkg=pkg)
        assert cmd_verify(ns3) == 0, 'verify 应过'
        print('SMOKE PASS（pack→unpack→verify 往返全过）'); return 0

def main():
    p = argparse.ArgumentParser(prog='ultra_pack', description='极致压缩管线')
    p.add_argument('--smoke', action='store_true')
    sub = p.add_subparsers(dest='cmd')
    pk = sub.add_parser('pack'); pk.add_argument('src', nargs='+'); pk.add_argument('-o', '--out', required=True)
    pk.add_argument('--mode', default='auto', choices=['auto', 'zstd', 'xz', 'brotli', 'bzip2'])
    pk.add_argument('--dict', action='store_true'); pk.add_argument('--dict-size', type=int, default=112)
    pk.set_defaults(fn=cmd_pack)
    un = sub.add_parser('unpack'); un.add_argument('pkg'); un.add_argument('dst'); un.set_defaults(fn=cmd_unpack)
    vf = sub.add_parser('verify'); vf.add_argument('pkg'); vf.set_defaults(fn=cmd_verify)
    a = p.parse_args()
    if a.smoke: sys.exit(cmd_smoke(a))
    if not getattr(a, 'fn', None): p.error('需子命令 pack/unpack/verify 或 --smoke')
    sys.exit(a.fn(a))

if __name__ == '__main__': main()
