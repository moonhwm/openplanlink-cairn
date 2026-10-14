#!/usr/bin/env python
"""
ultra-compress-ops: 极致压缩工具
将长文档压缩为结构化摘要，保留关键决策/数据/链接

依据: GOVERNANCE/proposals/context_compress_migration_20261007.md
档号: DF-CTX-COMPRESS-2026-1007-YANJIAN-01
"""

import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def extract_structure(content: str) -> Dict:
    """识别文档结构"""
    lines = content.split('\n')
    structure = {
        'headings': [],
        'lists': [],
        'tables': [],
        'code_blocks': [],
        'links': [],
    }

    for i, line in enumerate(lines):
        # 标题
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            structure['headings'].append({
                'level': level,
                'text': line.lstrip('#').strip(),
                'line': i + 1,
            })

        # 列表
        if re.match(r'^[\-\*\d+\.]\s', line):
            structure['lists'].append({
                'line': i + 1,
                'text': line.strip(),
            })

        # 表格
        if '|' in line and line.strip().startswith('|'):
            structure['tables'].append({
                'line': i + 1,
                'text': line.strip(),
            })

        # 链接
        for match in re.finditer(r'https?://[^\s\)]+', line):
            structure['links'].append({
                'url': match.group(0),
                'line': i + 1,
            })

    return structure


def extract_key_elements(content: str, structure: Dict) -> Dict:
    """提取关键决策点、数据指标、链接URL、档号"""
    # 档号
    doc_id_match = re.search(r'档号[：:]\s*(\S+)', content)
    doc_id = doc_id_match.group(1) if doc_id_match else 'unknown'

    # 关键决策（含"决定"、"确认"、"通过"、"批准"等关键词的段落）
    decision_keywords = ['决定', '确认', '通过', '批准', '共识', '裁定', '裁决', '结论']
    decisions = []
    for heading in structure['headings']:
        for kw in decision_keywords:
            if kw in heading['text']:
                decisions.append(heading['text'])
                break

    # 遗留事项（含"遗留"、"待办"、"TODO"、"待确认"等关键词）
    pending_keywords = ['遗留', '待办', 'TODO', '待确认', '待机主', '待启动', 'pending']
    pending_items = []
    for item in structure['lists']:
        for kw in pending_keywords:
            if kw in item['text']:
                pending_items.append(item['text'])
                break

    # 数据指标（表格中的数字数据）
    data_metrics = []
    for table_row in structure['tables']:
        if re.search(r'\d+', table_row['text']):
            data_metrics.append(table_row['text'])

    # 关键链接（去重）
    seen_urls = set()
    key_links = []
    for link in structure['links']:
        if link['url'] not in seen_urls:
            seen_urls.add(link['url'])
            key_links.append(link['url'])

    return {
        'doc_id': doc_id,
        'decisions': decisions,
        'pending_items': pending_items,
        'data_metrics': data_metrics[:10],  # 最多10条
        'key_links': key_links[:10],  # 最多10条
    }


def generate_summary(content: str, structure: Dict, key_elements: Dict) -> str:
    """生成<500字结构化摘要"""
    lines = []

    lines.append(f"档号: {key_elements['doc_id']}")

    # 核心议题（从一级标题提取）
    h1_headings = [h for h in structure['headings'] if h['level'] == 1]
    if h1_headings:
        lines.append(f"核心议题: {h1_headings[0]['text']}")
    else:
        # 从前100字提取
        first_100 = content[:100].replace('\n', ' ').strip()
        lines.append(f"核心议题: {first_100[:60]}...")

    # 关键决策
    if key_elements['decisions']:
        lines.append("关键决策:")
        for d in key_elements['decisions'][:5]:
            lines.append(f"  - {d}")

    # 数据指标
    if key_elements['data_metrics']:
        lines.append("数据指标:")
        for m in key_elements['data_metrics'][:5]:
            lines.append(f"  - {m}")

    # 关键链接
    if key_elements['key_links']:
        lines.append("关键链接:")
        for l in key_elements['key_links'][:5]:
            lines.append(f"  - {l}")

    # 遗留事项
    if key_elements['pending_items']:
        lines.append("遗留事项:")
        for p in key_elements['pending_items'][:5]:
            lines.append(f"  - {p}")

    summary = '\n'.join(lines)

    # 确保不超过500字
    if len(summary) > 500:
        summary = summary[:497] + '...'

    return summary


def generate_compression_report(original: str, summary: str) -> Dict:
    """生成压缩比报告"""
    original_chars = len(original)
    summary_chars = len(summary)
    original_tokens = original_chars // 4
    summary_tokens = summary_chars // 4

    return {
        'timestamp': datetime.now().isoformat(),
        'original_chars': original_chars,
        'summary_chars': summary_chars,
        'original_tokens_est': original_tokens,
        'summary_tokens_est': summary_tokens,
        'compression_ratio': round(original_chars / max(summary_chars, 1), 1),
        'meets_10to1_target': original_chars / max(summary_chars, 1) >= 10,
    }


def ultra_compress(input_path: str, output_path: Optional[str] = None) -> Dict:
    """主入口：极致压缩"""
    content = Path(input_path).read_text(encoding='utf-8')

    structure = extract_structure(content)
    key_elements = extract_key_elements(content, structure)
    summary = generate_summary(content, structure, key_elements)
    report = generate_compression_report(content, summary)

    result = {
        'summary': summary,
        'compression_report': report,
        'key_elements': key_elements,
        'input_path': input_path,
    }

    if output_path:
        Path(output_path).write_text(summary, encoding='utf-8')
        result['output_path'] = output_path

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='极致压缩工具')
    parser.add_argument('input', help='输入文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径', default=None)
    args = parser.parse_args()

    result = ultra_compress(args.input, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))