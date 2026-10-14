#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""link_bridge.py — junction 移植件：Windows junction/mklink 操作在 Linux 的等价实现
核心术：搬移+回链（数据落大盘，原路径留符号链接）= junction 搬运术
注册表：默认 /mnt/agents/upload/link_bridge_registry.jsonl（跨 lineage 可见，SHA256 留痕）
冗余预留：schema 含 replicas[]；--replica-dir 占位登记；LINK_BRIDGE_HOOKS 环境变量钩子（冒号分隔，迁后调用）
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, datetime

REG_DEFAULT = '/mnt/agents/upload/link_bridge_registry.jsonl'

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()

def reg_append(reg, entry):
    os.makedirs(os.path.dirname(reg), exist_ok=True)
    entry['ts'] = datetime.datetime.now(datetime.UTC).isoformat()
    with open(reg, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def is_within(child, parent):
    return os.path.realpath(child).startswith(os.path.realpath(parent) + os.sep)

def cmd_migrate(a):
    """搬移+回链：src → dst_dir/，原路径留 symlink。对应 mklink /j 工作流。"""
    src = os.path.abspath(a.src)
    dst_dir = os.path.abspath(a.dst_dir)
    if not os.path.exists(src):
        print(f'FAIL 源不存在: {src}'); return 1
    if os.path.islink(src):
        print(f'FAIL 源已是符号链接（防链式腐烂 A→B→C）: {src} -> {os.readlink(src)}'); return 1
    if is_within(dst_dir, src):
        print('FAIL 目标目录在源内部（防自吞）'); return 1
    if os.path.isdir(src) and is_within(src, dst_dir):
        print('FAIL 源在目标目录内部（防倒吞）'); return 1
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(src))
    if os.path.exists(dst) or os.path.islink(dst):
        print(f'FAIL 目标已存在（不覆盖）: {dst}'); return 2
    size = os.path.getsize(src) if os.path.isfile(src) else None
    digest = sha256(src) if os.path.isfile(src) else None
    dir_stats = None
    if os.path.isdir(src):
        n, tot = 0, 0
        for dp, _, fs in os.walk(src):
            for f in fs:
                n += 1
                try:
                    tot += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
        dir_stats = {'files': n, 'bytes': tot}
    shutil.move(src, dst)
    if digest and sha256(dst) != digest:
        print('FAIL 落点哈希不符，已中止（文件已在新位，未回链）'); return 1
    if dir_stats:
        n2, tot2 = 0, 0
        for dp, _, fs in os.walk(dst):
            for f in fs:
                n2 += 1
                try:
                    tot2 += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
        if (n2, tot2) != (dir_stats['files'], dir_stats['bytes']):
            print(f'FAIL 目录完整性不符（迁前{dir_stats} vs 迁后files={n2},bytes={tot2}），'
                  '已中止未回链（数据在新位，人工核对）'); return 1
    os.symlink(dst, src)
    # 回链核验：链接可解且指向落点
    if os.path.realpath(src) != os.path.realpath(dst):
        print('FAIL 回链核验不过'); return 1
    entry = {'op': 'migrate-link', 'link': src, 'target': dst, 'size': size,
             'sha256': digest, 'dir_stats': dir_stats,
             'kind': 'dir' if os.path.isdir(dst) else 'file',
             'replicas': [], 'replica_dir_reserved': a.replica_dir}
    # 钩子接口（冗余扩展点）：迁后调用；结果入注册表，败则 exit 4（防状态不一致）
    hooks = [h for h in os.environ.get('LINK_BRIDGE_HOOKS', '').split(':') if h]
    hook_results = []
    for h in hooks:
        try:
            rc = subprocess.run([h, src, dst], timeout=300, check=False).returncode
            hook_results.append({'hook': h, 'rc': rc})
            if rc != 0:
                print(f'WARN 钩子 {h} 返回 rc={rc}（冗余未建立）')
        except Exception as e:
            hook_results.append({'hook': h, 'rc': -1, 'err': str(e)[:120]})
            print(f'WARN 钩子 {h} 异常: {e}')
    entry['hook_results'] = hook_results
    reg_append(a.registry, entry)
    print(json.dumps({'ok': True, 'link': src, 'target': dst,
                      'hooks': hook_results}, ensure_ascii=False))
    return 4 if any(r['rc'] != 0 for r in hook_results) else 0

