import json,pathlib,sys
sys.stdout.reconfigure(encoding='utf-8')
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text(encoding='utf-8'))
pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(d['public_key_hex']))
payload = bytes.fromhex(d['signature_hex'])
rows = [json.loads(l) for l in (pathlib.Path(sys.argv[2])).read_text(encoding='utf-8').splitlines() if l.strip()]
core = {k: v for k, v in rows[-1].items() if k != 'hash'}
msg = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode('utf-8')
try:
    pub.verify(payload, msg)
    print('  ✅ 独立进程验证：签名有效（且内容未被改）')
    print('  ★ 该进程【没有私钥】—— 只读了样张里的公钥')
except Exception as e:
    print('  ★ 独立进程验证：失败 ——', type(e).__name__)
    sys.exit(1)
