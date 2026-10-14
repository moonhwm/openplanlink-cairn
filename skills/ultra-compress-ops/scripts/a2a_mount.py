#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a2a_mount.py — A2A 全员同步挂载协议（首份强制同步件）
三段：build-manifest（发件席铸户口）→ envelope（铸广播草稿，写总线须逐次批准）→ verify-mount（收件席校验挂载漂移）。
挂载位约定：dist 源 = /mnt/agents/upload/skill-dist-<日期>/；成员挂载后跑 verify-mount 并向 ack 台账登记。
"""
import argparse, hashlib, json, os, sys, time

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()

def build_manifest(skill_dir, seat):
    files = {}
    for dp, dns, fns in os.walk(skill_dir):
        dns.sort(); fns.sort()
        for fn in fns:
            if fn == 'mount_manifest.json': continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, skill_dir)
            files[rel] = {'size': os.path.getsize(p), 'sha256': sha256(p)}
    name = os.path.basename(skill_dir.rstrip('/'))
    ver = None
    sk = os.path.join(skill_dir, 'SKILL.md')
    if os.path.exists(sk):
        for line in open(sk, encoding='utf-8'):
            if 'version' in line.lower() and ':' in line:
                ver = line.split(':', 1)[1].strip(); break
    return {'proto': 'a2a-mount/1', 'skill': name, 'version': ver or 'v1.0.0',
            'seat': seat, 'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'files': files, 'file_count': len(files)}

def cmd_manifest(a):
    m = build_manifest(a.skill_dir, a.seat)
    out = os.path.join(a.skill_dir, 'mount_manifest.json')
    if os.path.exists(out) and not a.force:
        print('FAIL manifest 已存在（--force 方覆写）'); return 2
    json.dump(m, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'ok': True, 'skill': m['skill'], 'files': m['file_count']}, ensure_ascii=False)); return 0

def cmd_envelope(a):
    m = build_manifest(a.skill_dir, a.seat)
    env = {'kind': 'a2a-skill-mount', 'skill': m['skill'], 'version': m['version'],
           'file_count': m['file_count'],
           'manifest_sha256': hashlib.sha256(json.dumps(m['files'], sort_keys=True).encode()).hexdigest(),
           'dist_hint': f'/mnt/agents/upload/skill-dist-<日期>/{m["skill"]}.skill',
           'duty': '全体成员：①拉取 dist 包 ②解压至技能位 ③python3 a2a_mount.py verify-mount ④ACK 登记',
           'ts': m['ts'], 'by': a.seat}
    out = a.out or os.path.join(a.skill_dir, 'mount_envelope.json')
    json.dump(env, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'ok': True, 'envelope': out,
                      'note': '此为草稿——总线写操作须逐次显式批准（丁编第六条）'}, ensure_ascii=False)); return 0

def cmd_verify(a):
    m = json.load(open(a.manifest, encoding='utf-8'))
    bad = []
    for rel, meta in m['files'].items():
        p = os.path.join(a.mount_dir, rel)
        if not os.path.exists(p) or sha256(p) != meta['sha256']:
            bad.append(rel)
    print(json.dumps({'ok': not bad, 'checked': len(m['files']), 'drift': bad}, ensure_ascii=False))
    return 0 if not bad else 1

def cmd_smoke(a):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        sd = os.path.join(td, 'demo-skill'); os.makedirs(sd)
        open(os.path.join(sd, 'SKILL.md'), 'w').write('---\nname: demo\nversion: v0.1.0\n---\n')
        os.makedirs(os.path.join(sd, 'scripts')); open(os.path.join(sd, 'scripts/x.py'), 'w').write('print(1)')
        ns = argparse.Namespace(skill_dir=sd, seat='smoke', force=False)
        assert cmd_manifest(ns) == 0
        nsf = argparse.Namespace(skill_dir=sd, seat='smoke', force=False)
        assert cmd_manifest(nsf) == 2, '撞名必拒'
        ns2 = argparse.Namespace(skill_dir=sd, seat='smoke', out=None)
        assert cmd_envelope(ns2) == 0
        ns3 = argparse.Namespace(manifest=os.path.join(sd, 'mount_manifest.json'), mount_dir=sd)
        assert cmd_verify(ns3) == 0
        open(os.path.join(sd, 'scripts', 'x.py'), 'a').write('#drift')
        assert cmd_verify(ns3) == 1, '漂移必报'
    print('SMOKE PASS（manifest/envelope/verify 全链＋撞名拒＋漂移报负断言）'); return 0

def main():
    p = argparse.ArgumentParser(prog='a2a_mount', description='A2A 全员同步挂载协议')
    p.add_argument('--smoke', action='store_true')
    sub = p.add_subparsers(dest='cmd')
    m = sub.add_parser('build-manifest'); m.add_argument('skill_dir'); m.add_argument('--seat', default='k3-main')
    m.add_argument('--force', action='store_true'); m.set_defaults(fn=cmd_manifest)
    e = sub.add_parser('envelope'); e.add_argument('skill_dir'); e.add_argument('--seat', default='k3-main')
    e.add_argument('--out', default=None); e.set_defaults(fn=cmd_envelope)
    v = sub.add_parser('verify-mount'); v.add_argument('manifest'); v.add_argument('mount_dir'); v.set_defaults(fn=cmd_verify)
    a = p.parse_args()
    if a.smoke: sys.exit(cmd_smoke(a))
    if not getattr(a, 'fn', None): p.error('需子命令 build-manifest/envelope/verify-mount 或 --smoke')
    sys.exit(a.fn(a))

if __name__ == '__main__': main()