def cmd_hardlink(a):
    """硬链接（对应 mklink /h）：仅文件、仅同文件系统；跨设备拒（EXDEV 不静默降级为复制）。"""
    src, dst = os.path.abspath(a.src), os.path.abspath(a.dst)
    if not os.path.isfile(src):
        print('FAIL 硬链只对文件'); return 1
    if os.path.exists(dst) or os.path.islink(dst):
        print(f'FAIL 目标已存在: {dst}'); return 2
    if os.stat(src).st_dev != os.stat(os.path.dirname(dst) or '.').st_dev:
        print('FAIL 跨文件系统硬链被拒（EXDEV；如需跨盘请用 migrate-link）'); return 1
    os.link(src, dst)
    reg_append(a.registry, {'op': 'hardlink', 'link': dst, 'target': src,
                            'size': os.path.getsize(src), 'sha256': sha256(src),
                            'kind': 'file', 'replicas': [], 'replica_dir_reserved': None})
    print(json.dumps({'ok': True, 'link': dst, 'target': src, 'inode_shared': True}, ensure_ascii=False))
    return 0

def cmd_check(a):
    """健康检查：注册表全量链路核验（断链/落点丢失/哈希漂移）。"""
    if not os.path.exists(a.registry):
        print('注册表不存在'); return 3
    total = broken = drift = 0
    for line in open(a.registry, encoding='utf-8'):
        e = json.loads(line)
        if e.get('op') not in ('migrate-link', 'hardlink'):
            continue
        total += 1
        link, target = e['link'], e['target']
        if e['op'] == 'migrate-link':
            if not os.path.islink(link) or not os.path.exists(target):
                broken += 1; print(f'BROKEN {link} -> {target}')
            elif e.get('sha256') and os.path.isfile(target) and sha256(target) != e['sha256']:
                drift += 1; print(f'DRIFT  {target}（落点哈希漂移）')
        else:
            if not (os.path.exists(link) and os.path.exists(target)
                    and os.path.samefile(link, target)):
                broken += 1; print(f'BROKEN hardlink {link} =/= {target}')
    print(json.dumps({'total': total, 'broken': broken, 'drift': drift}, ensure_ascii=False))
    return 0 if (broken == 0 and drift == 0) else 1

