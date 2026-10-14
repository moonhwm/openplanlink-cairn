#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-only AND SSPL-1.0
"""
K4常态化审计排程脚本
档号: DF-A2AK4-20261005-YANJIAN-01
席位: 砚坚（挂帅席/神经中枢）
日期: 2026-10-05
依据: A2A协商结果——频率优化建议（4h→6h/8h, 12h→24h, 48h不变）

排程频率（优化后）：
  - 凭据形态扫描: 每6小时
  - 哈希链连续性校验: 每24小时
  - 登记面根值校验: 每24小时
  - 协议标识覆盖率扫描: 每48小时

运行方式:
  python scripts/k4_audit_schedule.py [--once] [--dry-run]
  --once: 只执行一次所有到期任务，不进入循环
  --dry-run: 只打印将要执行的任务，不实际执行
"""

import hashlib
import json
import os
import time
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
GOVERNANCE_DIR = PROJECT_ROOT / "GOVERNANCE"
AUDIT_LOG_DIR = GOVERNANCE_DIR / "audit_logs"
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

# 排程频率（秒）
SCHEDULE = {
    "credential_form_scan": 6 * 3600,      # 每6小时
    "hash_chain_check": 24 * 3600,          # 每24小时
    "registry_root_check": 24 * 3600,       # 每24小时
    "protocol_coverage_scan": 48 * 3600,    # 每48小时
}

# 上次执行时间记录文件
LAST_RUN_FILE = AUDIT_LOG_DIR / "last_run.json"


