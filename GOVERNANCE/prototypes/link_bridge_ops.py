#!/usr/bin/env python
"""
link-bridge-ops: 链路桥接工具
建立压缩摘要与原始文档的桥接链接，确保可追溯

依据: GOVERNANCE/proposals/context_compress_migration_20261007.md
档号: DF-CTX-COMPRESS-2026-1007-YANJIAN-01
"""

import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def compute_hmac_sha3_512(data: str) -> str:
    """计算HMAC-SHA3-512签名（简化版：使用SHA3-512哈希）"""
    return hashlib.sha3_512(data.encode('utf-8')).hexdigest()[:32]


def build_bridge_index(summary_path: str, original_path: str) -> Dict:
    """建立摘要→原文的桥接索引"""
    summary_content = Path(summary_path).read_text(encoding='utf-8')
    original_content = Path(original_path).read_text(encoding='utf-8')

    # 计算签名
    summary_hash = compute_hmac_sha3_512(summary_content)
    original_hash = compute_hmac_sha3_512(original_content)

    # 提取档号
    import re
    doc_id_match = re.search(r'档号[：:]\s*(\S+)', original_content)
    doc_id = doc_id_match.group(1) if doc_id_match else 'unknown'

    # 建立映射
    bridge_index = {
        'bridge_id': f"BR-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        'doc_id': doc_id,
        'summary': {
            'path': summary_path,
            'hash': summary_hash,
            'char_count': len(summary_content),
        },
        'original': {
            'path': original_path,
            'hash': original_hash,
            'char_count': len(original_content),
        },
        'mapping': {
            'algorithm': 'SHA3-512',
            'hash_length': 32,
            'verification': 'full_content_hash',
        },
        'created_at': datetime.now().isoformat(),
        'status': 'active',
    }

    return bridge_index


def verify_bridge(bridge_index: Dict) -> Dict:
    """验证桥接索引的完整性"""
    summary_path = bridge_index['summary']['path']
    original_path = bridge_index['original']['path']

    verification = {
        'bridge_id': bridge_index['bridge_id'],
        'summary_exists': Path(summary_path).exists(),
        'original_exists': Path(original_path).exists(),
    }

    if verification['summary_exists']:
        summary_content = Path(summary_path).read_text(encoding='utf-8')
        summary_hash = compute_hmac_sha3_512(summary_content)
        verification['summary_hash_match'] = (summary_hash == bridge_index['summary']['hash'])

    if verification['original_exists']:
        original_content = Path(original_path).read_text(encoding='utf-8')
        original_hash = compute_hmac_sha3_512(original_content)
        verification['original_hash_match'] = (original_hash == bridge_index['original']['hash'])

    verification['all_passed'] = all([
        verification.get('summary_exists', False),
        verification.get('original_exists', False),
        verification.get('summary_hash_match', False),
        verification.get('original_hash_match', False),
    ])

    return verification


def link_bridge(summary_path: str, original_path: str, output_path: Optional[str] = None) -> Dict:
    """主入口：链路桥接"""
    bridge_index = build_bridge_index(summary_path, original_path)
    verification = verify_bridge(bridge_index)

    result = {
        'bridge_index': bridge_index,
        'verification': verification,
    }

    if output_path:
        Path(output_path).write_text(
            json.dumps(bridge_index, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        result['output_path'] = output_path

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='链路桥接工具')
    parser.add_argument('summary', help='摘要文件路径')
    parser.add_argument('original', help='原文文件路径')
    parser.add_argument('-o', '--output', help='桥接索引输出路径', default=None)
    args = parser.parse_args()

    result = link_bridge(args.summary, args.original, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))