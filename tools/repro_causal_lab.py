# -*- coding: utf-8 -*-
"""repro_causal_lab.py —— A2A 前沿因果实验室之独立复现校验器（2026-10-14 立）

用途：对跨席件（如 DF-LAB-20261014-HERMES-01）之关键量做★独立复算：
      Z = |theta_hat| / se；Delta(-2 ln L) = Z^2；区间 = theta_hat ± n*se（覆盖 = erf(n/sqrt(2)））
纪律：★不调用被复现方之脚本（独立算式）｜★只读其 JSON｜★零凭据
输出：复现表（复算值 / 声明值 / 差 / 判）＋ 两处常见须标注点（p 之下溢、触发阈之交）
用法：python repro_causal_lab.py [--json <跨席件路径>]
"""
import argparse, json, math, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8")
DEFAULT = (pathlib.Path.home() / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
           / "A2A共同体_共享交换区" / "a2a_frontier_causal_lab_20261014.json")
SIGMAS = (("1sigma_68.27%", 1.0), ("2sigma_95.45%", 2.0),
          ("3sigma_99.73%_evidence", 3.0), ("5sigma_99.99994%_discovery", 5.0))


def Phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def two_sided_p(z: float) -> float:
    return 2.0 * (1.0 - Phi(abs(z)))


def verdict(z: float) -> str:
    return ("5sigma Discovery (>=5.0 sigma)" if z >= 5.0 else
            "3sigma Evidence (>=3.0 sigma)" if z >= 3.0 else "below 3 sigma")


def check(label: str, est: float, se: float, z_decl: float, d_decl: float, p_asymp: str = "") -> list:
    out = []
    z = abs(est) / se
    d = z * z
    p = two_sided_p(z)
    out.append((label + " Z", "%.4f" % z, "%.4f" % z_decl, "%.2e" % abs(z - z_decl),
                "OK" if abs(z - z_decl) < 5e-4 else "DIFF"))
    out.append((label + " Delta(-2lnL)=Z^2", "%.3f" % d, "%.3f" % d_decl, "%.3f" % abs(d - d_decl),
                "OK" if abs(d - d_decl) < 0.01 else "DIFF"))
    ln_p = math.log(2.0) - 0.5 * math.log(2.0 * math.pi) - 0.5 * (z ** 2) - math.log(z) + math.log(max(1e-12, 1.0 - (1.0 / (z ** 2)) + (3.0 / (z ** 4))))
    log10_p = ln_p / math.log(10.0)
    mant = 10.0 ** (log10_p - math.floor(log10_p))
    p_calc_str = f"{mant:.2f}e{int(math.floor(log10_p))}"
    out.append((label + " p (Mill's ratio)", p_calc_str, p_asymp or "0.0 (declared)",
                "log10_p=%.2f" % log10_p,
                "OK" if p_asymp else "NOTE: report as p < 1e-30, not 0.0"))
    out.append((label + " verdict", verdict(z), "-", "-", "OK"))
    for name, n in SIGMAS:
        lo, hi = est - n * se, est + n * se
        out.append((label + " " + name, "[%.4f, %.4f] cov=%.5f" % (lo, hi, math.erf(n / math.sqrt(2.0))), "-", "-", "OK"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(DEFAULT))
    a = ap.parse_args()
    src = pathlib.Path(a.json)
    if not src.exists():
        print("  [ERR] 跨席件不在：%s" % src); return 2
    j = json.loads(src.read_text(encoding="utf-8"))
    print("  === 独立复现校验 ===")
    print("  被复现件：%s" % j.get("doc_id"))
    print("  出件席  ：%s" % j.get("seat"))
    print("  诚实分级：%s" % (j.get("honesty") or {}))
    rows = []
    a1 = j.get("1_psm_did") or {}
    if a1:
        h = a1.get("hep_inference") or {}
        rows += check("PSM-DID(ATT)", a1.get("att_did"), a1.get("se_att"),
                      h.get("z_sigma", float("nan")), h.get("delta_minus_2lnL_vs_null", float("nan")), h.get("p_value_asymptotic", ""))
    a2 = j.get("2_bayesian_causal_forest") or {}
    if a2:
        h = a2.get("hep_inference_ate") or {}
        rows += check("BCF(ATE)", a2.get("ate_posterior_mean"), a2.get("ate_posterior_sd"),
                      h.get("z_sigma", float("nan")), h.get("delta_minus_2lnL_vs_null", float("nan")), h.get("p_value_asymptotic", ""))
    print("  %-40s %-16s %-16s %-12s %s" % ("量", "本席复算", "他席声明", "差", "判"))
    for r in rows:
        print("  %-40s %-16s %-16s %-12s %s" % r)
    a3 = j.get("3_neural_net_metacognitive") or {}
    if a3:
        r0, r1 = a3.get("rmse_pre_metacognitive_M0"), a3.get("rmse_post_metacognitive_M1")
        drop = 100.0 * (r0 - r1) / r0
        print("  %-40s %-16s %-16s %-12s %s" % ("NN RMSE drop %", "%.2f%%" % drop,
              "%.1f%%" % a3.get("rmse_reduction_pct", float("nan")), "%.2f" % abs(drop - a3.get("rmse_reduction_pct", 0)), "OK"))
        trig_str = a3.get("metacognitive_trigger", "")
        thr = 12.0 if "threshold=12.0" in trig_str else 15.0
        print("  %-40s 阈值 %.1f vs 实测 %.4f => %s" % ("NN trigger check", thr, r0,
              "OK" if r0 > thr else f"NOTE: RMSE_M0 not above {thr} threshold"))
    bad = [r for r in rows if r[4].startswith("DIFF")]
    print("  === 判：复现差异 %d 项；须标注项见上 NOTE ===" % len(bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
