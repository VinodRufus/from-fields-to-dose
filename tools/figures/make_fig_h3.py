"""Figure 5: H3, the primary comparison, as paired Workflow C minus Workflow B differences per model under the two
protocol wordings. Panel A, Section 1 wording (composite dose-consequence failure rate; negative favours the hybrid
workflow). Panel B, Section 16 wording (primary endpoint; positive favours the hybrid workflow). Locked-scorer
estimates are computed from the scored run-1 files with analysis/analyze.py's paired clustered bootstrap (seed 2,
2,000 resamples) and must equal results/analysis_primary.txt; written-rule estimates are parsed from
results/analysis_sensitivity_text_rule.txt (tolerance 0.10 block) when that file is present.

Usage: python tools/figures/make_fig_h3.py [--report results/analysis_sensitivity_text_rule.txt] [--out docs/figures/F2D_Figure_5_H3_Both_Wordings]
"""
from __future__ import annotations
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.getcwd())
from common import plt, save, style, load_cells, ORDER, SHORT, BLUE, ORANGE, INK, INK2, GRID
from analysis.analyze import by_scenario, paired_cluster_boot


def locked(cells):
    out = {}
    for m in ORDER:
        B = [r for r in cells[(m, "B")] if not r.get("abstention_case")]
        C = [r for r in cells[(m, "C")] if not r.get("abstention_case")]
        s1 = paired_cluster_boot(by_scenario(C, "dose_consequential"), by_scenario(B, "dose_consequential"))
        s16 = paired_cluster_boot(by_scenario(C, "primary_endpoint"), by_scenario(B, "primary_endpoint"))
        out[m] = {"S1": s1, "S16": s16}
    return out


def text_rule(report):
    if not os.path.exists(report):
        return None
    txt = open(report).read()
    block = txt.split("== H3 under the protocol-text rule at tolerance 0.10")[1].split("== Level 3 rule sensitivity at sensitivity tolerance")[0]
    out = {}
    for m in ORDER:
        mm = re.search(re.escape(m) + r"\s+S1 diff=([+-][\d.]+) \[([+-][\d.]+),([+-][\d.]+)\].*?S16 diff=([+-][\d.]+) \[([+-][\d.]+),([+-][\d.]+)\]", block)
        if not mm:
            raise SystemExit(f"STOP: no H3 text-rule line for {m}")
        v = [float(x) for x in mm.groups()]
        out[m] = {"S1": tuple(v[0:3]), "S16": tuple(v[3:6])}
    return out


def panel(ax, lk, tr, key, title, favour_note, good_sign, text_side="right"):
    ys = list(range(len(ORDER)))[::-1]
    ax.axvline(0, color="#888888", lw=0.9)
    for y, m in zip(ys, ORDER):
        e, lo, hi = lk[m][key]
        met = (hi < 0) if good_sign < 0 else (lo > 0)
        ax.errorbar([e], [y + 0.12], xerr=[[e - lo], [hi - e]], fmt="o", color=BLUE, mfc=BLUE if met else "white", mec=BLUE, ms=6.5, capsize=3, lw=1.3)
        ax.text(0.985 if text_side == "right" else 0.015, y + 0.12, f"{e:+.3f} [{lo:+.3f}, {hi:+.3f}]", transform=ax.get_yaxis_transform(), ha=text_side, va="center", fontsize=7.2, color=INK)
        if tr:
            e2, lo2, hi2 = tr[m][key]
            met2 = (hi2 < 0) if good_sign < 0 else (lo2 > 0)
            ax.errorbar([e2], [y - 0.18], xerr=[[e2 - lo2], [hi2 - e2]], fmt="s", color=ORANGE, mfc=ORANGE if met2 else "white", mec=ORANGE, ms=5.5, capsize=3, lw=1.1)
    ax.set_yticks(ys); ax.set_yticklabels([SHORT[m] for m in ORDER], fontsize=8.6)
    ax.set_xlim(-0.36, 0.36)
    ax.set_title(title, fontsize=9.4, loc="left", color=INK)
    ax.set_xlabel(favour_note, fontsize=8.2, color=INK2)
    style(ax, grid_axis="x")
    ax.set_ylim(-0.7, len(ORDER) - 0.3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="results/analysis_sensitivity_text_rule.txt")
    ap.add_argument("--out", default="docs/figures/F2D_Figure_5_H3_Both_Wordings")
    a = ap.parse_args()
    cells = load_cells()
    lk = locked(cells); tr = text_rule(a.report)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3), dpi=200)
    panel(axes[0], lk, tr, "S1", "A. Section 1 wording: C minus B, composite failure rate", "Difference in composite failure rate (negative favours the hybrid workflow)", -1, text_side="left")
    panel(axes[1], lk, tr, "S16", "B. Section 16 wording: C minus B, primary endpoint", "Difference in primary endpoint (positive favours the hybrid workflow)", +1)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="o", color=BLUE, ls="", ms=6.5, label="Locked scorer (as registered by hash)"),
               Line2D([], [], marker="o", color=BLUE, mfc="white", ls="", ms=6.5, label="Interval includes zero or opposes the hypothesis (hollow)")]
    if tr:
        handles.append(Line2D([], [], marker="s", color=ORANGE, ls="", ms=5.5, label="Protocol's written Level 3 rule (sensitivity)"))
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout()
    save(fig, a.out)
    for m in ORDER:
        print(m, "S1", lk[m]["S1"], "S16", lk[m]["S16"], "text-rule", tr[m] if tr else None)


if __name__ == "__main__":
    main()
