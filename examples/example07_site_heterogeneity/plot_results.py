#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Draw publication figures from the derived result tables; captions are in RESULTS.md."""

from pathlib import Path
import argparse
import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
COLORS = [
    "#306845",
    "#70a66a",
    "#d49d55",
    "#8cc9ae",
    "#b76c45",
    "#b99acb",
    "#5189b5",
    "#42598a",
]
NAMES = [
    "High plateau, Ava",
    "Low plateau, Ava",
    "Plateau, Marron",
    "Slope, Ava",
    "Slope, Marron",
    "Fairchild",
    "Stream corridor",
    "Seasonal swamp",
]
PFT_COLORS = ["#e8c58b", "#a8c4b6", "#a4b4c9"]
SCENARIOS = ["A_heterogeneous", "B_uniform_multisite", "C_uniform_single"]
SNAPSHOT = "2015-07-01"


def style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "text.color": "black",
            "axes.labelcolor": "black",
            "axes.edgecolor": "black",
            "xtick.color": "black",
            "ytick.color": "black",
            "axes.linewidth": 0.65,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def save(fig, name):
    target = HERE / "figures"
    target.mkdir(exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(target / f"{name}.{suffix}", dpi=300, bbox_inches="tight")
    previews = {
        "01_site_stands": "overview.png",
        "07_site_responses": "site_responses.png",
        "08_site_composition": "site_composition.png",
    }
    if name in previews:
        # Compact README previews; full-resolution and vector exports stay in figures/.
        fig.savefig(HERE / previews[name], dpi=120, bbox_inches="tight")
    plt.close(fig)


def site_overview():
    q = pd.read_csv(HERE / "data/quadrat_assignment.csv")
    pft = pd.read_csv(HERE / "results/A_site_pft_monthly.csv.gz", parse_dates=["date"])
    pft = pft[pft.dbh_min_cm == 0]
    p = pft[pft.date == SNAPSHOT]
    totals = p.groupby("site")[["agb_kgC_m2", "lai"]].sum().reindex(range(1, 9))
    composition = p.pivot(index="site", columns="pft", values="agb_kgC_m2")
    composition = composition.div(composition.sum(axis=1), axis=0) * 100
    area = q.groupby("site_id").size().reindex(range(1, 9)) * 0.04
    weights = area.to_numpy() / area.sum()
    agb, lai = totals.agb_kgC_m2.to_numpy() * 10, totals.lai.to_numpy()
    assert len(q) == 1250 and np.allclose(composition.sum(axis=1), 100)
    export = totals.assign(area_ha=area, agb_MgC_ha=agb)
    for k in (1, 2, 3):
        export[f"pft{k}_agb_percent"] = composition[k]
    export.to_csv(HERE / "results/site_overview_values.csv")

    fig = plt.figure(figsize=(12.6, 7.2))
    grid = fig.add_gridspec(
        2,
        4,
        width_ratios=[1.55, 1.35, 1.2, 1.85],
        height_ratios=[1, 1.38],
        hspace=0.46,
        wspace=0.30,
    )
    ax = fig.add_subplot(grid[0, :2])
    ax.pcolormesh(
        np.arange(0, 1020, 20),
        np.arange(0, 520, 20),
        q.pivot(index="y", columns="x", values="site_id"),
        cmap=ListedColormap(COLORS),
        norm=BoundaryNorm(np.arange(0.5, 9.5), 8),
    )
    ax.set(
        aspect="equal",
        xlim=(0, 1000),
        ylim=(0, 500),
        xlabel="x (m)",
        ylabel="y (m)",
        xticks=[0, 250, 500, 750, 1000],
        yticks=[0, 250, 500],
    )
    ax.set_title("a  Site distribution", loc="left")
    monthly = pft.groupby(["date", "site"])[["agb_kgC_m2", "lai"]].sum().reset_index()
    for column, key, scale, label, title in [
        (2, "agb_kgC_m2", 10, r"AGB (Mg C ha$^{-1}$)", "b  Biomass"),
        (3, "lai", 1, r"LAI (m$^2$ m$^{-2}$)", "c  Leaf area"),
    ]:
        ax = fig.add_subplot(grid[0, column])
        for site, color in enumerate(COLORS, 1):
            group = monthly[monthly.site == site]
            ax.plot(group.date, group[key] * scale, color=color, lw=1.1)
        ax.axvline(pd.Timestamp(SNAPSHOT), color="black", lw=0.6, ls="--")
        ax.set_ylabel(label)
        ax.set_xticks(
            pd.to_datetime(["2011-01-01", "2014-01-01", "2018-01-01"]),
            ["2011", "2014", "2018"],
        )
        ax.set_title(title, loc="left")
    rows = np.arange(8)
    labels = fig.add_subplot(grid[1, 0])
    labels.set(xlim=(0, 1), ylim=(7.6, -0.6))
    labels.axis("off")
    labels.set_title("Site / area (ha)", loc="left")
    for row, name, color, size in zip(rows, NAMES, COLORS, area):
        labels.scatter(0, row, marker="s", s=35, color=color, clip_on=False)
        labels.text(0.07, row - 0.10, name, va="center", fontsize=9)
        labels.text(0.07, row + 0.25, f"{size:.2f}", va="center", fontsize=8)
    for column, values, label, title in [
        (1, agb, r"AGB (Mg C ha$^{-1}$)", "d  Biomass"),
        (2, lai, r"LAI (m$^2$ m$^{-2}$)", "e  Leaf area"),
    ]:
        ax = fig.add_subplot(grid[1, column])
        mean = weights @ values
        ax.axvline(mean, color="black", lw=0.8, ls="--")
        for row, value, color in zip(rows, values, COLORS):
            ax.plot([mean, value], [row, row], color=color, lw=1.4)
            ax.scatter(
                value,
                row,
                color=color,
                s=35,
                edgecolor="black",
                linewidth=0.3,
                zorder=3,
            )
        extent = np.ptp(values)
        ax.set(
            xlim=(values.min() - 0.12 * extent, values.max() + 0.12 * extent),
            ylim=(7.6, -0.6),
            yticks=[],
            xlabel=label,
        )
        ax.spines["left"].set_visible(False)
        ax.set_title(title, loc="left")
    ax = fig.add_subplot(grid[1, 3])
    left = np.zeros(8)
    for k, color in enumerate(PFT_COLORS, 1):
        values = composition[k].to_numpy()
        ax.barh(
            rows,
            values,
            left=left,
            height=0.52,
            color=color,
            edgecolor="black",
            linewidth=0.35,
        )
        for row, value, start in zip(rows, values, left):
            ax.text(
                start + value / 2,
                row,
                f"{value:.0f}",
                va="center",
                ha="center",
                fontsize=8,
            )
        left += values
    ax.set(
        ylim=(7.6, -0.6),
        yticks=[],
        xlim=(0, 100),
        xticks=[0, 50, 100],
        xlabel="AGB share (%)",
    )
    ax.spines["left"].set_visible(False)
    ax.set_title("f  PFT composition", loc="left")
    ax.legend(
        [Patch(facecolor=c, edgecolor="black", linewidth=0.4) for c in PFT_COLORS],
        ["Low", "Mid", "High"],
        title="Wood density",
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        frameon=False,
        fontsize=8,
        handlelength=1,
        columnspacing=0.8,
    )
    save(fig, "01_site_stands")


def contrasts():
    annual = pd.read_csv(HERE / "results/annual_metrics.csv").query("year >= 2012")
    mean = annual.groupby("scenario").mean(numeric_only=True)
    pairs = [
        (SCENARIOS[0], SCENARIOS[1], "A − B"),
        (SCENARIOS[1], SCENARIOS[2], "B − C"),
        (SCENARIOS[0], SCENARIOS[2], "A − C"),
        ("S_equal_depth", SCENARIOS[1], "Equal depth − B"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5), layout="constrained")
    for ax, (key, title) in zip(
        axes,
        [
            ("gpp_kgC_m2_yr", "a  GPP"),
            ("et_mm_yr", "b  Evapotranspiration"),
            ("agb_mean_kgC_m2", "c  Aboveground biomass"),
        ],
    ):
        for row, (left, right, _) in enumerate(pairs):
            if left not in mean.index:
                continue
            a = annual[annual.scenario == left].set_index("year")[key]
            b = annual[annual.scenario == right].set_index("year")[key]
            values = 100 * (a - b) / mean.at[right, key]
            value = 100 * (mean.at[left, key] / mean.at[right, key] - 1)
            color = [COLORS[0], COLORS[6], COLORS[4], COLORS[5]][row]
            ax.plot([values.min(), values.max()], [row, row], color=color, lw=1)
            ax.scatter(
                values,
                np.full(len(values), row),
                facecolor="white",
                edgecolor=color,
                s=20,
            )
            ax.scatter(value, row, color=color, marker="D", s=30, zorder=3)
        ax.axvline(0, color="black", ls="--", lw=0.6)
        ax.set(
            yticks=range(len(pairs)),
            yticklabels=[p[2] for p in pairs],
            ylim=(len(pairs) - 0.4, -0.6),
            xlabel="Difference relative to reference (%)",
        )
        ax.set_title(title, loc="left")
    save(fig, "02_representation_contrasts")


def environment():
    d = pd.read_csv(HERE / "results/daily_sites.csv.gz", parse_dates=["date"])
    a = d[(d.scenario == SCENARIOS[0]) & d.date.between("2015-01-01", "2016-12-31")]
    b = d[(d.scenario == SCENARIOS[1]) & d.date.between("2015-01-01", "2016-12-31")]
    paired = a.merge(
        b, on=["date", "site_id"], suffixes=("_a", "_b"), validate="one_to_one"
    )
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6), layout="constrained")
    for sid, color, name in zip(range(1, 9), COLORS, NAMES):
        g = a[a.site_id == sid].sort_values("date")
        for ax, key in [(axes[0, 0], "psi_15cm"), (axes[0, 1], "soil_water_mm")]:
            ax.plot(
                g.date,
                g[key].rolling(7, min_periods=1).mean(),
                color=color,
                lw=1,
                label=name,
            )
        g = paired[paired.site_id == sid]
        for ax, key in [
            (axes[1, 0], "mean_air_temp_si"),
            (axes[1, 1], "mean_direct_beam_si"),
        ]:
            v = g[key + "_a"] - g[key + "_b"]
            ax.plot(g.date, v.rolling(7, min_periods=1).mean(), color=color, lw=1)
    for ax, title, ylabel in zip(
        axes.flat,
        [
            "a  Soil water potential at 0.15 m",
            "b  Column water storage",
            "c  Temperature: A − B",
            "d  Direct-beam radiation: A − B",
        ],
        [
            "Water potential (MPa)",
            "Water storage (mm)",
            "Air temperature difference (K)",
            r"Direct-beam difference (W m$^{-2}$)",
        ],
    ):
        ax.set_title(title, loc="left")
        ax.set_ylabel(ylabel)
        ax.set_xticks(
            pd.to_datetime(["2015-01-01", "2016-01-01", "2017-01-01"]),
            ["2015", "2016", "2017"],
        )
    axes[0, 0].legend(frameon=False, fontsize=7, ncol=2, loc="lower left")
    save(fig, "03_site_environment")


