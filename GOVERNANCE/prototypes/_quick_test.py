#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""快速验证服务层"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ['API_302AI_KEY'] = os.environ.get('API_302AI_KEY', '')
os.environ['SILICONFLOW_API_KEY'] = os.environ.get('SILICONFLOW_API_KEY', '')

# Test 1: Graphiti Config
from GOVERNANCE.prototypes.graphiti_config import GraphitiConfig
gc = GraphitiConfig()
verify = gc.verify_config()
with open('GOVERNANCE/research/_test_results.txt', 'w', encoding='utf-8') as f:
    f.write(f"=== Graphiti Config ===\nall_pass={verify['all_pass']}\n")
    for check, result in verify['checks'].items():
        f.write(f"  {check}: {'PASS' if result else 'FAIL'}\n")

    # Test 2: Embedding Service (if keys available)
    if os.environ.get('API_302AI_KEY') or os.environ.get('SILICONFLOW_API_KEY'):
        try:
            from GOVERNANCE.prototypes.embedding_service import EmbeddingService
            svc = EmbeddingService()
            health = svc.health_check()
            f.write(f"\n=== Embedding Service ===\n")
            for name, info in health.items():
                status = info['status']
                if status == 'ok':
                    f.write(f"  [{name}] ok dim={info.get('dim','?')} latency={info.get('latency_ms','?')}ms\n")
                else:
                    f.write(f"  [{name}] {status} {info.get('detail','')[:60]}\n")
        except Exception as e:
            f.write(f"\n=== Embedding Service ===\nERROR: {e}\n")

        # Test 3: Rerank Service
        try:
            from GOVERNANCE.prototypes.rerank_service import RerankService
            rsvc = RerankService()
            rhealth = rsvc.health_check()
            f.write(f"\n=== Rerank Service ===\n")
            for name, info in rhealth.items():
                status = info['status']
                if status == 'ok':
                    f.write(f"  [{name}] ok latency={info.get('latency_ms','?')}ms\n")
                else:
                    f.write(f"  [{name}] {status} {info.get('detail','')[:60]}\n")
        except Exception as e:
            f.write(f"\n=== Rerank Service ===\nERROR: {e}\n")
    else:
        f.write("\n=== Embedding/Rerank ===\nSKIPPED: no API keys in env\n")

    f.write("\n=== DONE ===\n")

print("Test results written to GOVERNANCE/research/_test_results.txt")