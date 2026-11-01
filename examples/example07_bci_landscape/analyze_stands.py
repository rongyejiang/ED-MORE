#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reconstruct site stands from patch area and cohort abundance; check polygon closure."""

from pathlib import Path
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
KEYS = ["agb_kgC_m2", "lai", "density_ha", "basal_area_m2_ha"]


def reconstruct(scenario, sites):
    """Recover site and PFT stands and verify their area-weighted polygon totals."""
    prefix = scenario.split("_", 1)[0]
    folder = HERE / "output" / scenario
    history = {x["date"]: x for x in json.loads((folder / "progress.json").read_text())}
    files = [(pd.Timestamp("2011-01-01"), folder / "stand_initial.csv.gz")]
    files += [
        (pd.Timestamp(p.name[6:16]), p)
        for p in sorted(folder.glob("stand_[0-9]*.csv.gz"))
    ]
    records, closure = [], []
    for date, path in files:
        c = pd.read_csv(path)
        weights = c.site.map(sites.area_fraction)
        assert np.allclose(c.share, c.area * weights, rtol=1e-12, atol=1e-14)
        c["agb_kgC_m2"] = c.area * c.nplant * c.agb
        c["lai"] = c.area * c.nplant * c.leaf_area
        c["density_ha"] = c.area * c.nplant * 10000
        c["basal_area_m2_ha"] = c.density_ha * np.pi * (c.dbh / 200) ** 2
        for threshold in [0, 1]:
            g = c[c.dbh >= threshold].groupby(["site", "pft"])[KEYS].sum()
            g = g.reindex(
                pd.MultiIndex.from_product(
                    [range(1, 9), range(1, 4)], names=["site", "pft"]
                ),
                fill_value=0,
            ).reset_index()
            g["date"] = date
            g["dbh_min_cm"] = threshold
            for key in ["agb_kgC_m2", "lai", "density_ha", "basal_area_m2_ha"]:
                g[key + "_fraction"] = g[key] / g.groupby("site")[key].transform("sum")
            records.append(g)
            if threshold == 0:
                item = history[str(date.date())]
                for key, expected_key, scale in [
                    ("agb_kgC_m2", "agb_kgC_m2", 1),
                    ("lai", "lai", 1),
                    ("density_ha", "nplant_m2", 10000),
                    ("basal_area_m2_ha", "basal_area_m2_ha", 1),
                ]:
                    actual = float((g[key] * g.site.map(sites.area_fraction)).sum())
                    expected = item[expected_key] * scale
                    assert np.isclose(actual, expected, rtol=1e-10, atol=1e-11), (
                        date,
                        key,
                        actual,
                        expected,
                    )
                    closure.append(
                        dict(
                            date=date,
                            metric=key,
                            reconstructed=actual,
                            runtime_total=expected,
                            absolute_error=abs(actual - expected),
                        )
                    )
    pft = pd.concat(records, ignore_index=True)
    pft.to_csv(HERE / f"results/{prefix}_site_pft_monthly.csv.gz", index=False)
    pd.DataFrame(closure).to_csv(
        HERE / f"results/{prefix}_site_stand_closure.csv", index=False
    )
    monthly = pft.groupby(["date", "dbh_min_cm", "site"])[KEYS].sum().reset_index()
    monthly.to_csv(HERE / f"results/{prefix}_site_stand_monthly.csv", index=False)
    return pft, monthly


def census_diagnostics(sites, pft, monthly):
    """Compare the heterogeneous forest with the census at a common diameter threshold."""
    obs = pd.read_csv(HERE / "data/census_validation_by_site_pft.csv").rename(
        columns={"site_id": "site"}
    )
    area = obs.site.map(sites.area_ha)
    obs["density_ha"] = obs.n_trees / area
    obs["basal_area_m2_ha"] = obs.basal_area_m2 / area
    obs["agb_kgC_m2"] = obs.model_agb_kgC / (area * 10000)
    obs["original_all_stem_agb_dry_Mg_ha"] = obs.original_all_stem_agb_Mg / area
    for key in ["agb_kgC_m2", "density_ha", "basal_area_m2_ha"]:
        obs[key + "_fraction"] = obs[key] / obs.groupby(["census_year", "site"])[
            key
        ].transform("sum")
    obs.to_csv(HERE / "results/site_census_composition.csv", index=False)
    model15 = pft[(pft.date == "2015-07-01") & (pft.dbh_min_cm == 1)]
    comparison = model15.merge(
        obs[obs.census_year == 2015],
        on=["site", "pft"],
        suffixes=("_model", "_census"),
        validate="one_to_one",
    )
    for key in ["agb_kgC_m2", "density_ha", "basal_area_m2_ha"]:
        comparison[key + "_bias_percent"] = 100 * (
            comparison[key + "_model"] / comparison[key + "_census"] - 1
        )
    comparison.to_csv(HERE / "results/A_site_pft_census_2015.csv", index=False)
    daily = pd.read_csv(HERE / "results/daily_sites.csv.gz", parse_dates=["date"])
    daily = daily[(daily.scenario == "A_heterogeneous") & (daily.date.dt.year >= 2012)]
    summary = (
        daily.groupby("site_id")[["agb_kgC_m2", "lai"]]
        .mean()
        .rename(
            columns={
                "agb_kgC_m2": "mean_agb_kgC_m2_2012_2017",
                "lai": "mean_lai_2012_2017",
            }
        )
    )
    summary["unit"] = sites.name
    summary["area_ha"] = sites.area_ha
    summary["area_fraction"] = sites.area_fraction
    for date, label in [
        ("2011-01-01", "initial"),
        ("2015-07-01", "2015"),
        ("2018-01-01", "final"),
    ]:
        m = monthly[(monthly.date == date) & (monthly.dbh_min_cm == 1)].set_index(
            "site"
        )
        for key in KEYS:
            summary[f"{key}_{label}_dbh1"] = m[key]
    census15 = obs[obs.census_year == 2015].groupby("site").sum(numeric_only=True)
    for key in ["agb_kgC_m2", "density_ha", "basal_area_m2_ha"]:
        summary[key + "_census2015"] = census15[key]
        summary[key + "_bias2015_percent"] = 100 * (
            summary[key + "_2015_dbh1"] / census15[key] - 1
        )
    summary["agb_original_all_stem_dry_Mg_ha_census2015"] = (
        census15.original_all_stem_agb_dry_Mg_ha
    )
    summary.to_csv(HERE / "results/A_site_stand_summary.csv")
    return obs, summary