def soil_profiles():
    from prepare_input import theta

    sites = json.loads((HERE / "data/sites.json").read_text())
    eq = json.loads((HERE / "data/equivalent_environment.json").read_text())
    storage = pd.read_csv(HERE / "data/equivalent_storage.csv")
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4), layout="constrained")
    psi = -np.geomspace(0.01, 10, 120)
    for sid, (site, color) in enumerate(zip(sites, COLORS), 1):
        axes[0].bar(sid, site["depth"], width=0.24, color=color)
        axes[0].scatter(
            np.full(8, sid),
            site["layer_bottoms"],
            marker="_",
            color="black",
            s=65,
            zorder=3,
        )
        axes[1].plot(
            -psi,
            theta(psi, site["curve_par_a"], site["curve_par_n"]),
            color=color,
            lw=1,
        )
    axes[0].axhline(eq["depth"], color="black", ls="--", lw=0.8)
    axes[0].set(ylim=(2.2, 0), ylabel="Depth (m)", xlabel="Site", xticks=range(1, 9))
    axes[0].set_title("a  Soil layers", loc="left")
    axes[1].set(
        xscale="log", xlabel="Suction (MPa)", ylabel=r"Water content (m$^3$ m$^{-3}$)"
    )
    axes[1].set_title("b  Site retention curves", loc="left")
    axes[2].plot(
        -storage.psi_MPa,
        storage.target_storage_mm,
        color="black",
        label="Area-weighted sites",
    )
    axes[2].plot(
        -storage.psi_MPa,
        storage.equivalent_storage_mm,
        color="black",
        ls="--",
        label="Equivalent column",
    )
    axes[2].set(xscale="log", xlabel="Suction (MPa)", ylabel="Water storage (mm)")
    axes[2].set_title("c  Equivalent water storage", loc="left")
    axes[2].legend(frameon=False, fontsize=8)
    save(fig, "04_soil_profiles")


