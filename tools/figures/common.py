"""Shared style for the From Fields to Dose figures. Every figure script imports this and reads only committed files.

Palette: four categorical hues validated earlier for lightness, chroma, colour-vision-deficiency separation and
normal-vision separation (#2a78d6 blue, #eb6834 orange, #1baf7a green, #eda100 amber). Ordered categories (age bands,
complexity levels, heat-map cells) use a single-hue ramp, light to dark, so no fifth hue is needed.
"""
from __future__ import annotations
import glob, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["svg.fonttype"] = "none"

BLUE, ORANGE, GREEN, AMBER = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
CAT4 = [BLUE, ORANGE, GREEN, AMBER]
# Single-hue blue ramp, light to dark (five steps), for ordered categories.
RAMP5 = ["#cfe0f7", "#9cc0ee", "#6aa0e4", "#3b80d9", "#1f5cb0"]
RAMP3 = ["#cfe0f7", "#6aa0e4", "#1f5cb0"]
INK, INK2, GRID = "#222222", "#555555", "#d9d9d9"

ORDER = ["gpt-5.5-2026-04-23", "claude-sonnet-5", "gemini-3.1-pro-preview", "deepseek-v4-pro", "llama3.1:8b"]
SHORT = {"gpt-5.5-2026-04-23": "GPT-5.5", "claude-sonnet-5": "Claude Sonnet 5", "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
         "deepseek-v4-pro": "DeepSeek V4 Pro", "llama3.1:8b": "Llama 3.1 8B"}
BANDS = ["neonate", "infant", "toddler", "school_age", "adolescent"]
BAND_LABEL = {"neonate": "Neonate", "infant": "Infant", "toddler": "Toddler and young child", "school_age": "School-age child", "adolescent": "Adolescent"}


def style(ax, grid_axis="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#999999"); ax.spines["bottom"].set_color("#999999")
    ax.tick_params(colors=INK2, labelsize=9)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)


def load_cells(pattern="results/scored_test_*_run1.jsonl"):
    """Return {(model, workflow): rows} for the run-1 scored files. Rows keep every scored record."""
    cells = {}
    for f in sorted(glob.glob(pattern)):
        lines = [json.loads(l) for l in open(f)]
        cfg = lines[0]["_config"]
        cells[(cfg["model"]["id"], cfg["workflow"])] = [r for r in lines[1:] if "record_id" in r]
    if len(cells) != 10:
        raise SystemExit(f"STOP: expected 10 run-1 cells, found {len(cells)} from {pattern}")
    return cells


def save(fig, out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fig.savefig(out + ".png", bbox_inches="tight", dpi=200)
    fig.savefig(out + ".pdf", bbox_inches="tight")
    fig.savefig(out + ".svg", bbox_inches="tight")
    svg = open(out + ".svg").read().replace("font-family: 'DejaVu Sans'", "font-family: 'DejaVu Sans', Arial, Helvetica, sans-serif")
    open(out + ".svg", "w").write(svg)
    print(f"wrote {out}.png, .pdf, .svg")


def donut(ax, values, labels, colors, title=None, center_text=None, label_min_share=0.06, fontsize=8.5):
    """A single donut. Counts are written on the ring for slices at or above label_min_share; smaller slices are
    labelled through the legend (use legend_labels), so no leader lines cross the title."""
    import math
    total = sum(values)
    wedges, _ = ax.pie(values, colors=colors, startangle=90, counterclock=False,
                       wedgeprops=dict(width=0.38, edgecolor="white", linewidth=1.5))
    for w, v in zip(wedges, values):
        if v == 0 or total == 0 or v / total < label_min_share:
            continue
        ang = (w.theta2 + w.theta1) / 2.0
        x, y = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        ax.text(0.81 * x, 0.81 * y, str(v), ha="center", va="center", fontsize=fontsize, color="white" if v / total > 0.08 else INK)
    if center_text:
        ax.text(0, 0, center_text, ha="center", va="center", fontsize=fontsize + 0.5, color=INK)
    if title:
        ax.set_title(title, fontsize=fontsize + 1, color=INK, pad=10)
    ax.set_aspect("equal")
    return wedges


def legend_labels(labels, values):
    return [f"{l} ({v})" for l, v in zip(labels, values)]
