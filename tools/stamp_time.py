# -*- coding: utf-8 -*-
"""自动打钟器（根治"估记冒称取钟"）
- 行为：读真实钟（与 clock_stamp.py 同源 → 系统时间 + Asia/Shanghai），
  在件内**定位或插入**"时点：北京时间 **YYYY-MM-DD HH:MM**（★由 `stamp_time.py` 实跑取钟）"行
- 只改**该行**；其余内容不动；改后回读自验
用法：
    python stamp_time.py <file>            # 就地写入/替换时点行
    python stamp_time.py <file> --check    # 只检不写：打印件内行 vs 真实钟之差
"""
import pathlib, re, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
TZ = time.strftime("%z")
now = time.localtime()
claimed_line = "时点：北京时间 **%s**（★由 `stamp_time.py` 实跑取钟）" % time.strftime("%Y-%m-%d %H:%M", now)
PAT = re.compile(r"时点：北京时间\s*\**\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})")

def real_minutes():
    return time.mktime(time.strptime(time.strftime("%Y-%m-%d %H:%M", now), "%Y-%m-%d %H:%M"))

def check(p):
    t = p.read_text(encoding="utf-8", errors="replace")
    m = PAT.search(t)
    if not m:
        print("   件内无时点行 ⇒ 建议插入"); return None
    claimed = time.mktime(time.strptime("%s %s" % (m.group(1), m.group(2)), "%Y-%m-%d %H:%M"))
    d = round((claimed - real_minutes())/60)
    print("   件内=%s %s ｜ 真实钟=%s ｜ 偏差=%+d 分钟 ｜ %s" % (
        m.group(1), m.group(2), time.strftime("%Y-%m-%d %H:%M", now), d, "★超阈" if abs(d) > 30 else "在阈内"))
    return d

def stamp(p):
    t = p.read_text(encoding="utf-8", errors="replace")
    if PAT.search(t):
        t2 = PAT.sub(claimed_line, t, count=1)
    else:
        lines = t.split("\n")
        ins = 1 if lines and lines[0].startswith("#") else 0
        lines.insert(ins, "\n- " + claimed_line)
        t2 = "\n".join(lines)
    p.write_text(t2, encoding="utf-8", newline="\n")
    back = p.read_text(encoding="utf-8", errors="replace")
    ok = claimed_line in back
    print("   ★ 已打钟：%s ｜ 回读自验=%s" % (time.strftime("%Y-%m-%d %H:%M", now), "相符" if ok else "不符"))

def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    p = pathlib.Path(sys.argv[1])
    if not p.exists():
        print("   找不到：%s" % p); return 2
    print("  真实钟：%s %s（%s）" % (time.strftime("%Y-%m-%d %H:%M:%S", now), TZ, time.tzname[0]))
    if "--check" in sys.argv:
        check(p); return 0
    stamp(p); return 0

if __name__ == "__main__":
    sys.exit(main())