def seasonal_profiles():
    profiles = pd.read_csv(HERE / "results/soil_layer_profiles.csv")
    for variable, label, stem in [
        (
            "mean_soil_water_layer_si",
            r"Water content (m$^3$ m$^{-3}$)",
            "05_soil_water",
        ),
        ("mean_soil_psi_layer_si", "Water potential (MPa)", "06_soil_potential"),
    ]:
        fig, axes = plt.subplots(
            2, 4, figsize=(10.5, 5.5), layout="constrained", sharey=True
        )
        for site, (ax, name, color) in enumerate(zip(axes.flat, NAMES, COLORS), 1):
            for season, linestyle in [("Jan-Mar", "-"), ("Jul-Sep", "--")]:
                group = profiles[
                    (profiles.site_id == site)
                    & (profiles.variable == variable)
                    & (profiles.season == season)
                ].sort_values("depth_m")
                ax.plot(
                    group.value,
                    group.depth_m,
                    linestyle,
                    marker="o",
                    ms=3,
                    color=color,
                    label=season,
                )
            ax.set_title(f"{chr(96 + site)}  {name}", loc="left", fontsize=9)
            ax.set(xlabel=label, ylim=(2.1, 0))
        for ax in axes[:, 0]:
            ax.set_ylabel("Depth (m)")
        axes[0, 0].legend(frameon=False, fontsize=8)
        save(fig, stem)


