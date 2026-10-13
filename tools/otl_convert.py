# -*- coding: utf-8 -*-
"""otl_convert.py —— OTL 全文形态转换器（2026-10-14 立）

依据：令条「相关文档统一转换为WPS OTL格式…须确保目录结构、修订记录、附件及权限设置等元数据完整无缺」
      ＋ 本席《OTL格式与元数据完整性规范 OTL-SPEC-20261014-CAIRN-01》
形态：乙形态（全文）＝ *.otl.md，正文之后追加 <!-- OTL-META ... --> 元数据块
复算：取文件字节中 "\n<!-- OTL-META" 之前的部分计 SHA-256（承 cairn-otl-signing 技能定义）
纪律：★只增不改（源件不动）｜★写后回读复算必校｜★仅写本席领地（outbox 下之 otl）
用法：python otl_convert.py [--src <目录>] [--dst <目录>]
"""
import argparse, datetime as dt, hashlib, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path.home() / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A新席_石敢当Cairn_20260928"
ACL = "acl: {seat: write-own, 常务局: read, 辩护席位: read, 他席: read-via-bus}"
BY = "cairn-dsh"

META_SEP = "\n<!-- OTL-META"


def body_sha256(b: bytes) -> str:
    """正文摘要＝分隔符之前（含分隔符前之换行规则：取 '\n<!-- OTL-META' 之前）"""
    i = b.find(META_SEP.encode("utf-8"))
    return hashlib.sha256(b if i < 0 else b[:i]).hexdigest()


def convert(src: pathlib.Path, dst_dir: pathlib.Path) -> dict:
    raw = src.read_bytes()
    body = body_sha256(raw)
    out = dst_dir / (src.stem + ".otl.md")
    prev = ""
    if out.exists():                       # 幂等：取上版正文摘要作链
        prev = body_sha256(out.read_bytes())
    meta = (
        "\n<!-- OTL-META\n"
        "otl_meta:\n"
        "  spec: OTL-SPEC-20261014-CAIRN-01\n"
        "  form: full-text            # 乙形态（全文）\n"
        "  source_path: %s\n"
        "  revision: %d\n"
        "  prev_sha256: %s\n"
        "  body_sha256: %s\n"
        "  attachments: []\n"
        "  seat_tree: outbox/otl\n"
        "  %s\n"
        "  archive_ref: archive/docs/<key>/v_<YYYYMMDD_HHMM>.md\n"
        "  converted_at: %s\n"
        "  by: %s\n"
        "-->\n" % (src.name, int(prev != "") + 1, prev or "(首版无上版)", body,
                   ACL, dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"), BY)
    )
    dst_dir.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw + meta.encode("utf-8"))
    # ★写后回读复算必校
    back = body_sha256(out.read_bytes())
    return {"src": src.name, "out": out.name, "in": len(raw), "out_bytes": out.stat().st_size,
            "body_ok": back == body, "sha16": body[:16]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(SEAT / "outbox" / "mem"))
    ap.add_argument("--dst", default=str(SEAT / "outbox" / "otl"))
    a = ap.parse_args()
    src_dir, dst_dir = pathlib.Path(a.src), pathlib.Path(a.dst)
    files = sorted(p for p in src_dir.glob("*.md") if not p.name.endswith(".otl.md"))
    print("  源目录 %s ⇒ %d 件" % (src_dir.name, len(files)))
    ok = bad = 0
    for p in files:
        r = convert(p, dst_dir)
        ok += r["body_ok"]; bad += (not r["body_ok"])
        print("   %s %-58s %7d B ⇒ %8d B ｜ body=%s" % ("✓" if r["body_ok"] else "✗",
              r["src"][:58], r["in"], r["out_bytes"], r["sha16"]))
    print("  ★合计 %d 件 ｜ 复算一致 %d ｜ 不一致 %d" % (len(files), ok, bad))
    print("  ★输出目录：%s" % dst_dir)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
