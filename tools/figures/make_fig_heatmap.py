"""Figure 9: composite dose-consequence failure rate by stratum (complexity, age band, generation method, documentation
challenge) for each model, Workflow B (left) and Workflow C (right), as heat maps. Rates are read from
results/by_stratum_run1.csv (tools/by_stratum.py); the drug strata are left to the CSV and Figure 2. Challenge strata
overlap and do not sum to the total. Sequential single-hue scale, 0 to 1.

Usage: python tools/figures/make_fig_heatmap.py [--csv results/by_stratum_run1.csv] [--out docs/figures/F2D_Figure_9_Composite_Failure_by_Stratum]
"""
from __future__ import annotations
import argparse, csv, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import plt, save, ORDER, SHORT, INK, INK2, BAND_LABEL
from matplotlib.colors import LinearSegmentedColormap

KINDS = [("complexity", "Complexity"), ("age_band", "Age band"), ("generation", "Generation"), ("challenge", "Challenge")]
NICE_CH = {"birth_weight": "birth weight present", "concentration_volume": "concentration and volume", "derive_per_dose": "per-dose amount withheld",
           "discontinued_same_drug": "discontinued order, same drug", "dose_cap": "maximum in the order", "lb_documentation": "weight in pounds",
           "mcg_drug": "microgram drug", "multiple_meds": "second medication", "multiple_weights": "prior-visit weight", "per_day_basis": "per-day basis",
           "weight_tail": "weight in the upper tail"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results/by_stratum_run1.csv")
    ap.add_argument("--out", default="docs/figures/F2D_Figure_9_Composite_Failure_by_Stratum")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.csv)))
    strata = []
    for kind, _ in KINDS:
        seen = []
        for r in rows:
            if r["stratum_kind"] == kind and r["stratum"] not in seen:
                seen.append(r["stratum"])
        if kind == "age_band":
            seen = [b for b in ("neonate", "infant", "toddler", "school_age", "adolescent") if b in seen]
        strata += [(kind, s) for s in seen]
    val = {(r["stratum_kind"], r["stratum"], r["model"], r["workflow"]): (float(r["composite_failure_rate"]), int(r["n"])) for r in rows}
    cmap = LinearSegmentedColormap.from_list("blue_seq", ["#f4f8fd", "#9cc0ee", "#3b80d9", "#0f3d7a"])

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 7.4), dpi=200, sharey=True)
    for ax, wf in zip(axes, ("B", "C")):
        M = [[val[(k, s, m, wf)][0] for m in ORDER] for k, s in strata]
        im = ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
        for i, (k, s) in enumerate(strata):
            for j, m in enumerate(ORDER):
                v, n = val[(k, s, m, wf)]
                ax.text(j, i, f"{v:.3f}" if v > 0 else "0", ha="center", va="center", fontsize=7.2, color="white" if v > 0.55 else INK)
        ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([SHORT[m] for m in ORDER], fontsize=8, rotation=20, ha="right")
        ax.set_title(f"Workflow {wf} ({'end-to-end' if wf == 'B' else 'hybrid'})", fontsize=9.6, loc="left", color=INK)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        # separators between kinds
        pos = 0
        for kind, _ in KINDS[:-1]:
            pos += sum(1 for k, _ in strata if k == kind)
            ax.axhline(pos - 0.5, color="white", lw=2.2)
    labels = []
    for k, s in strata:
        n = val[(k, s, ORDER[0], "B")][1]
        if k == "complexity":
            lab = s
        elif k == "age_band":
            lab = BAND_LABEL[s]
        elif k == "generation":
            lab = "Paraphrased note" if s == "paraphrase" else "Template note"
        else:
            lab = NICE_CH.get(s, s)
        labels.append(f"{lab} (n={n})")
    axes[0].set_yticks(range(len(strata))); axes[0].set_yticklabels(labels, fontsize=7.8)
    cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02)
    cb.set_label("Composite dose-consequence failure rate (run 1, non-abstention records)", fontsize=8.4, color=INK2)
    cb.ax.tick_params(labelsize=8)
    fig.suptitle("Composite failure by stratum and model; challenge strata overlap and do not sum to the total", fontsize=10, x=0.01, ha="left", color=INK)
    save(fig, a.out)
    print(f"{len(strata)} strata x {len(ORDER)} models x 2 workflows from {a.csv}")


if __name__ == "__main__":
    main()
