#!/usr/bin/env python3
"""
Tushare 高性能燃烧引擎 v1.0
砚坚席位 · 码道(CodeArts) · 2026-09-29

目标: 最大化利用 Tushare 积分额度，高性能拉取全市场多维度数据
策略: 50线程并发 + 多接口交替 + 按交易日批量拉取
"""

import requests
import json
import time
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# ============================================================
# 配置
# ============================================================
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', 'a7ad47b0fcdc8964610b7101dcfee0016ce47cf3db2bf6e421ab21d0')
TUSHARE_URL = 'https://api.tushare.pro'
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tushare_data')
MAX_WORKERS = 50  # 并发线程数 (50线程稳定, 100线程超时)
REQUEST_TIMEOUT = 20

# ============================================================
# 接口清单 (已验证可用, 积分15000+)
# ============================================================
# 格式: (api_name, 描述, 参数模式, 单日预估行数)
# 参数模式: 'trade_date' = 用trade_date拉全市场, 'ts_code' = 按个股拉

DAILY_APIS = [
    # === 行情类 (每只股票一行) ===
    ('daily',          '日线行情',     'trade_date', 5557),
    ('daily_basic',    '每日指标',     'trade_date', 5557),
    ('moneyflow',      '资金流向',     'trade_date', 5569),
    ('adj_factor',     '复权因子',     'trade_date', 5569),
    ('stk_limit',      '涨跌停价',     'trade_date', 5648),
    ('stk_factor_pro', '每日因子Pro',  'trade_date', 5557),
    ('cyq_perf',       '每日筹码',     'trade_date', 5557),
    
    # === 统计类 (少量行) ===
    ('limit_list_d',   '涨跌停统计',   'trade_date', 75),
    ('block_trade',    '大宗交易',     'trade_date', 135),
    ('top_list',       '龙虎榜',       'trade_date', 72),
    ('top_inst',       '龙虎榜机构',   'trade_date', 810),
    ('margin_detail',  '融资融券明细', 'trade_date', 4452),
    ('moneyflow_hsgt', '沪深港通资金', 'trade_date', 1),
    ('hsgt_top10',     '沪深港通十大', 'trade_date', 20),
    
    # === 行业/概念 ===
    ('sw_daily',       '申万行业日线', 'trade_date', 439),
    ('dc_index',       '东财概念板块', 'trade_date', 1031),
    
    # === 期货 ===
    ('fut_daily',      '期货日线',     'trade_date', 1075),
    ('fut_settle',     '期货结算',     'trade_date', 870),
    ('fut_wsr',        '期货仓单',     'trade_date', 1394),
    ('fut_mapping',    '期货主力映射', 'trade_date', 202),
    
    # === 沪深港通 ===
    ('hk_hold',        '沪深港通持股', 'trade_date', 1013),
    ('ccass_hold',     '中央结算持股', 'trade_date', 5000),
    
    # === 期权/可转债/回购 ===
    ('opt_daily',      '期权日线',     'trade_date', 15000),
    ('cb_daily',       '可转债日线',   'trade_date', 315),
    ('repo_daily',     '国债回购',     'trade_date', 46),
]

# 按个股拉的接口 (需要遍历股票列表)
PER_STOCK_APIS = [
    ('income',             '利润表',       129),
    ('balancesheet',       '资产负债表',   100),
    ('cashflow',            '现金流量表',   100),
    ('fina_indicator',      '财务指标',     100),
    ('fina_mainbz',         '主营业务构成', 150),
    ('forecast',            '业绩预告',     16),
    ('express',             '业绩快报',     4),
    ('dividend',            '分红送股',     98),
    ('stk_managers',        '高管信息',     265),
    ('stk_rewards',         '高管薪酬',     1428),
    ('stk_holdernumber',    '股东人数',     149),
    ('pledge_stat',         '股权质押统计', 646),
    ('fina_audit',          '审计意见',     39),
]

# 基础数据 (一次性拉取)
BASIC_APIS = [
    ('stock_basic',     {'list_status': 'L'},      '股票列表'),
    ('index_basic',     {'market': 'SSE'},          '指数基本信息'),
    ('fund_basic',      {'market': 'E'},            '基金基本信息'),
    ('cb_basic',        {'trade_date': ''},         '可转债基本信息'),
    ('fut_basic',       {'trade_date': ''},         '期货基本信息'),
    ('opt_basic',       {'trade_date': ''},         '期权基本信息'),
    ('hk_basic',        {'trade_date': ''},         '港股基本信息'),
    ('us_basic',        {'trade_date': ''},         '美股基本信息'),
    ('new_share',       {'trade_date': ''},         '新股数据'),
    ('trade_cal',       {'exchange': 'SSE'},        '交易日历'),
    ('shibor_lpr',      {'trade_date': ''},         'LPR利率'),
    ('stock_company',   {'ts_code': ''},            '公司信息'),
]

