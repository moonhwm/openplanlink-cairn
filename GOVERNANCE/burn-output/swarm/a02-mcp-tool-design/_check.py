import re, sys, glob, os

base = os.path.dirname(os.path.abspath(__file__))

def check(path):
    with open(path, encoding='utf-8') as f:
        t = f.read()
    hanzi = len(re.findall(r'[\u4e00-\u9fff]', t))
    # sections: markdown ## headings (>=3 required)
    sections = len(re.findall(r'^##\s+\S', t, re.M))
    has_code_or_list = ('```' in t) or bool(re.search(r'^\s*[-*]\s+\S', t, re.M))
    # secrets heuristics
    secret_pat = re.compile(r'(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|-----BEGIN|api[_-]?key\s*[:=]\s*[\"\']?[A-Za-z0-9]{12,}|password\s*[:=]\s*[\"\']?[^\s\"\']{8,})', re.I)
    has_secret = bool(secret_pat.search(t))
    bad_promise = bool(re.search(r'(保证.{0,6}(收益|盈利|赚钱|翻倍)|稳赚|包赚|立即买入|马上转账|付费解锁|收费群)', t))
    ok = hanzi >= 1500 and sections >= 3 and has_code_or_list and not has_secret and not bad_promise
    return ok, hanzi, sections, has_code_or_list, has_secret, bad_promise

total_attempt = 0
total_pass = 0
for path in sorted(glob.glob(os.path.join(base, '[0-9][0-9].md'))):
    ok, h, s, cl, sec, bp = check(path)
    total_attempt += 1
    if ok:
        total_pass += 1
    print(f"{os.path.basename(path)}: {'PASS' if ok else 'FAIL'} hanzi={h} sections={s} code/list={cl} secret={sec} promise={bp}")
print(f"TOTAL: {total_pass}/{total_attempt} passed")