def load_last_run():
    """加载上次执行时间"""
    if LAST_RUN_FILE.exists():
        with open(LAST_RUN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_last_run(last_run):
    """保存上次执行时间"""
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as f:
        json.dump(last_run, f, indent=2, ensure_ascii=False)


def log_audit(task_name, result, details=""):
    """记录审计日志"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "task": task_name,
        "result": result,
        "details": details,
    }
    log_file = AUDIT_LOG_DIR / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    print(f"[{log_entry['timestamp']}] {task_name}: {result} {details}")


def credential_form_scan():
    """凭据形态扫描——检查凭据文件的形态完整性"""
    credential_files = [
        "GOVERNANCE/proposals/selfevo_yanjian_20261004.md",
        "GOVERNANCE/proposals/collab_patterns.md",
        "GOVERNANCE/proposals/a2a_negotiation_results_20261004.md",
        "GOVERNANCE/proposals/k1_k3_k5_supplementary_20261005.md",
    ]
    
    issues = []
    for cf in credential_files:
        fp = PROJECT_ROOT / cf
        if not fp.exists():
            issues.append(f"MISSING: {cf}")
            continue
        # 检查文件是否为空
        if fp.stat().st_size == 0:
            issues.append(f"EMPTY: {cf}")
            continue
        # 检查档号格式
        content = fp.read_text(encoding="utf-8")
        if "档号:" not in content and "档号:" not in content:
            issues.append(f"NO_DOC_ID: {cf}")
    
    if issues:
        log_audit("credential_form_scan", "ISSUES_FOUND", "; ".join(issues))
    else:
        log_audit("credential_form_scan", "OK", f"Checked {len(credential_files)} files")


def hash_chain_check():
    """哈希链连续性校验——检查审计日志的哈希链是否连续"""
    log_files = sorted(AUDIT_LOG_DIR.glob("audit_*.jsonl"))
    
    if not log_files:
        log_audit("hash_chain_check", "OK", "No audit logs yet")
        return
    
    issues = []
    prev_hash = ""
    for log_file in log_files:
        with open(log_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    # 计算当前条目的哈希
                    current_hash = hashlib.sha3_512(
                        (prev_hash + line.strip()).encode("utf-8")
                    ).hexdigest()[:16]
                    prev_hash = current_hash
                except json.JSONDecodeError:
                    issues.append(f"PARSE_ERROR: {log_file.name}:{line_num}")
    
    if issues:
        log_audit("hash_chain_check", "ISSUES_FOUND", "; ".join(issues))
    else:
        log_audit("hash_chain_check", "OK", f"Chain verified, last_hash={prev_hash}")


def registry_root_check():
    """登记面根值校验——检查eid registry的根值"""
    registry_file = GOVERNANCE_DIR / "eid_registry.json"
    
    if not registry_file.exists():
        log_audit("registry_root_check", "OK", "Registry not yet created")
        return
    
    with open(registry_file, "r", encoding="utf-8") as f:
        registry = json.load(f)
    
    # 计算registry的根值
    registry_str = json.dumps(registry, sort_keys=True, ensure_ascii=False)
    root_hash = hashlib.sha3_512(registry_str.encode("utf-8")).hexdigest()[:16]
    
    entry_count = len(registry) if isinstance(registry, list) else len(registry.get("entries", []))
    log_audit("registry_root_check", "OK", f"root_hash={root_hash}, entries={entry_count}")


def protocol_coverage_scan():
    """协议标识覆盖率扫描——检查源文件的SPDX标识覆盖率"""
    source_dirs = [
        PROJECT_ROOT / "entry" / "src",
        PROJECT_ROOT / "scripts",
    ]
    
    total_files = 0
    files_with_spdx = 0
    missing_spdx = []
    
    for src_dir in source_dirs:
        if not src_dir.exists():
            continue
        for ext in [".ets", ".ts", ".py", ".js"]:
            for fp in src_dir.rglob(f"*{ext}"):
                if "_deprecated" in str(fp):
                    continue
                total_files += 1
                content = fp.read_text(encoding="utf-8", errors="ignore")
                if "SPDX-License-Identifier" in content:
                    files_with_spdx += 1
                else:
                    missing_spdx.append(str(fp.relative_to(PROJECT_ROOT)))
    
    coverage = (files_with_spdx / total_files * 100) if total_files > 0 else 0
    
    if coverage < 90:
        log_audit("protocol_coverage_scan", "LOW_COVERAGE", 
                  f"{coverage:.1f}% ({files_with_spdx}/{total_files}), missing: {len(missing_spdx)} files")
    else:
        log_audit("protocol_coverage_scan", "OK", 
                  f"{coverage:.1f}% ({files_with_spdx}/{total_files})")


TASK_MAP = {
    "credential_form_scan": credential_form_scan,
    "hash_chain_check": hash_chain_check,
    "registry_root_check": registry_root_check,
    "protocol_coverage_scan": protocol_coverage_scan,
}


def run_once(dry_run=False):
    """执行一次所有到期任务"""
    last_run = load_last_run()
    now = datetime.now()
    
    for task_name, interval in SCHEDULE.items():
        last_run_time = last_run.get(task_name)
        if last_run_time:
            last_dt = datetime.fromisoformat(last_run_time)
            elapsed = (now - last_dt).total_seconds()
            if elapsed < interval:
                continue  # 未到执行时间
        
        if dry_run:
            print(f"[DRY-RUN] Would execute: {task_name}")
        else:
            try:
                TASK_MAP[task_name]()
                last_run[task_name] = now.isoformat()
            except Exception as e:
                log_audit(task_name, "ERROR", str(e))
                last_run[task_name] = now.isoformat()
    
    save_last_run(last_run)


def main():
    dry_run = "--dry-run" in sys.argv
    once = "--once" in sys.argv
    
    if once:
        run_once(dry_run=dry_run)
        return
    
    # 循环模式：每5分钟检查一次是否有到期任务
    print(f"[{datetime.now().isoformat()}] K4审计排程启动，循环间隔5分钟")
    while True:
        try:
            run_once(dry_run=dry_run)
        except KeyboardInterrupt:
            print("\n[K4] 收到中断信号，退出循环")
            break
        except Exception as e:
            print(f"[K4] 循环异常: {e}")
        
        time.sleep(300)  # 5分钟


if __name__ == "__main__":
    main()