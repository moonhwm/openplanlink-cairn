#!/usr/bin/env python
"""
context-pruner: 上下文裁剪工具
识别并移除冗余信息（重复指令、已过期事项、无关上下文）

依据: GOVERNANCE/proposals/context_compress_migration_20261007.md
档号: DF-CTX-COMPRESS-2026-1007-YANJIAN-01
"""

import re
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def scan_context(content: str) -> Dict:
    """扫描上下文，标记冗余信息类别"""
    lines = content.split('\n')
    markers = {
        'duplicate_instructions': [],
        'expired_items': [],
        'irrelevant_context': [],
        'redundant_references': [],
    }

    # 1. 重复指令检测：同一指令出现>2次
    instruction_pattern = re.compile(r'^[>\-]\s*(.+)', re.MULTILINE)
    instructions = {}
    for match in instruction_pattern.finditer(content):
        text = match.group(1).strip()[:80]
        if text not in instructions:
            instructions[text] = []
        instructions[text].append(match.start())

    for text, positions in instructions.items():
        if len(positions) > 2:
            markers['duplicate_instructions'].append({
                'text': text,
                'count': len(positions),
                'positions': positions,
            })

    # 2. 已过期事项检测：TODO已完成、遗留已解决
    completed_pattern = re.compile(r'(已完成|✅|DONE|resolved|已解决)', re.IGNORECASE)
    for i, line in enumerate(lines):
        if completed_pattern.search(line):
            markers['expired_items'].append({
                'line': i + 1,
                'text': line.strip()[:100],
                'reason': 'completed_or_resolved',
            })

    # 3. 冗余引用检测：同一文档被多次引用
    ref_pattern = re.compile(r'GOVERNANCE/[^\s\)]+\.md')
    refs = {}
    for match in ref_pattern.finditer(content):
        path = match.group(0)
        if path not in refs:
            refs[path] = []
        refs[path].append(match.start())

    for path, positions in refs.items():
        if len(positions) > 1:
            markers['redundant_references'].append({
                'path': path,
                'count': len(positions),
                'positions': positions,
            })

    return markers


def prune_context(content: str, markers: Dict) -> Tuple[str, List[Dict]]:
    """裁剪上下文，移除标记内容，保留核心信息"""
    lines = content.split('\n')
    pruned_lines = []
    prune_log = []

    # 裁剪已过期事项行
    expired_line_nums = {item['line'] - 1 for item in markers['expired_items']}

    for i, line in enumerate(lines):
        if i in expired_line_nums:
            prune_log.append({
                'action': 'remove_expired',
                'line': i + 1,
                'content': line.strip()[:80],
                'reason': 'completed_or_resolved',
            })
            continue
        pruned_lines.append(line)

    pruned_content = '\n'.join(pruned_lines)

    # 裁剪冗余引用（保留首次，后续改为指针引用）
    for ref in markers['redundant_references']:
        path = ref['path']
        positions = ref['positions']
        # 保留首次完整引用，后续替换为指针
        for i, pos in enumerate(positions[1:], 1):
            # 找到该位置所在的行
            line_num = content[:pos].count('\n')
            if line_num < len(pruned_lines):
                original = pruned_lines[line_num]
                pruned_lines[line_num] = original.replace(
                    path, f'[→见前文引用: {path}]'
                )
                prune_log.append({
                    'action': 'replace_redundant_ref',
                    'line': line_num + 1,
                    'original_ref': path,
                    'reason': 'redundant_reference',
                })

    pruned_content = '\n'.join(pruned_lines)

    return pruned_content, prune_log


def generate_prune_report(original: str, pruned: str, prune_log: List[Dict]) -> Dict:
    """生成裁剪报告"""
    original_tokens = len(original) // 4  # 粗略token估算
    pruned_tokens = len(pruned) // 4
    reduction = original_tokens - pruned_tokens

    return {
        'timestamp': datetime.now().isoformat(),
        'original_chars': len(original),
        'pruned_chars': len(pruned),
        'original_tokens_est': original_tokens,
        'pruned_tokens_est': pruned_tokens,
        'reduction_tokens': reduction,
        'reduction_pct': round(reduction / max(original_tokens, 1) * 100, 1),
        'prune_actions': len(prune_log),
        'log': prune_log,
    }


def context_pruner(input_path: str, output_path: Optional[str] = None) -> Dict:
    """主入口：上下文裁剪"""
    content = Path(input_path).read_text(encoding='utf-8')

    markers = scan_context(content)
    pruned, prune_log = prune_context(content, markers)
    report = generate_prune_report(content, pruned, prune_log)

    if output_path:
        Path(output_path).write_text(pruned, encoding='utf-8')
        report['output_path'] = output_path

    report['input_path'] = input_path
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='上下文裁剪工具')
    parser.add_argument('input', help='输入文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径', default=None)
    args = parser.parse_args()

    report = context_pruner(args.input, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))