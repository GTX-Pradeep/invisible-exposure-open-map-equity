"""Phase 8: manuscript figures (PNG 300 dpi + PDF) from processed tables only."""
import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from coverage_risk import aggregate as ag

F = Path("outputs/figures"); F.mkdir(parents=True, exist_ok=True)
T = Path("outputs/tables"); P = Path("data/processed")
C1, C2, C3, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2 = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
                     "grid.color": "#e6e5e0", "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False,
                     "font.family": "DejaVu Sans"})
REG = {"maricopa-az": "Maricopa, AZ", "northern-ca": "Northern CA", "eastern-ok": "Eastern OK",
       "south-central-tx": "South-central TX", "eastern-wa": "Eastern WA"}


from matplotlib.ticker import FixedLocator, NullFormatter, FuncFormatter


def plain_log(ax, ticks=(0.1, 0.2, 0.5, 1, 2, 5, 10)):
    lo, hi = ax.get_xlim()
    t = [v for v in ticks if lo <= v <= hi]
    ax.xaxis.set_major_locator(FixedLocator(t)); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))


def save(fig, name):
    fig.savefig(F / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(F / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


d = pd.read_parquet(P / "audit_frame.parquet")

# Fig 1: maps of deficit_z with flags, one panel per region
tr = ag.load_tracts(list(REG)).merge(d[["GEOID", "bldg_deficit_z", "bldg_flag", "poi_flag"]], on="GEOID")
from matplotlib.colors import LinearSegmentedColormap
DIV = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#a9c8ee", "#efeeea", "#f2a7a6", "#c4302f"])
fig, axes = plt.subplots(1, 5, figsize=(11, 3.0))
for ax, (r, lab) in zip(axes, REG.items()):
    g = tr[tr.region == r].to_crs(5070)
    g.plot(ax=ax, column=g.bldg_deficit_z.clip(-2, 2), cmap=DIV, vmin=-2, vmax=2, linewidth=0.05, edgecolor="white")
    g[g.bldg_flag].plot(ax=ax, facecolor="none", edgecolor=INK, linewidth=0.6)
    ax.set_title(lab, fontsize=9, color=INK); ax.set_axis_off()
sm = plt.cm.ScalarMappable(cmap=DIV, norm=plt.Normalize(-2, 2))
cb = fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.04, pad=0.02, aspect=50)
cb.set_label("Standardized building deficit (red = fewer mapped buildings than expected, blue = more); black outline = flagged tract")
save(fig, "fig1_maps")

# Fig 2: Overture vs USA Structures, flags highlighted
fig, ax = plt.subplots(figsize=(4.2, 4.0))
s = d[d.ref_bldg.notna()]
ax.scatter(s.ref_bldg + 1, s.r2026a_bldg450 + 1, s=3, c=GREY, alpha=0.35, lw=0, label="not flagged")
f = s[s.bldg_flag]
ax.scatter(f.ref_bldg + 1, f.r2026a_bldg450 + 1, s=8, c=C2, alpha=0.9, lw=0.3, edgecolor="white", label="flagged by model")
lim = [1, s[["ref_bldg", "r2026a_bldg450"]].max().max() * 1.5]
ax.plot(lim, lim, color=INK2, lw=0.8); ax.plot(lim, [0.8 * x for x in lim], color=INK2, lw=0.8, ls="--")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("USA Structures buildings per tract (+1)"); ax.set_ylabel("Overture buildings ≥450 sq ft per tract (+1)")
ax.text(lim[1] / 1.4, lim[1] / 1.6 * 0.8, "80% of reference", ha="right", va="top", color=INK2, fontsize=7.5)
ax.legend(loc="upper left", markerscale=2)
save(fig, "fig2_reference_scatter")

# Fig 3: coverage by region under CV schemes x calibration
cv = pd.read_csv(T / "cv_schemes.csv")
fig, axes = plt.subplots(1, 2, figsize=(8, 3.0), sharey=True)
for ax, layer, title in [(axes[0], "bldg", "Buildings"), (axes[1], "poi", "POIs")]:
    c = cv[cv.layer == layer].reset_index(drop=True)
    labs = [f"{a}\n{b.replace('mondrian-region', 'per-region')}" for a, b in zip(c.scheme, c.calibration)]
    for i, row in c.iterrows():
        vals = [row[f"cov_{r}"] for r in REG]
        ax.plot([i, i], [min(vals), max(vals)], color=GREY, lw=2, solid_capstyle="round")
        ax.scatter([i] * 5, vals, s=12, color=C1, zorder=3, lw=0)
        ax.scatter(i, row.coverage, s=40, marker="D", color=C2, zorder=4, lw=0.6, edgecolor="white")
    ax.axhline(0.90, color=INK2, lw=0.8, ls="--")
    ax.set_xticks(range(len(c))); ax.set_xticklabels(labs, fontsize=7); ax.set_title(title, fontsize=9)
axes[0].set_ylabel("Empirical coverage of 90% range")
axes[0].scatter([], [], color=C1, s=12, label="per region"); axes[0].scatter([], [], color=C2, marker="D", s=30, label="overall")
axes[0].legend(loc="lower left")
save(fig, "fig3_coverage_schemes")

# Fig 4: deletion test
dt = pd.read_csv(T / "deletion_test.csv")
fig, ax = plt.subplots(figsize=(4.2, 3.0))
for layer, col, lab in [("bldg", C1, "Buildings"), ("poi", C2, "POIs")]:
    x = dt[dt.layer == layer]
    ax.plot(x.removed_share * 100, x.detection_rate * 100, color=col, lw=2, marker="o", ms=4, label=lab)
ax.set_xlabel("Share of a tract's mapped features removed (%)"); ax.set_ylabel("Tracts flagged (%)")
ax.set_ylim(0, 102); ax.legend(loc="lower right")
save(fig, "fig4_deletion")
print("base figures done")

# ---------------------------------------------------------------- result figures
GLAB = {"svi": "High vs low SVI", "cvi": "High vs low CVI", "rural": "Rural vs urban", "tribal": "Tribal vs non-tribal"}

# Fig 5: two lenses — map-trained flag vs reference-anchored flag vs reference gap (adjusted odds ratios)
e2 = pd.read_csv(T / "e2_normalization.csv")
e2 = e2[e2.analysis == "E2-flags"]
OUT = [("bldg_flag", "Map-trained expectation (flag)", C1), ("anchored_flag", "Reference-anchored expectation (flag)", C3),
       ("ref_gap_b", "Reference gap (<80% of USA Structures)", C2)]
fig, ax = plt.subplots(figsize=(6.2, 3.4))
for gi, grp in enumerate(GLAB):
    for oi, (o, lab, col) in enumerate(OUT):
        r = e2[(e2.group == grp) & (e2.outcome == o)].iloc[0]
        y = gi + (oi - 1) * 0.22
        ax.plot([r.aor_ci_lo, r.aor_ci_hi], [y, y], color=col, lw=1.6, solid_capstyle="round")
        ax.scatter(r.adj_odds_ratio, y, color=col, s=26, zorder=3, edgecolor="white", lw=0.6, label=lab if gi == 0 else None)
ax.axvline(1, color=INK2, lw=0.8, ls="--"); ax.set_xscale("log"); plain_log(ax)
ax.set_yticks(range(len(GLAB))); ax.set_yticklabels(GLAB.values()); ax.invert_yaxis()
ax.set_xlabel("Adjusted odds ratio of a building gap (region fixed effects, 95% CI)")
ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.2), ncol=1, fontsize=7.5)
save(fig, "fig5_two_lenses")