def site_responses():
    summary = pd.read_csv(HERE / "results/AB_site_summary.csv").set_index("site_id")
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 7.3), layout="constrained")
    for ax, metric, title in zip(
        axes.flat,
        ["gpp_umol", "et_mm_day", "agb_MgC_ha", "lai"],
        [
            "a  GPP",
            "b  Evapotranspiration",
            "c  Aboveground biomass",
            "d  Leaf area index",
        ],
    ):
        values = summary[metric + "_relative_percent"].reindex(range(1, 9)).to_numpy()
        ax.axvline(0, color="0.5", lw=0.7)
        for row, value, color in zip(range(8), values, COLORS):
            ax.plot([0, value], [row, row], color=color, lw=1.4)
            ax.scatter(
                value,
                row,
                s=32,
                color=color,
                edgecolor="black",
                linewidth=0.35,
                zorder=3,
            )
            label = "<0.01" if abs(value) < 0.005 else f"{value:+.2f}"
            ax.annotate(
                label,
                (value, row),
                xytext=(-6 if value < 0 else 6, 0),
                textcoords="offset points",
                ha="right" if value < 0 else "left",
                va="center",
                fontsize=8,
            )
        ax.set(
            yticks=range(8),
            yticklabels=NAMES,
            ylim=(7.6, -0.6),
            xlim=(min(-0.75, values.min() - 1.1), max(0.9, values.max() + 0.95)),
            xlabel="A relative to B (%)",
        )
        ax.tick_params(axis="y", length=0, pad=7)
        ax.set_title(title, loc="left")
    save(fig, "07_site_responses")


