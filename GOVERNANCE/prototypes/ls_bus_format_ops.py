#!/usr/bin/env python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
ls-bus-format-ops: 总线格式化操作
将不同来源的上下文数据统一为标准总线格式，便于跨席位/跨系统交换

依据: GOVERNANCE/proposals/context_compress_migration_20261007.md
档号: DF-CTX-COMPRESS-2026-1007-YANJIAN-01
"""

import re
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# 标准总线格式 schema
BUS_SCHEMA = {
    'bus_version': '1.0.0',
    'bus_id': '',           # 自动生成
    'timestamp': '',        # 自动生成
    'source': {
        'type': '',         # markdown | json | text | changelog | skill
        'path': '',         # 原始文件路径
        'hash': '',         # SHA3-512[:32]
    },
    'metadata': {
        'doc_id': '',       # 档号（如有）
        'title': '',        # 标题（如有）
        'author': '',       # 作者/席位（如有）
        'created_at': '',   # 原始创建时间（如有）
    },
    'payload': {
        'format': '',       # structured | raw
        'sections': [],     # 结构化分段
        'raw_content': '',  # 原始内容（format=raw时）
    },
    'integrity': {
        'payload_hash': '', # payload的hash
        'verified': False,  # 完整性验证结果
    },
}


def detect_source_type(content: str, file_path: str) -> str:
    """检测来源类型"""
    ext = Path(file_path).suffix.lower()
    if ext == '.json':
        return 'json'
    if ext == '.md':
        # 检查是否是技能文件
        if '---' in content[:100] and 'name:' in content[:200]:
            return 'skill'
        # 检查是否是CHANGELOG
        if content.startswith('# CHANGELOG') or 'CHANGELOG' in content[:50]:
            return 'changelog'
        return 'markdown'
    return 'text'


def compute_hash(data: str) -> str:
    """计算SHA3-512[:32]哈希"""
    return hashlib.sha3_512(data.encode('utf-8')).hexdigest()[:32]


def extract_metadata(content: str, source_type: str) -> Dict:
    """从内容中提取元数据"""
    metadata = {
        'doc_id': '',
        'title': '',
        'author': '',
        'created_at': '',
    }

    # 档号提取
    doc_id_match = re.search(r'档号[：:]\s*(\S+)', content)
    if doc_id_match:
        metadata['doc_id'] = doc_id_match.group(1)

    # 标题提取（第一个#标题）
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        metadata['title'] = title_match.group(1).strip()

    # 作者/席位提取
    author_patterns = [
        r'（码道·[^）]+）',
        r'（[^）]*席[^）]*）',
        r'·\s*(砚坚|白秉烛|顾权|Moon|Kimi|Codex)',
        r'作者[：:]\s*(\S+)',
    ]
    for pattern in author_patterns:
        match = re.search(pattern, content[:500])
        if match:
            metadata['author'] = match.group(0).strip('（）·： ')
            break

    # 创建时间提取
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',
        r'(\d{4}-\d{2}-\d{2})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, content[:500])
        if match:
            metadata['created_at'] = match.group(1)
            break

    # 技能文件的frontmatter解析
    if source_type == 'skill':
        fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            name_match = re.search(r'^name:\s*(.+)$', fm_text, re.MULTILINE)
            if name_match:
                metadata['title'] = name_match.group(1).strip()
            version_match = re.search(r'version:\s*["\']?([^"\'\n]+)', fm_text)
            if version_match:
                metadata['doc_id'] = f"SKILL-{version_match.group(1).strip()}"

    return metadata


def parse_sections(content: str, source_type: str) -> List[Dict]:
    """将内容解析为结构化分段"""
    sections = []

    if source_type == 'json':
        try:
            data = json.loads(content)
            # JSON按顶层键分段
            for key, value in data.items():
                sections.append({
                    'id': f'sec_{len(sections)+1}',
                    'key': key,
                    'type': type(value).__name__,
                    'preview': str(value)[:200],
                    'char_count': len(str(value)),
                })
            return sections
        except json.JSONDecodeError:
            pass

    # Markdown/文本按标题分段
    lines = content.split('\n')
    current_section = None
    section_num = 0

    for i, line in enumerate(lines):
        # 检测标题行
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            # 保存上一个section
            if current_section:
                current_section['end_line'] = i
                current_section['char_count'] = len(current_section['content'])
                current_section['content'] = current_section['content'][:500]  # 预览限500字
                sections.append(current_section)

            section_num += 1
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            current_section = {
                'id': f'sec_{section_num}',
                'level': level,
                'title': title,
                'start_line': i + 1,
                'end_line': None,
                'content': '',
                'char_count': 0,
            }
        else:
            if current_section is not None:
                current_section['content'] += line + '\n'
            else:
                # 标题前的内容作为section_0
                if line.strip():
                    if not sections or sections[-1].get('id') != 'sec_0':
                        section_num += 1
                        current_section = {
                            'id': f'sec_{section_num}',
                            'level': 0,
                            'title': '(前言)',
                            'start_line': 1,
                            'end_line': None,
                            'content': '',
                            'char_count': 0,
                        }
                    if current_section:
                        current_section['content'] += line + '\n'

    # 保存最后一个section
    if current_section:
        current_section['end_line'] = len(lines)
        current_section['char_count'] = len(current_section['content'])
        current_section['content'] = current_section['content'][:500]
        sections.append(current_section)

    return sections


def format_to_bus(content: str, file_path: str) -> Dict:
    """将内容格式化为标准总线格式"""
    source_type = detect_source_type(content, file_path)
    source_hash = compute_hash(content)
    metadata = extract_metadata(content, source_type)

    # 判断是否可以结构化
    can_structure = source_type in ('markdown', 'skill', 'changelog') or source_type == 'json'
    payload_format = 'structured' if can_structure else 'raw'

    sections = []
    raw_content = ''
    if can_structure:
        sections = parse_sections(content, source_type)
    else:
        raw_content = content[:2000]  # raw模式限2000字

    payload = {
        'format': payload_format,
        'sections': sections,
        'raw_content': raw_content,
    }

    payload_hash = compute_hash(json.dumps(payload, ensure_ascii=False))

    bus_record = {
        'bus_version': BUS_SCHEMA['bus_version'],
        'bus_id': f"BUS-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{source_hash[:8]}",
        'timestamp': datetime.now().isoformat(),
        'source': {
            'type': source_type,
            'path': file_path,
            'hash': source_hash,
        },
        'metadata': metadata,
        'payload': payload,
        'integrity': {
            'payload_hash': payload_hash,
            'verified': True,  # 初始生成时自验通过
        },
    }

    return bus_record


def verify_bus_record(bus_record: Dict, original_path: str) -> Dict:
    """验证总线记录的完整性"""
    verification = {
        'bus_id': bus_record.get('bus_id', ''),
        'source_exists': Path(original_path).exists(),
    }

    if verification['source_exists']:
        original_content = Path(original_path).read_text(encoding='utf-8')
        original_hash = compute_hash(original_content)
        verification['source_hash_match'] = (original_hash == bus_record['source']['hash'])

    # 验证payload hash
    payload = bus_record.get('payload', {})
    payload_hash = compute_hash(json.dumps(payload, ensure_ascii=False))
    verification['payload_hash_match'] = (payload_hash == bus_record['integrity']['payload_hash'])

    verification['all_passed'] = all([
        verification.get('source_exists', False),
        verification.get('source_hash_match', False),
        verification.get('payload_hash_match', False),
    ])

    return verification


def ls_bus_format(input_path: str, output_path: Optional[str] = None) -> Dict:
    """主入口：总线格式化"""
    content = Path(input_path).read_text(encoding='utf-8')
    bus_record = format_to_bus(content, input_path)

    result = {
        'bus_record': bus_record,
        'verification': verify_bus_record(bus_record, input_path),
    }

    if output_path:
        Path(output_path).write_text(
            json.dumps(bus_record, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        result['output_path'] = output_path

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='总线格式化操作')
    parser.add_argument('input', help='输入文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径', default=None)
    args = parser.parse_args()

    result = ls_bus_format(args.input, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))