# Fig 6: catch-up across snapshots, share of tracts below 80% of reference
sn = pd.read_csv(T / "h3_snapshots.csv")
x = [0, 1, 2]; xl = ["2023-07", "2026-08", "2026-10"]
fig, axes = plt.subplots(1, 4, figsize=(10, 2.8), sharey=True)
from coverage_risk.audit import CONTRASTS
for ax, (grp, (hi, lo)) in zip(axes, CONTRASTS.items()):
    ax.plot(x, sn[f"lt80_{grp}_{hi}"] * 100, color=C2, lw=2, marker="o", ms=4, label=hi)
    ax.plot(x, sn[f"lt80_{grp}_{lo}"] * 100, color=C1, lw=2, marker="o", ms=4, label=lo)
    ax.set_xticks(x); ax.set_xticklabels(xl, fontsize=7.5); ax.set_title(GLAB[grp], fontsize=9)
    ax.legend(loc="upper right", fontsize=7.5)
axes[0].set_ylabel("Tracts below 80% of reference (%)")
axes[0].annotate("Bexar Co. release\nregression", xy=(2, sn["lt80_svi_Q4"].iloc[2] * 100), xytext=(1.1, 12), fontsize=7,
                 color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
save(fig, "fig6_catchup")

# Fig 7: hidden exposure rate ratios
h5 = pd.read_csv(T / "confirmatory_fdr.csv"); h5 = h5[h5.hyp == "H5"].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(5.4, 3.2))
hz_col = {"heat": C2, "wildfire": "#e34948", "drought": "#eda100"}
for i, r in h5.iterrows():
    lo_ = max(r.ci_lo, 0.02)
    ax.plot([lo_, r.ci_hi], [i, i], color=hz_col[r.hazard_name], lw=1.6)
    ax.scatter(max(r.rate_ratio, 0.02), i, color=hz_col[r.hazard_name], s=28, zorder=3, edgecolor="white", lw=0.6,
               marker="D" if r.reject_bh else "o")
ax.set_yticks(range(len(h5)))
ax.set_yticklabels([f"{r.hazard_name}: {GLAB[r.group].lower()}" for _, r in h5.iterrows()], fontsize=7.5)
ax.axvline(1, color=INK2, lw=0.8, ls="--"); ax.set_xscale("log"); plain_log(ax, (0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10)); ax.invert_yaxis()
ax.set_xlabel("Hidden exposure rate ratio (missing structures per 1,000 HU in top-tercile hazard tracts)")
ax.text(0.99, 0.02, "◆ significant after BH-FDR", transform=ax.transAxes, ha="right", fontsize=7, color=INK2)
save(fig, "fig7_hidden_exposure")

# Fig 8: Bexar County release regression
c = pd.read_parquet(P / "catchup_frame.parquet")
bx = ag.load_tracts(["south-central-tx"]).merge(c[["GEOID", "county", "loss_aug_oct", "flag_r2026b"]], on="GEOID")
bx = bx[bx.county == "48029"].to_crs(5070)
fig, ax = plt.subplots(figsize=(5, 4.2))
seq = LinearSegmentedColormap.from_list("seq", ["#efeeea", "#f2a7a6", "#c4302f", "#7a1414"])
bx.plot(ax=ax, column=(bx.loss_aug_oct * 100).clip(0, 70), cmap=seq, vmin=0, vmax=70, linewidth=0.1, edgecolor="white")
bx[bx.flag_r2026b].plot(ax=ax, facecolor="none", edgecolor=INK, linewidth=0.5)
ax.set_axis_off()
sm = plt.cm.ScalarMappable(cmap=seq, norm=plt.Normalize(0, 70))
cb = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.01); cb.set_label("Buildings lost, Aug → Oct 2026 release (%)")
ax.set_title("Bexar County, TX (San Antonio)", fontsize=9)
save(fig, "fig8_bexar_regression")
print("all figures done")