def site_composition():
    pair = pd.read_csv(
        HERE / "results/AB_site_pft_monthly.csv.gz", parse_dates=["date"]
    )
    pair = pair[pair.dbh_min_cm == 0]
    snapshots = [pd.Timestamp(SNAPSHOT), pair.date.max()]
    selected = pair[pair.date.isin(snapshots)]
    lower, upper = selected.agb_share_difference_pp.agg(["min", "max"])
    extent = max(upper - lower, 0.1)
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.7), layout="constrained")
    for panel, (ax, date) in enumerate(zip(axes, snapshots)):
        ax.axvline(0, color="0.5", lw=0.7)
        for pft, color in enumerate(PFT_COLORS, 1):
            g = (
                pair[(pair.date == date) & (pair.pft == pft)]
                .set_index("site")
                .reindex(range(1, 9))
            )
            rows = np.arange(8) + (pft - 2) * 0.21
            values = g.agb_share_difference_pp.to_numpy()
            ax.hlines(rows, 0, values, color=color, lw=1.4)
            ax.scatter(
                values,
                rows,
                color=color,
                edgecolor="black",
                linewidth=0.4,
                s=28,
                zorder=3,
            )
        ax.set(
            yticks=range(8),
            yticklabels=NAMES,
            ylim=(7.6, -0.6),
            xlim=(lower - 0.12 * extent, upper + 0.12 * extent),
            xlabel="A − B in AGB share (percentage points)",
        )
        ax.tick_params(axis="y", length=0, pad=7)
        ax.set_title(f"{chr(97 + panel)}  {date:%B %Y}", loc="left")
    axes[1].legend(
        [
            Line2D(
                [],
                [],
                marker="o",
                ls="",
                color=c,
                markeredgecolor="black",
                markeredgewidth=0.4,
            )
            for c in PFT_COLORS
        ],
        ["Low", "Mid", "High"],
        title="Wood-density PFT",
        frameon=False,
        loc="upper right",
        fontsize=8,
    )
    save(fig, "08_site_composition")


