"""Figure 2: composition of the locked test set as four donuts (record type, age band, complexity, dosing basis),
with the drug distribution as a horizontal bar panel. Counts come from data/test/records.jsonl and
data/test/scenarios.jsonl after a digest check against data/test/LOCK.json; nothing is typed in.

Usage: python tools/figures/make_fig_testset.py [--out docs/figures/F2D_Figure_2_Test_Set_Composition]
"""
from __future__ import annotations
import argparse, collections, hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import plt, save, donut, legend_labels, style, RAMP5, RAMP3, CAT4, BLUE, ORANGE, BANDS, BAND_LABEL, INK, INK2


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def data():
    lock = json.load(open("data/test/LOCK.json"))
    if sha256("data/test/records.jsonl") != lock["records_sha256"] or sha256("data/test/scenarios.jsonl") != lock["scenarios_sha256"]:
        sys.exit("STOP: locked data files do not match LOCK.json")
    R = [json.loads(l) for l in open("data/test/records.jsonl")]
    S = {s["scenario_id"]: s for s in (json.loads(l) for l in open("data/test/scenarios.jsonl"))}
    bands = {b["id"]: b for b in json.load(open("sources/age_bands.json"))["bands"]}
    assert len(R) == 361
    c = collections.Counter
    na = sum(1 for r in R if not r["abstention_case"]); ab = len(R) - na
    return dict(R=R, S=S, bands=bands, na=na, ab=ab, band_n=c(r["age_band"] for r in R), lvl_n=c(r["complexity"] for r in R),
                basis_n=c(S[r["scenario_id"]]["dose_basis"] for r in R),
                gen_n=c("paraphrase" if r["generation_method"].startswith("paraphrase") else "template" for r in R),
                drug_n=c(S[r["scenario_id"]]["drug"] for r in R))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/figures/F2D_Figure_2_Test_Set_Composition")
    a = ap.parse_args()
    d = data(); R, S, bands, na, ab = d["R"], d["S"], d["bands"], d["na"], d["ab"]
    band_n, lvl_n, basis_n, gen_n, drug_n = d["band_n"], d["lvl_n"], d["basis_n"], d["gen_n"], d["drug_n"]

    fig = plt.figure(figsize=(13.5, 7.2), dpi=200)
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 0.75, 1.6], height_ratios=[1, 1], wspace=0.15, hspace=0.55)
    ax1 = fig.add_subplot(gs[0, 0]); ax2 = fig.add_subplot(gs[0, 1]); ax3 = fig.add_subplot(gs[1, 0]); ax4 = fig.add_subplot(gs[1, 1])
    ax5 = fig.add_subplot(gs[:, 3])

    donut(ax1, [na, ab], ["Non-abstention", "Abstention"], [BLUE, ORANGE], title="A. Record type", center_text=f"{len(R)}\nrecords")
    ax1.legend(legend_labels(["Fully specified regimen", "Abstention case"], [na, ab]), loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=7.5, ncol=1)

    bv = [band_n[b] for b in BANDS]
    donut(ax2, bv, BANDS, RAMP5, title="B. Age band", center_text="5 bands")
    ax2.legend([f"{BAND_LABEL[b]}, {bands[b]['min_days']} to {bands[b]['max_days']} d ({band_n[b]})" for b in BANDS], loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=6.6, ncol=1)

    lv = [lvl_n[k] for k in (1, 2, 3)]
    donut(ax3, lv, ["L1", "L2", "L3"], RAMP3, title="C. Documentation complexity", center_text="3 levels")
    ax3.legend(legend_labels(["Level 1: bare order", "Level 2: history and plan", "Level 3: admission note"], lv), loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=7.2)

    bk = ["mg/kg/day", "mg/kg/dose", "mcg/kg/day", "mcg/kg/dose"]
    donut(ax4, [basis_n[k] for k in bk], bk, CAT4, title="D. Dosing basis in the order", center_text="4 bases", fontsize=8)
    ax4.legend(legend_labels(bk, [basis_n[k] for k in bk]), loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=7.2, ncol=2)

    drugs = sorted(drug_n.items(), key=lambda kv: kv[1])
    ax5.barh([d for d, _ in drugs], [n for _, n in drugs], color=BLUE, height=0.68)
    for i, (d, n) in enumerate(drugs):
        ax5.text(n + 0.6, i, str(n), va="center", fontsize=8, color=INK)
    style(ax5, grid_axis="x")
    ax5.set_title(f"E. Records per medication ({len(drug_n)} represented of 21 sourced)", fontsize=9.5, loc="left", color=INK)
    ax5.set_xlabel("Records", fontsize=9, color=INK2)
    ax5.tick_params(axis="y", labelsize=8.2)
    ax5.set_xlim(0, max(n for _, n in drugs) * 1.12)
    fig.suptitle(f"Locked test set: {len(R)} synthetic pediatric records, one per scenario ({gen_n['template']} template-rendered, {gen_n['paraphrase']} paraphrased and audited)", fontsize=11, x=0.01, ha="left", color=INK)
    save(fig, a.out)
    print(f"records {len(R)} (non-abstention {na}, abstention {ab}); bands {dict(band_n)}; levels {dict(lvl_n)}; basis {dict(basis_n)}; generation {dict(gen_n)}; drugs {len(drug_n)}")


if __name__ == "__main__":
    main()