def paired_sites(sites, a, b):
    """Pair the same forest under heterogeneous and equivalent environments."""
    join = ["date", "dbh_min_cm", "site", "pft"]
    assert a[join].equals(b[join]), (
        "A and B must cover the same snapshots, sites and PFTs"
    )
    pair = a.merge(b, on=join, suffixes=("_A", "_B"), validate="one_to_one")
    for key in KEYS:
        pair[key + "_difference"] = pair[key + "_A"] - pair[key + "_B"]
    pair["agb_share_difference_pp"] = 100 * (
        pair.agb_kgC_m2_fraction_A - pair.agb_kgC_m2_fraction_B
    )
    initial = pair[pair.date == "2011-01-01"]
    assert len(initial) and np.allclose(
        initial[[key + "_difference" for key in KEYS]], 0, atol=1e-12
    )
    assert np.allclose(
        pair.groupby(["date", "dbh_min_cm", "site"]).agb_share_difference_pp.sum(),
        0,
        atol=1e-10,
    )
    pair.to_csv(HERE / "results/AB_site_pft_monthly.csv.gz", index=False)

    daily = pd.read_csv(HERE / "results/daily_sites.csv.gz", parse_dates=["date"])
    daily = daily[
        daily.scenario.isin(["A_heterogeneous", "B_uniform_multisite"])
        & daily.date.between("2012-01-01", "2017-12-31")
    ].copy()
    dates = pd.date_range("2012-01-01", "2017-12-31")
    expected = pd.MultiIndex.from_product(
        [["A_heterogeneous", "B_uniform_multisite"], sites.index, dates],
        names=["scenario", "site_id", "date"],
    )
    actual = daily.set_index(["scenario", "site_id", "date"]).index
    assert actual.is_unique and actual.sort_values().equals(expected.sort_values())
    daily["et_mm_day"] = daily.et_kg_s * 86400
    daily["agb_MgC_ha"] = daily.agb_kgC_m2 * 10
    metrics = [
        "gpp_umol",
        "et_mm_day",
        "agb_MgC_ha",
        "lai",
        "psi_15cm",
        "soil_water_mm",
    ]
    assert np.isfinite(daily[metrics]).all().all()
    means = daily.groupby(["scenario", "site_id"])[metrics].mean()
    summary = sites[["name", "area_ha", "area_fraction"]].copy()
    for metric in metrics:
        for label, scenario in [("A", "A_heterogeneous"), ("B", "B_uniform_multisite")]:
            summary[metric + "_" + label] = means.loc[scenario, metric]
        difference = summary[metric + "_A"] - summary[metric + "_B"]
        summary[metric + "_difference"] = difference
        # Water potential is negative; report its absolute MPa difference.
        if metric != "psi_15cm":
            summary[metric + "_relative_percent"] = (
                100 * difference / summary[metric + "_B"]
            )
            baseline = (summary.area_fraction * summary[metric + "_B"]).sum()
            summary[metric + "_polygon_contribution_pp"] = (
                100 * summary.area_fraction * difference / baseline
            )
    summary.index.name = "site_id"
    summary.to_csv(HERE / "results/AB_site_summary.csv")
    return pair, summary


def main():
    sites = pd.DataFrame(json.loads((HERE / "data/sites.json").read_text())).set_index(
        "census_site_id"
    )
    a, monthly = reconstruct("A_heterogeneous", sites)
    b, _ = reconstruct("B_uniform_multisite", sites)
    census_diagnostics(sites, a, monthly)
    paired_sites(sites, a, b)


if __name__ == "__main__":
    main()