def report(update_readme=False):
    """Write numerical results and captions from the same tables as the figures."""
    annual = pd.read_csv(HERE / "results/annual_metrics.csv").query("year >= 2012")
    mean = annual.groupby("scenario").mean(numeric_only=True)
    a, b, c = [mean.loc[name] for name in SCENARIOS]
    depth = mean.loc["S_equal_depth"] if "S_equal_depth" in mean.index else None
    difference = 100 * (a / b - 1)
    paragraph = (
        f"For 2012–2017, A has {abs(difference.gpp_kgC_m2_yr):.3f}% lower GPP and "
        f"{abs(difference.et_mm_yr):.3f}% lower evapotranspiration than B. "
        f"The B − C differences are {100 * (b.gpp_kgC_m2_yr / c.gpp_kgC_m2_yr - 1):+.3f}% "
        f"for GPP and {100 * (b.et_mm_yr / c.et_mm_yr - 1):+.3f}% for evapotranspiration. "
        f"Across the full A − C comparison, the differences are "
        f"{100 * (a.gpp_kgC_m2_yr / c.gpp_kgC_m2_yr - 1):+.3f}% and "
        f"{100 * (a.et_mm_yr / c.et_mm_yr - 1):+.3f}%."
    )
    if depth is not None:
        eq = json.loads((HERE / "data/equivalent_environment.json").read_text())
        paragraph += (
            f" Assigning every A site the area-mean depth ({eq['depth']:.3f} m) changes "
            f"its differences from B to {100 * (depth.gpp_kgC_m2_yr / b.gpp_kgC_m2_yr - 1):+.3f}% "
            f"and {100 * (depth.et_mm_yr / b.et_mm_yr - 1):+.3f}%, respectively. "
            "Thus the simulated flux contrast depends strongly on the prescribed depth allocation."
        )
    summary = pd.read_csv(HERE / "results/site_overview_values.csv")
    weights = summary.area_ha / summary.area_ha.sum()
    avg = lambda key: float(weights @ summary[key])
    cv = lambda key: float(
        100 * np.sqrt(weights @ (summary[key] - avg(key)) ** 2) / avg(key)
    )
    lines = [
        "# Site heterogeneity in the BCI forest plot",
        "",
        paragraph,
        "",
        "| Scenario | GPP (Mg C ha⁻¹ yr⁻¹) | ET (mm yr⁻¹) | AGB (Mg C ha⁻¹) | LAI |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, row in mean.iterrows():
        lines.append(
            f"| {name} | {row.gpp_kgC_m2_yr * 10:.3f} | {row.et_mm_yr:.2f} | "
            f"{row.agb_mean_kgC_m2 * 10:.3f} | {row.lai_mean:.3f} |"
        )
    lines += [
        "",
        "AGB and LAI are means of daily polygon values; fluxes are integrated annual totals.",
        "",
        "## Site stands",
        "",
        f"On {SNAPSHOT}, site AGB ranges from {summary.agb_MgC_ha.min():.2f} to "
        f"{summary.agb_MgC_ha.max():.2f} Mg C ha⁻¹, and LAI from {summary.lai.min():.3f} "
        f"to {summary.lai.max():.3f} m² m⁻². The area-weighted means are "
        f"{avg('agb_MgC_ha'):.2f} Mg C ha⁻¹ and {avg('lai'):.3f} m² m⁻². "
        f"The corresponding spatial coefficients of variation are {cv('agb_MgC_ha'):.2f}% "
        f"and {cv('lai'):.2f}%. These describe variation among the represented sites.",
        "",
    ]
    paired = pd.read_csv(HERE / "results/AB_site_summary.csv")
    lines += [
        "## Paired site responses",
        "",
        "Daily means over 2012–2017, expressed as 100 × (A/B − 1). "
        "The initial site forests are identical; differences reflect their specified environments "
        "and subsequent dynamics. AGB and LAI include all modeled cohorts.",
        "",
        "| Site | GPP (%) | ET (%) | AGB (%) | LAI (%) |",
        "|---|---:|---:|---:|---:|",
    ]
    for row, name in zip(paired.itertuples(), NAMES):
        lines.append(
            f"| {name} | {row.gpp_umol_relative_percent:+.3f} | "
            f"{row.et_mm_day_relative_percent:+.3f} | {row.agb_MgC_ha_relative_percent:+.3f} | "
            f"{row.lai_relative_percent:+.3f} |"
        )
    lines += [
        "",
        "Absolute A and B values and area-weighted contributions are in `AB_site_summary.csv`. "
        "Monthly paired PFT abundances and AGB shares are in `AB_site_pft_monthly.csv.gz`.",
        "",
    ]
    captions = [
        (
            "01_site_stands",
            "Site distribution and stand structure. (a) Quadrats grouped by terrain and soil. "
            "Colors identify the sites in the lower-left key; areas are in hectares. (b,c) Monthly "
            "AGB and LAI from cohort states and patch areas. Vertical dashed lines mark 1 July 2015. "
            "(d,e) Site values on that date; dashed lines are polygon area-weighted means. "
            "(f) PFT shares of site AGB; labels are rounded percentages. Low, mid and high refer to "
            "wood-density PFTs. All modeled cohorts are included.",
        ),
        (
            "02_representation_contrasts",
            "Polygon responses to environmental representation. "
            "Open circles show annual differences and diamonds their mean over 2012–2017. "
            "Lines span the annual range. All differences use the reference run's period mean as "
            "denominator. A − B retains the same site grouping and initial forest; B − C also changes "
            "the scope and capacity of patch restructuring. A − C compares the heterogeneous polygon "
            "with the single equivalent site. Equal depth retains A's terrain, retention "
            "parameters and forest while assigning the common area-mean depth.",
        ),
        (
            "03_site_environment",
            "Site environments during 2015–2016. (a) Water potential interpolated "
            "to 0.15 m and (b) depth-integrated water storage in A. (c,d) Differences between A and B "
            "in air temperature and direct-beam radiation, summed over PAR and NIR. Curves are trailing "
            "seven-day means; colors follow Figure 1.",
        ),
        (
            "04_soil_profiles",
            "Construction of the equivalent soil column. (a) Assigned site depths "
            "and layer bottoms; the dashed line is the area-mean depth. Site numbers follow the order "
            "of Figure 1. (b) Site retention curves derived from mapped soil fractions and laboratory "
            "samples. (c) Area-weighted water storage and the fitted equivalent column. Profile depths "
            "are prescribed scenarios; laboratory data constrain retention.",
        ),
        (
            "05_soil_water",
            "Seasonal soil water content in A during 2016. Solid and dashed lines are "
            "daily means over January–March and July–September, respectively. Points are each site's "
            "own layer centers; all panels use the same depth scale.",
        ),
        (
            "06_soil_potential",
            "Seasonal soil water potential in A during 2016. Periods, layer centers "
            "and colors follow Figure 5. Horizontal scales vary among sites.",
        ),
    ]
    captions += [
        (
            "07_site_responses",
            "Paired site responses to heterogeneous (A) and equivalent (B) environments. "
            "Points show 100 × (mean A / mean B − 1) for daily GPP, ET, AGB and LAI over 2012–2017. "
            "Colors follow the site map. All modeled cohorts are included. Each paired forest starts "
            "from the same census initialization.",
        ),
        (
            "08_site_composition",
            "Paired differences in PFT shares of site AGB, in percentage points. "
            "The snapshots show July 2015 and the final saved month. Colors follow the low-, mid- and "
            "high-wood-density PFTs in Figure 1; within each site they run from top to bottom in that order. "
            "All modeled cohorts are included; each site's three differences sum to zero.",
        ),
    ]
    for number, (stem, caption) in enumerate(captions, 1):
        lines += [
            f"## Figure {number}",
            "",
            f"![Figure {number}](../figures/{stem}.png)",
            "",
            caption,
            "",
            f"[PDF](../figures/{stem}.pdf) · [SVG](../figures/{stem}.svg)",
            "",
        ]
    census = pd.read_csv(HERE / "results/census_2015_comparison.csv")
    obs = census[(census.scenario == SCENARIOS[0]) & (census.pft == 0)].iloc[0]
    lines += [
        "## Census and field-water diagnostics",
        "",
        f"At DBH ≥1 cm, the July 2015 simulation has {obs.nplant_model_ha:.1f} trees ha⁻¹, "
        f"compared with {obs.nplant_observed_ha:.1f} in the census. Basal areas are "
        f"{obs.basal_area_model_ha:.2f} and {obs.basal_area_observed_ha:.2f} m² ha⁻¹. "
        f"Model biomass expressed as dry mass is {obs.agb_model_implied_dry_Mg_ha:.2f} Mg ha⁻¹; "
        f"the archive's original all-stem estimate is {obs.agb_observed_original_all_stems_Mg_ha:.2f} "
        "Mg ha⁻¹. The latter comparison includes differences in allometry, traits and stem "
        "representation. Per-site and PFT comparisons retain both biomass estimators.",
        "",
    ]
    field = pd.read_csv(HERE / "results/field_swp_metrics.csv")
    field = field[
        (field.scenario == SCENARIOS[0]) & (field["filter"] == "outliers_removed")
    ].iloc[0]
    lines += [
        f"The paired soil-water dataset contains {field.n:.0f} field records. "
        f"A has a mean potential bias of {field.bias_MPa:.3f} MPa and RMSE "
        f"{field.rmse_MPa:.3f} MPa. The comparison joins each point sample to its site's "
        "daily profile at the recorded depth; site-specific residuals are retained in "
        "`field_swp_metrics_by_site.csv`.",
        "",
        "## Run records",
        "",
    ]
    provenance = json.loads((HERE / "results/model_provenance.json").read_text())
    commits = ", ".join(
        f"`{sha}`" for sha in sorted({r["source_commit"] for r in provenance})
    )
    audit = json.loads((HERE / "results/run_audit.json").read_text())
    closure = pd.concat(
        [
            pd.read_csv(HERE / f"results/{label}_site_stand_closure.csv")
            for label in ("A", "B")
        ]
    )
    lines += [
        f"The model provenance records identify commit(s) {commits}. "
        f"The analysis includes {len(audit)} completed historical runs and "
        f"{len(closure)} stand-aggregation checks. Numerical residuals and minimum-step "
        "exception counts are in `run_audit.json`; resolved process switches are in "
        "`module_audit.csv`. The figures are regenerated from these recorded trajectories.",
        "",
    ]
    (HERE / "results/RESULTS.md").write_text("\n".join(lines))
    if update_readme:
        path = HERE / "README.md"
        text = path.read_text()
        before, rest = text.split("<!-- results:start -->", 1)
        _, after = rest.split("<!-- results:end -->", 1)
        path.write_text(
            before
            + "<!-- results:start -->\n\n"
            + paragraph
            + "\n\n<!-- results:end -->"
            + after
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-readme", action="store_true")
    args = parser.parse_args()
    style()
    site_overview()
    contrasts()
    environment()
    soil_profiles()
    seasonal_profiles()
    site_responses()
    site_composition()
    report(args.update_readme)