# 宏观数据 (一次性拉取)
MACRO_APIS = [
    ('cn_gdp',    {}, 'GDP'),
    ('cn_cpi',    {}, 'CPI'),
    ('cn_ppi',    {}, 'PPI'),
    ('cn_m',      {}, '货币供应量'),
    ('cn_pmi',    {}, 'PMI'),
    ('sf_month',  {}, '社融月度'),
    ('shibor',    {'start_date': '', 'end_date': ''}, 'Shibor'),
    ('shibor_quote', {'start_date': '', 'end_date': ''}, 'Shibor报价'),
]

# ============================================================
# 核心函数
# ============================================================

def call_tushare(api_name, params, fields=''):
    """调用Tushare API"""
    payload = {
        'api_name': api_name,
        'token': TUSHARE_TOKEN,
        'params': params,
        'fields': fields
    }
    resp = requests.post(TUSHARE_URL, json=payload, timeout=REQUEST_TIMEOUT)
    data = resp.json()
    if data.get('code') != 0:
        return None, data.get('msg', '')
    return data.get('data'), ''

def get_trade_dates(start_date, end_date):
    """获取交易日列表"""
    data, msg = call_tushare('trade_cal', {
        'exchange': 'SSE',
        'start_date': start_date,
        'end_date': end_date
    })
    if not data:
        print(f'获取交易日失败: {msg}')
        return []
    dates = []
    fields = data['fields']
    for row in data['items']:
        d = dict(zip(fields, row))
        if d.get('is_open') == 1:
            dates.append(d['cal_date'])
    return dates

def pull_daily_data(api_name, trade_date, output_dir):
    """拉取单日全市场数据"""
    data, msg = call_tushare(api_name, {'trade_date': trade_date})
    if not data:
        return api_name, trade_date, 0, False, msg
    
    rows = len(data['items'])
    # 保存数据
    filename = f'{api_name}_{trade_date}.json'
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'api_name': api_name,
            'trade_date': trade_date,
            'fields': data['fields'],
            'items': data['items'],
            'pulled_at': datetime.now().isoformat()
        }, f, ensure_ascii=False)
    
    return api_name, trade_date, rows, True, ''

def pull_basic_data(api_name, params, output_dir):
    """拉取基础数据"""
    data, msg = call_tushare(api_name, params)
    if not data:
        return api_name, 0, False, msg
    
    rows = len(data['items'])
    filename = f'{api_name}_basic.json'
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'api_name': api_name,
            'fields': data['fields'],
            'items': data['items'],
            'pulled_at': datetime.now().isoformat()
        }, f, ensure_ascii=False)
    
    return api_name, rows, True, ''

def burn_daily_apis(trade_dates, output_dir):
    """燃烧: 按交易日批量拉取所有日频接口"""
    print(f'\n{"="*60}')
    print(f'燃烧日频接口: {len(DAILY_APIS)}接口 x {len(trade_dates)}交易日 = {len(DAILY_APIS)*len(trade_dates)}任务')
    print(f'并发线程: {MAX_WORKERS}')
    print(f'{"="*60}')
    
    tasks = []
    for api_name, desc, param_mode, est_rows in DAILY_APIS:
        for td in trade_dates:
            tasks.append((api_name, td))
    
    start_time = time.time()
    ok_count = 0
    fail_count = 0
    total_rows = 0
    fail_details = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(pull_daily_data, api_name, td, output_dir): (api_name, td)
            for api_name, td in tasks
        }
        completed = 0
        for future in as_completed(futures):
            api_name, trade_date, rows, success, msg = future.result()
            completed += 1
            if success:
                ok_count += 1
                total_rows += rows
            else:
                fail_count += 1
                fail_details.append((api_name, trade_date, msg))
            
            # 进度报告
            if completed % 50 == 0 or completed == len(tasks):
                elapsed = time.time() - start_time
                pct = completed / len(tasks) * 100
                rate = completed / elapsed if elapsed > 0 else 0
                print(f'  进度: {completed}/{len(tasks)} ({pct:.0f}%) | 成功={ok_count} 失败={fail_count} | 数据行={total_rows:,} | {rate:.1f}req/s | 耗时={elapsed:.0f}s')
    
    elapsed = time.time() - start_time
    print(f'\n日频接口燃烧完成:')
    print(f'  成功: {ok_count}, 失败: {fail_count}')
    print(f'  总数据行: {total_rows:,}')
    print(f'  总耗时: {elapsed:.1f}s')
    print(f'  吞吐量: {len(tasks)/elapsed:.1f}req/s, {total_rows/elapsed:.0f}rows/s')
    
    if fail_details:
        print(f'  失败详情(前10):')
        for api, td, msg in fail_details[:10]:
            print(f'    {api} {td}: {msg[:60]}')
    
    return ok_count, fail_count, total_rows