def cmd_smoke(a):
    """自检（含负断言）：临时目录内全流程 + 三类必拒。"""
    import tempfile
    reg = os.path.join(tempfile.mkdtemp(), 'reg.jsonl')
    with tempfile.TemporaryDirectory() as td:
        big = os.path.join(td, 'bigdisk'); os.makedirs(big)
        f1 = os.path.join(td, 'data.bin')
        open(f1, 'wb').write(b'junction-port-' * 1000)
        ns = argparse.Namespace(src=f1, dst_dir=big, registry=reg, replica_dir=None)
        assert cmd_migrate(ns) == 0, 'migrate 应成功'
        assert os.path.islink(f1), '原路径应成 symlink'
        assert open(f1, 'rb').read() == b'junction-port-' * 1000, '经链读内容应一致'
        # 负断言 1：删链接不伤目标
        os.unlink(f1)
        assert os.path.exists(os.path.join(big, 'data.bin')), '删链不得伤目标'
        # 负断言 2：源已是链接必拒
        os.symlink(os.path.join(big, 'data.bin'), f1)
        assert cmd_migrate(ns) == 1, '链接源必拒'
        # 负断言 3：目标撞名必拒 exit 2（测后恢复链接，保注册表健康态）
        os.unlink(f1); open(f1, 'wb').write(b'x')
        assert cmd_migrate(ns) == 2, '撞名必拒'
        os.unlink(f1); os.symlink(os.path.join(big, 'data.bin'), f1)
        # 负断言 4：自吞必拒
        d1 = os.path.join(td, 'd1'); os.makedirs(d1)
        ns2 = argparse.Namespace(src=d1, dst_dir=os.path.join(d1, 'sub'), registry=reg, replica_dir=None)
        assert cmd_migrate(ns2) == 1, '自吞必拒'
        # 负断言 5：跨设备硬链必拒（/dev/shm 与 td 通常不同设备；若同设备则跳过）
        ns3 = argparse.Namespace(src=os.path.join(big, 'data.bin'),
                                 dst='/dev/shm/_lb_hl', registry=reg)
        try:
            cross = os.stat(ns3.src).st_dev != os.stat('/dev/shm').st_dev
        except Exception:
            cross = False
        if cross:
            assert cmd_hardlink(ns3) == 1, '跨设备硬链必拒'
        else:
            print('  (smoke: /dev/shm 同设备，跨设备断言跳过)')
        if os.path.lexists('/dev/shm/_lb_hl'):
            os.unlink('/dev/shm/_lb_hl')
        # 正断言 6：目录迁移带完整性核验（件数+字节入注册表）
        d2 = os.path.join(td, 'proj'); os.makedirs(os.path.join(d2, 'sub'))
        open(os.path.join(d2, 'a.txt'), 'w').write('aa')
        open(os.path.join(d2, 'sub', 'b.txt'), 'w').write('bbb')
        ns5 = argparse.Namespace(src=d2, dst_dir=big, registry=reg, replica_dir=None)
        assert cmd_migrate(ns5) == 0, '目录迁移应成功'
        last = json.loads(open(reg, encoding='utf-8').read().strip().split('\n')[-1])
        assert last['dir_stats'] == {'files': 2, 'bytes': 5}, 'dir_stats 应准确'
        assert open(os.path.join(d2, 'sub', 'b.txt')).read() == 'bbb', '经链读目录内容应一致'
        # 负断言 7：钩子失败 → exit 4 且注册表留痕
        hook = os.path.join(td, 'bad_hook.sh')
        open(hook, 'w').write('#!/bin/sh\nexit 7\n'); os.chmod(hook, 0o755)
        os.environ['LINK_BRIDGE_HOOKS'] = hook
        f2 = os.path.join(td, 'data2.bin'); open(f2, 'wb').write(b'zz')
        ns6 = argparse.Namespace(src=f2, dst_dir=big, registry=reg, replica_dir=None)
        assert cmd_migrate(ns6) == 4, '钩子失败应 exit 4'
        last = json.loads(open(reg, encoding='utf-8').read().strip().split('\n')[-1])
        assert last['hook_results'][0]['rc'] != 0, '钩子失败应入注册表'
        del os.environ['LINK_BRIDGE_HOOKS']
        # check 门：健康态
        ns4 = argparse.Namespace(registry=reg)
        assert cmd_check(ns4) == 0, '健康检查应过'
    print('SMOKE PASS（含 5 项负断言）')
    return 0

def main():
    p = argparse.ArgumentParser(prog='link_bridge', description='junction 移植件：搬移+回链/硬链/健康检查')
    p.add_argument('--registry', default=os.environ.get('LINK_BRIDGE_REGISTRY', REG_DEFAULT))
    p.add_argument('--smoke', action='store_true', help='自检（含负断言）')
    sub = p.add_subparsers(dest='cmd')
    m = sub.add_parser('migrate-link', help='搬移+回链（junction 搬运术）')
    m.add_argument('src'); m.add_argument('dst_dir')
    m.add_argument('--replica-dir', default=None, help='[预留] 冗余副本目录（登记不执行）')
    m.set_defaults(fn=cmd_migrate)
    h = sub.add_parser('hardlink', help='硬链接（mklink /h 等价，同文件系统）')
    h.add_argument('src'); h.add_argument('dst')
    h.set_defaults(fn=cmd_hardlink)
    c = sub.add_parser('check', help='注册表链路健康检查')
    c.set_defaults(fn=cmd_check)
    a = p.parse_args()
    if a.smoke:
        sys.exit(cmd_smoke(a))
    if not getattr(a, 'fn', None):
        p.error('需子命令（migrate-link/hardlink/check）或 --smoke')
    sys.exit(a.fn(a))

if __name__ == '__main__':
    main()
