#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""madao_watch.py — 码道（CodeArts/长任务管线）24h 运维可视＋命令注入
机制：共享存储即总线。跑批席向 <watchdir>/heartbeat.jsonl 追加心跳（stage/done/total/note）；
指挥席向 <watchdir>/inbox.jsonl 注入命令（op/args），跑批席轮询收件并回 ack.jsonl。
status 一眼三问：在不在跑（心跳新鲜度）、跑到哪（done/total）、卡在哪（stage 滞留时长）。
失联判级：fresh(<2×interval) / stale(<10×) / lost(≥10×)。
"""
import argparse, json, os, sys, time, uuid

def now(): return time.strftime('%Y-%m-%dT%H:%M:%S%z')

def read_jsonl(p):
    if not os.path.exists(p): return []
    out = []
    with open(p, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if l:
                try: out.append(json.loads(l))
                except json.JSONDecodeError: pass
    return out

def append_jsonl(p, row):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'a', encoding='utf-8') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')

def cmd_emit(a):
    append_jsonl(os.path.join(a.watchdir, 'heartbeat.jsonl'),
                 {'ts': now(), 'epoch': time.time(), 'seat': a.seat, 'stage': a.stage,
                  'done': a.done, 'total': a.total, 'note': a.note})
    print(json.dumps({'ok': True, 'stage': a.stage, 'done': a.done, 'total': a.total}, ensure_ascii=False)); return 0

def cmd_status(a):
    hbs = read_jsonl(os.path.join(a.watchdir, 'heartbeat.jsonl'))
    if not hbs:
        print(json.dumps({'ok': False, 'verdict': 'no-heartbeat', 'note': '未见任何心跳——如实报死，不猜'}, ensure_ascii=False)); return 2
    last = hbs[-1]
    age = time.time() - last.get('epoch', 0)
    interval = a.interval
    verdict = 'fresh' if age < 2 * interval else ('stale' if age < 10 * interval else 'lost')
    done, total = last.get('done', 0), last.get('total', 0)
    pct = round(100.0 * done / total, 1) if total else None
    # 吞吐：近 10 心跳的 done 增速
    recent = hbs[-10:]
    rate = None
    if len(recent) >= 2 and recent[-1]['epoch'] > recent[0]['epoch']:
        rate = round((recent[-1].get('done', 0) - recent[0].get('done', 0)) / (recent[-1]['epoch'] - recent[0]['epoch']), 3)
    inbox = read_jsonl(os.path.join(a.watchdir, 'inbox.jsonl'))
    acks = {r.get('ack_id') for r in read_jsonl(os.path.join(a.watchdir, 'ack.jsonl'))}
    pending = [c.get('id') for c in inbox if c.get('id') not in acks]
    out = {'ok': verdict != 'lost', 'verdict': verdict, 'age_sec': round(age, 1),
           'seat': last.get('seat'), 'stage': last.get('stage'), 'done': done, 'total': total,
           'pct': pct, 'rate_per_sec': rate, 'heartbeats': len(hbs), 'pending_cmds': pending,
           'last_ts': last.get('ts'), 'note': last.get('note')}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if verdict == 'fresh' else (1 if verdict == 'stale' else 2)

def cmd_inject(a):
    cid = uuid.uuid4().hex[:12]
    append_jsonl(os.path.join(a.watchdir, 'inbox.jsonl'),
                 {'id': cid, 'ts': now(), 'by': a.seat, 'op': a.op, 'args': a.args})
    print(json.dumps({'ok': True, 'cmd_id': cid, 'op': a.op}, ensure_ascii=False)); return 0

def cmd_poll(a):
    """跑批席轮询：取未 ack 命令，回执后打印待执行清单（执行与否由跑批席决定，不自动执行）。"""
    inbox = read_jsonl(os.path.join(a.watchdir, 'inbox.jsonl'))
    acks = {r.get('ack_id') for r in read_jsonl(os.path.join(a.watchdir, 'ack.jsonl'))}
    todo = [c for c in inbox if c.get('id') not in acks]
    for c in todo:
        append_jsonl(os.path.join(a.watchdir, 'ack.jsonl'),
                     {'ack_id': c['id'], 'ts': now(), 'seat': a.seat, 'status': 'received'})
    print(json.dumps({'ok': True, 'received': [c['id'] for c in todo],
                      'ops': [{'id': c['id'], 'op': c['op'], 'args': c['args']} for c in todo]}, ensure_ascii=False)); return 0

def cmd_smoke(a):
    import tempfile
    with tempfile.TemporaryDirectory() as wd:
        ns = argparse.Namespace(watchdir=wd, seat='smoke-runner', stage='压测第3批', done=30, total=100, note='smoke')
        assert cmd_emit(ns) == 0
        ns2 = argparse.Namespace(watchdir=wd, interval=3600)
        assert cmd_status(ns2) == 0, 'fresh 应 0'
        ns3 = argparse.Namespace(watchdir=wd, seat='smoke-cmdr', op='switch_model', args='{"model":"pangu"}')
        assert cmd_inject(ns3) == 0
        ns4 = argparse.Namespace(watchdir=wd, seat='smoke-runner')
        assert cmd_poll(ns4) == 0
        st = read_jsonl(os.path.join(wd, 'ack.jsonl'))
        assert len(st) == 1, 'ack 应落'
        ns5 = argparse.Namespace(watchdir=wd, interval=3600)
        assert cmd_status(ns5) == 0
        # 负断言：空目录报死
        with tempfile.TemporaryDirectory() as wd2:
            ns6 = argparse.Namespace(watchdir=wd2, interval=3600)
            assert cmd_status(ns6) == 2, '无心跳应 exit 2'
    print('SMOKE PASS（emit→status→inject→poll→ack 全链＋无心跳报死负断言）'); return 0

def main():
    p = argparse.ArgumentParser(prog='madao_watch', description='码道 24h 运维可视＋命令注入')
    p.add_argument('--watchdir', default='/mnt/agents/upload/madao_watch')
    p.add_argument('--smoke', action='store_true')
    sub = p.add_subparsers(dest='cmd')
    e = sub.add_parser('emit'); e.add_argument('--seat', default='runner'); e.add_argument('--stage', required=True)
    e.add_argument('--done', type=int, default=0); e.add_argument('--total', type=int, default=0)
    e.add_argument('--note', default=''); e.set_defaults(fn=cmd_emit)
    s = sub.add_parser('status'); s.add_argument('--interval', type=int, default=3600); s.set_defaults(fn=cmd_status)
    i = sub.add_parser('inject'); i.add_argument('--seat', default='commander'); i.add_argument('--op', required=True)
    i.add_argument('--args', default='{}'); i.set_defaults(fn=cmd_inject)
    po = sub.add_parser('poll'); po.add_argument('--seat', default='runner'); po.set_defaults(fn=cmd_poll)
    a = p.parse_args()
    if a.smoke: sys.exit(cmd_smoke(a))
    if not getattr(a, 'fn', None): p.error('需子命令 emit/status/inject/poll 或 --smoke')
    sys.exit(a.fn(a))

if __name__ == '__main__': main()