def burn_basic_apis(output_dir):
    """燃烧: 基础数据一次性拉取"""
    print(f'\n{"="*60}')
    print(f'燃烧基础数据: {len(BASIC_APIS)}接口')
    print(f'{"="*60}')
    
    start_time = time.time()
    ok_count = 0
    fail_count = 0
    total_rows = 0
    
    for api_name, params, desc in BASIC_APIS:
        # 清理空参数
        clean_params = {k: v for k, v in params.items() if v != ''}
        data, msg = call_tushare(api_name, clean_params)
        if data:
            rows = len(data['items'])
            total_rows += rows
            ok_count += 1
            filename = f'{api_name}_basic.json'
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'api_name': api_name,
                    'fields': data['fields'],
                    'items': data['items'],
                    'pulled_at': datetime.now().isoformat()
                }, f, ensure_ascii=False)
            print(f'  OK   | {api_name:25s} | {desc:20s} | {rows:6d} rows')
        else:
            fail_count += 1
            print(f'  FAIL | {api_name:25s} | {desc:20s} | {msg[:50]}')
    
    elapsed = time.time() - start_time
    print(f'\n基础数据燃烧完成: 成功={ok_count} 失败={fail_count} 总行={total_rows:,} 耗时={elapsed:.1f}s')
    return ok_count, fail_count, total_rows

def burn_macro_apis(output_dir):
    """燃烧: 宏观数据一次性拉取"""
    print(f'\n{"="*60}')
    print(f'燃烧宏观数据: {len(MACRO_APIS)}接口')
    print(f'{"="*60}')
    
    start_time = time.time()
    ok_count = 0
    fail_count = 0
    total_rows = 0
    
    for api_name, params, desc in MACRO_APIS:
        clean_params = {k: v for k, v in params.items() if v != ''}
        data, msg = call_tushare(api_name, clean_params)
        if data:
            rows = len(data['items'])
            total_rows += rows
            ok_count += 1
            filename = f'{api_name}_macro.json'
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'api_name': api_name,
                    'fields': data['fields'],
                    'items': data['items'],
                    'pulled_at': datetime.now().isoformat()
                }, f, ensure_ascii=False)
            print(f'  OK   | {api_name:25s} | {desc:20s} | {rows:6d} rows')
        else:
            fail_count += 1
            print(f'  FAIL | {api_name:25s} | {desc:20s} | {msg[:50]}')
    
    elapsed = time.time() - start_time
    print(f'\n宏观数据燃烧完成: 成功={ok_count} 失败={fail_count} 总行={total_rows:,} 耗时={elapsed:.1f}s')
    return ok_count, fail_count, total_rows

def generate_burn_report(stats, output_dir):
    """生成燃烧报告"""
    report_path = os.path.join(output_dir, 'burn_report.json')
    report = {
        'burn_engine_version': '1.0',
        'burned_at': datetime.now().isoformat(),
        'token': TUSHARE_TOKEN[:8] + '****',
        'estimated_points_level': '15000+',
        'stats': stats,
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n燃烧报告已保存: {report_path}')

# ============================================================
# 主入口
# ============================================================

def main():
    print('='*60)
    print('Tushare 高性能燃烧引擎 v1.0')
    print('砚坚席位 · 码道(CodeArts) · 2026-09-29')
    print('='*60)
    print(f'Token: {TUSHARE_TOKEN[:8]}...{TUSHARE_TOKEN[-8:]}')
    print(f'并发线程: {MAX_WORKERS}')
    print(f'输出目录: {OUTPUT_DIR}')
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 获取交易日 (最近3个月)
    today = datetime.now().strftime('%Y%m%d')
    start = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
    trade_dates = get_trade_dates(start, today)
    print(f'交易日范围: {start} ~ {today}, 共 {len(trade_dates)} 个交易日')
    
    if not trade_dates:
        print('错误: 未获取到交易日')
        sys.exit(1)
    
    stats = {}
    
    # 1. 燃烧基础数据
    ok, fail, rows = burn_basic_apis(OUTPUT_DIR)
    stats['basic'] = {'ok': ok, 'fail': fail, 'rows': rows}
    
    # 2. 燃烧宏观数据
    ok, fail, rows = burn_macro_apis(OUTPUT_DIR)
    stats['macro'] = {'ok': ok, 'fail': fail, 'rows': rows}
    
    # 3. 燃烧日频数据 (核心)
    ok, fail, rows = burn_daily_apis(trade_dates, OUTPUT_DIR)
    stats['daily'] = {'ok': ok, 'fail': fail, 'rows': rows, 'trade_dates': len(trade_dates)}
    
    # 4. 生成报告
    total_ok = sum(s['ok'] for s in stats.values())
    total_fail = sum(s['fail'] for s in stats.values())
    total_rows = sum(s['rows'] for s in stats.values())
    stats['total'] = {'ok': total_ok, 'fail': total_fail, 'rows': total_rows}
    
    generate_burn_report(stats, OUTPUT_DIR)
    
    print(f'\n{"="*60}')
    print(f'燃烧总结')
    print(f'{"="*60}')
    print(f'  总成功: {total_ok}')
    print(f'  总失败: {total_fail}')
    print(f'  总数据行: {total_rows:,}')
    print(f'  输出目录: {OUTPUT_DIR}')

if __name__ == '__main__':
    main()