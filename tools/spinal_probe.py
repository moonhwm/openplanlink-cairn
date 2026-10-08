# -*- coding: utf-8 -*-
"""脊线桥 Supabase 只读健康探测（石敢当席工具）
用法: python spinal_probe.py
只读: cross_mode_channel 最新一条 + 行数, 不写不删。
"""
import os, sys, json
try:
    import supabase
except ImportError:
    print(json.dumps({'ok': False, 'err': 'supabase lib missing'}, ensure_ascii=False)); sys.exit(1)

URL = 'https://ltdodcumoxiqsnakpqog.supabase.co'
KEY = os.environ.get('SPINAL_PUB_KEY', 'sb_publishable_volgoMLbvToQQVKoSjlfxA_DKNb26Hl')

def main():
    c = supabase.create_client(URL, KEY)
    try:
        r = c.table('cross_mode_channel').select('*').order('ts', desc=True).limit(1).execute()
        cnt = c.table('cross_mode_channel').select('id', count='exact').execute()
        out = {'ok': True, 'last': r.data[0] if r.data else None,
               'count': cnt.count if cnt.data is not None else None}
    except Exception as e:
        out = {'ok': False, 'err': str(e)[:200]}
    print(json.dumps(out, ensure_ascii=False, default=str))

if __name__ == '__main__':
    main()
