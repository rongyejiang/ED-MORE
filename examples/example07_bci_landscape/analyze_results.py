#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Aggregate only completed simulations, audit numerical behavior and compare held-out observations."""

from pathlib import Path
import argparse, json, tomllib
import netCDF4 as nc
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
MAIN = ["A_heterogeneous", "B_uniform_multisite", "C_uniform_single"]
SENS = ["S_wetland_aquifer", "S_no_cue", "S_single_patch_budget", "S_equal_depth"]


def values(var):
    return np.ma.asarray(var[:], dtype=float).filled(np.nan)


def audit_environment(name):
    folder = HERE / "output" / name
    sites = tomllib.loads((folder / "run.toml").read_text())["sites"]
    records = []
    with nc.Dataset(sorted(folder.glob(name + "-D-*.nc"))[0]) as d:
        assert int(values(d["n_site"])[0]) == len(sites), name
        for i, site in enumerate(sites):
            for key, variable in [
                ("area_fraction", "area_si"),
                ("elevation", "elevation_si"),
                ("slope", "slope_si"),
                ("aspect", "aspect_si"),
                ("depth", "soil_depth_si"),
                ("deep_temp", "deep_temp_si"),
            ]:
                actual = float(values(d[variable])[0, i])
                expected = float(site[key])
                assert np.isclose(actual, expected, rtol=0, atol=1e-11), (name, i, key)
                records.append(
                    dict(
                        scenario=name,
                        site_id=i + 1,
                        parameter=key,
                        expected=expected,
                        actual=actual,
                        passed=True,
                    )
                )
            actual_bc = int(values(d["bottom_bc_si"])[0, i])
            expected_bc = 2 if site["water_bottom_bc"] == "aquifer" else 1
            assert actual_bc == expected_bc, (name, i, "bottom boundary")
            records.append(
                dict(
                    scenario=name,
                    site_id=i + 1,
                    parameter="bottom_bc_code",
                    expected=expected_bc,
                    actual=actual_bc,
                    passed=True,
                )
            )
            n = int(values(d["n_soil_si"])[0, i])
            bottoms = -np.min(values(d["soil_z_bnds"])[0, i, :n], axis=-1)
            assert np.allclose(bottoms, site["layer_bottoms"], rtol=0, atol=1e-12), name
    return records


def read_run(name):
    folder = HERE / "output" / name
    assert (folder / "completed.json").exists(), name + " not complete"
    scalars = []
    by_site = []
    aggregation = []
    for file in sorted(folder.glob(name + "-D-*.nc")):
        with nc.Dataset(file) as d:
            t = d["time"]
            dates = pd.to_datetime(
                [x.strftime("%Y-%m-%d") for x in nc.num2date(t[:], t.units, t.calendar)]
            )
            seconds = np.diff(values(d["time_bnds"]), axis=1)[:, 0] * 86400
            columns = {"date": dates, "seconds": seconds}
            for key, var in d.variables.items():
                if key.endswith("_py") and var.dimensions == ("time", "polygon"):
                    columns[key] = values(var)[:, 0]
            frame = pd.DataFrame(columns)
            scalars.append(frame)
            areas = values(d["area_si"])[0]
            nsoil = values(d["n_soil_si"])[0].astype(int)
            nodes = -values(d["soil_z"])[0]
            bounds = values(d["soil_z_bnds"])[0]
            patch_site = values(d["patch_site"])[:, 0].astype(float)
            patch_area = (
                values(d["mean_area_pa"])[:, 0]
                if "mean_area_pa" in d.variables
                else values(d["area_pa"])[:, 0]
            )
            check_gpp = np.zeros(len(dates))
            for k in range(len(areas)):
                n = nsoil[k]
                z = nodes[k, :n]
                dz = abs(np.diff(bounds[k, :n], axis=1)[:, 0])
                theta = values(d["mean_soil_water_layer_si"])[:, 0, k, :n]
                psi = values(d["mean_soil_psi_layer_si"])[:, 0, k, :n]
                temp = values(d["mean_soil_temp_layer_si"])[:, 0, k, :n]
                mask = patch_site == k + 1
                weights = np.where(mask, patch_area, 0)
                s = pd.DataFrame(
                    {
                        "date": dates,
                        "site_id": k + 1,
                        "area_fraction": areas[k],
                        "soil_water_mm": theta @ dz * 1000,
                        "psi_15cm": np.array([np.interp(0.15, z, row) for row in psi]),
                        "theta_15cm": np.array(
                            [np.interp(0.15, z, row) for row in theta]
                        ),
                        "soil_temp_15cm": np.array(
                            [np.interp(0.15, z, row) for row in temp]
                        ),
                    }
                )
                for var, label in [
                    ("mean_gpp_pa", "gpp_umol"),
                    ("mean_et_pa", "et_kg_s"),
                    ("mean_lai_pa", "lai"),
                    ("mean_agb_pa", "agb_kgC_m2"),
                ]:
                    s[label] = np.nansum(
                        np.where(mask, values(d[var])[:, 0] * weights, 0), axis=1
                    )
                s["patch_area_sum"] = np.nansum(weights, axis=1)
                check_gpp += s.gpp_umol.to_numpy() * areas[k]
                for var in [
                    "mean_air_temp_si",
                    "mean_sw_in_si",
                    "mean_par_beam_si",
                    "mean_nir_beam_si",
                ]:
                    if var in d.variables:
                        s[var] = values(d[var])[:, 0, k]
                s["mean_direct_beam_si"] = s.mean_par_beam_si + s.mean_nir_beam_si
                by_site.append(s)
            aggregation.append(
                dict(
                    file=file.name,
                    max_absolute_gpp_patch_to_polygon_error=float(
                        np.max(abs(check_gpp - frame.mean_gpp_py.to_numpy()))
                    ),
                )
            )
    daily = pd.concat(scalars, ignore_index=True).sort_values("date")
    site = pd.concat(by_site, ignore_index=True).sort_values(["site_id", "date"])
    assert not daily.date.duplicated().any()
    assert len(daily) == 2557, (name, len(daily))
    assert daily.date.iloc[0] == pd.Timestamp("2011-01-01") and daily.date.iloc[
        -1
    ] == pd.Timestamp("2017-12-31")
    assert np.isfinite(daily.select_dtypes("number")).all().all()
    daily["scenario"] = name
    site["scenario"] = name
    return daily, site, aggregation


def layer_profiles():
    """Seasonal profiles at each site's own layer centers, without vertical remapping."""
    folder = HERE / "output/A_heterogeneous"
    rows = []
    for path in sorted(folder.glob("*-D-*.nc")):
        with nc.Dataset(path) as dataset:
            time = dataset["time"]
            dates = pd.DatetimeIndex(
                [
                    v.strftime("%Y-%m-%d")
                    for v in nc.num2date(time[:], time.units, time.calendar)
                ]
            )
            if not (dates.year == 2016).any():
                continue
            counts = values(dataset["n_soil_si"])[0].astype(int)
            centers = -values(dataset["soil_z"])[0]
            for season, months in [("Jan-Mar", [1, 2, 3]), ("Jul-Sep", [7, 8, 9])]:
                select = (dates.year == 2016) & dates.month.isin(months)
                for key in ["mean_soil_water_layer_si", "mean_soil_psi_layer_si"]:
                    data = values(dataset[key])[select, 0]
                    for site, count in enumerate(counts):
                        for layer in range(count):
                            rows.append(
                                dict(
                                    site_id=site + 1,
                                    layer=layer + 1,
                                    season=season,
                                    depth_m=centers[site, layer],
                                    variable=key,
                                    value=float(data[:, site, layer].mean()),
                                )
                            )
    pd.DataFrame(rows).to_csv(HERE / "results/soil_layer_profiles.csv", index=False)


def external_validation(sites):
    obs = pd.read_csv(HERE / "data/field_swp_labeled.csv", parse_dates=["date"])
    obs["observed_psi"] = obs.swp
    obs["usable"] = obs.swp.notna() & (obs.outlier != 1) & obs.depth.notna()
    pairs = []
    metrics = []
    for name in MAIN + (
        ["S_equal_depth"] if "S_equal_depth" in set(sites.scenario) else []
    ):
        pred = sites[sites.scenario == name][["date", "site_id", "psi_15cm"]].rename(
            columns={"psi_15cm": "predicted_psi"}
        )
        x = obs.copy()
        if name == "C_uniform_single":
            x["source_unit"] = x.site_id
            x.site_id = 1
        x = x.merge(pred, on=["date", "site_id"], how="left", validate="many_to_one")
        x["predicted_psi_15cm"] = x.predicted_psi
        x["predicted_psi"] = np.nan
        # Samples nominally target 15 cm, but recorded depths range from 12 to 22 cm.
        # Match each recorded depth to the modeled layer centers on its sampling day.
        for path in sorted((HERE / "output" / name).glob("*-D-*.nc")):
            with nc.Dataset(path) as d:
                t = d["time"]
                dates = pd.DatetimeIndex(
                    [
                        v.strftime("%Y-%m-%d")
                        for v in nc.num2date(t[:], t.units, t.calendar)
                    ]
                )
                positions = dates.get_indexer(x.date)
                selected = x[(positions >= 0) & x.depth.notna()]
                if selected.empty:
                    continue
                psi = values(d["mean_soil_psi_layer_si"])
                centers = -values(d["soil_z"])[0]
                counts = values(d["n_soil_si"])[0].astype(int)
                for idx, row in selected.iterrows():
                    sid = int(row.site_id) - 1
                    n = counts[sid]
                    z = centers[sid, :n]
                    depth = row.depth / 100
                    assert z[0] <= depth <= z[-1], (name, idx, depth)
                    x.at[idx, "predicted_psi"] = np.interp(
                        depth, z, psi[positions[idx], 0, sid, :n]
                    )
        assert x.loc[x.usable, "predicted_psi"].notna().all(), name
        x["scenario"] = name
        if name == "C_uniform_single":
            x.site_id = x.source_unit
        pairs.append(x)
        for filter_name, mask in [
            ("outliers_removed", x.usable),
            ("dry_index_subset", x.usable & (x.exclude == 0)),
        ]:
            xx = x[mask & x.predicted_psi.notna()]
            r = xx.predicted_psi - xx.observed_psi
            log_pair = xx[(xx.predicted_psi < 0) & (xx.observed_psi < 0)]
            lr = np.log10(-log_pair.predicted_psi) - np.log10(-log_pair.observed_psi)
            metrics.append(
                dict(
                    scenario=name,
                    filter=filter_name,
                    n=len(xx),
                    records_without_depth=int(x.depth.isna().sum()),
                    records_flagged_outlier=int((x.outlier == 1).sum()),
                    n_log_suction_pairs=len(log_pair),
                    bias_MPa=float(r.mean()),
                    rmse_MPa=float(np.sqrt(np.mean(r * r))),
                    rmse_log10_suction=float(np.sqrt(np.mean(lr * lr))),
                )
            )
    all_pairs = pd.concat(pairs)
    all_pairs.to_csv(HERE / "results/field_swp_pairs.csv", index=False)
    by_site = []
    for (scenario, sid), group in all_pairs[all_pairs.usable].groupby(
        ["scenario", "site_id"]
    ):
        residual = group.predicted_psi - group.observed_psi
        by_site.append(
            dict(
                scenario=scenario,
                site_id=int(sid),
                n=len(group),
                observed_mean_MPa=float(group.observed_psi.mean()),
                predicted_mean_MPa=float(group.predicted_psi.mean()),
                bias_MPa=float(residual.mean()),
                rmse_MPa=float(np.sqrt(np.mean(residual**2))),
            )
        )
    pd.DataFrame(by_site).to_csv(
        HERE / "results/field_swp_metrics_by_site.csv", index=False
    )
    pd.DataFrame(metrics).to_csv(HERE / "results/field_swp_metrics.csv", index=False)
    obsstand = pd.read_csv(HERE / "data/census_validation_by_site_pft.csv")
    comparison = []
    for name in MAIN + ["S_single_patch_budget", "S_equal_depth"]:
        path = HERE / "output" / name / "stand_2015-07-01.csv.gz"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df = df[df.dbh >= 1].copy()
        df["stems_m2"] = df["share"] * df.nplant
        df["ba_m2_ha"] = df.stems_m2 * np.pi * (df.dbh / 200) ** 2 * 10000
        df["agb_kgC_m2"] = df.stems_m2 * df.agb
        for pft in [0, 1, 2, 3]:
            f = df if pft == 0 else df[df.pft == pft]
            o = obsstand[obsstand.census_year == 2015]
            if pft:
                o = o[o.pft == pft]
            comparison.append(
                dict(
                    scenario=name,
                    date="2015-07-01",
                    pft=pft,
                    nplant_model_ha=float(f.stems_m2.sum() * 10000),
                    nplant_observed_ha=float(o.n_trees.sum() / 50),
                    basal_area_model_ha=float(f.ba_m2_ha.sum()),
                    basal_area_observed_ha=float(o.basal_area_m2.sum() / 50),
                    basal_area_observed_all_stems_ha=float(
                        o.original_all_stem_ba_m2.sum() / 50
                    ),
                    agb_observed_original_all_stems_Mg_ha=float(
                        o.original_all_stem_agb_Mg.sum() / 50
                    ),
                    agb_model_kgC_m2=float(f.agb_kgC_m2.sum()),
                    agb_model_implied_dry_Mg_ha=float(f.agb_kgC_m2.sum() * 20),
                    agb_original_at_model_half_carbon_kgC_m2=float(
                        o.original_all_stem_agb_Mg.sum() / 50 * 0.05
                    ),
                    agb_observed_common_allometry_kgC_m2=float(
                        o.model_agb_kgC.sum() / 500000
                    ),
                )
            )
    pd.DataFrame(comparison).to_csv(
        HERE / "results/census_2015_comparison.csv", index=False
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--available", action="store_true")
    ap.add_argument(
        "--source-commit",
        help="verified model commit for archives predating execution manifests",
    )
    args = ap.parse_args()
    daily_all = []
    site_all = []
    annual = []
    audits = []
    environments = []
    init = []
    modules = []
    aggregation = []
    provenance = []
    names = MAIN + SENS
    if args.available:
        names = [n for n in names if (HERE / "output" / n / "completed.json").exists()]
    for name in names:
        manifest_path = HERE / "output" / name / "execution_manifest.json"
        if manifest_path.exists():
            record = json.loads(manifest_path.read_text())
            provenance.append(
                dict(
                    scenario=name,
                    source_commit=record["source_commit"],
                    evidence="execution_manifest",
                    library_sha256=record["library_sha256"],
                )
            )
        elif args.source_commit:
            provenance.append(
                dict(
                    scenario=name,
                    source_commit=args.source_commit,
                    evidence="explicit archive annotation",
                )
            )
        else:
            raise ValueError(
                f"{name}: no execution manifest; supply the verified --source-commit."
            )
        environments.extend(audit_environment(name))
        print("Analyze " + name, flush=True)
        daily, site, agg = read_run(name)
        daily_all.append(daily)
        site_all.append(site)
        aggregation.extend([dict(scenario=name, **r) for r in agg])
        for year, g in daily.groupby(daily.date.dt.year):
            row = dict(
                scenario=name,
                year=int(year),
                days=len(g),
                adjustment_year=bool(year == 2011),
            )
            for var, label in [
                ("mean_gpp_py", "gpp_kgC_m2_yr"),
                ("mean_npp_py", "npp_kgC_m2_yr"),
                ("mean_rhet_py", "rh_kgC_m2_yr"),
                ("mean_nee_py", "nee_kgC_m2_yr"),
            ]:
                row[label] = float((g[var] * g.seconds).sum() * 12e-9)
            for var, label in [
                ("mean_et_py", "et_mm_yr"),
                ("mean_precip_py", "precip_mm_yr"),
                ("mean_runoff_py", "runoff_mm_yr"),
                ("mean_drainage_py", "drainage_mm_yr"),
                ("mean_transp_py", "transp_mm_yr"),
            ]:
                row[label] = float((g[var] * g.seconds).sum())
            for var, label in [
                ("mean_lai_py", "lai_mean"),
                ("mean_agb_py", "agb_mean_kgC_m2"),
                ("mean_soil_water_total_py", "soil_water_mean_mm"),
            ]:
                row[label] = float(np.average(g[var], weights=g.seconds))
            annual.append(row)
        folder = HERE / "output" / name
        progress = json.loads((folder / "progress.json").read_text())
        init.append(dict(scenario=name, **progress[0]))
        record = pd.read_csv(folder / (name + "_parameters.csv"))
        flags = record[
            record.key.str.contains(
                r"_on$|phenology\.(?:flush_cue_mask|shed_cue_mask)|use_boundary_layer|thermal_acclimation|apply_elevation_lapse|dt_fast|time_integrator|water_bottom_bc|max_patch|min_patch_area|soil_carbon\.(?:decomp_scheme|step_solver|k_micr|k_pass)|trait_dynamics\.|fast\.(?:rtol|water_atol)"
            )
        ].copy()
        flags["scenario"] = name
        modules.append(flags)
        required = [
            "run.slow_on",
            "fast.fast_biophysics_on",
            "fast.canopy_water_on",
            "soil_carbon.soil_carbon_on",
            "demography.demography_on",
            "demography.recruitment_on",
            "demography.patch_disturbance_on",
            "trait_dynamics.trait_plasticity_on",
        ]
        for key in required:
            assert (
                record[record.key == key].value.astype(str).str.strip() == "true"
            ).all() and (record.key == key).any(), (name, key)
        log = (folder / "run.log").read_text()
        a = dict(
            scenario=name,
            complete="OK: simulation completed" in log
            and progress[-1]["date"] == "2018-01-01",
            daily_records=len(daily),
            slow_ledger_closed="VERDICT: every phase closes within tolerance" in log,
            max_daily_abs_energy_residual_W_m2=float(
                abs(daily.mean_resid_energy_py).max()
            ),
            max_daily_abs_water_residual_kg_m2_s=float(
                abs(daily.mean_resid_water_py).max()
            ),
            max_water_unconverged=float(daily.mean_work_water_nfail_py.max()),
            max_stage_clamps=float(daily.mean_work_clamp_stage_py.max()),
            days_with_water_minimum_step_exceptions=int(
                (daily.mean_work_water_nfail_py > 0).sum()
            ),
            water_exception_fraction_ppm=float(
                np.sum(daily.mean_work_water_nfail_py * daily.seconds)
                / np.sum(daily.mean_work_water_nsub_py * daily.seconds)
                * 1e6
            ),
            max_rk45_rescues=float(daily.mean_work_rk45_rescue_py.max()),
            max_site_patch_area_error=float(abs(site.patch_area_sum - 1).max()),
            elapsed_seconds=float(progress[-1]["elapsed_seconds"]),
        )
        audits.append(a)
    if not daily_all:
        return
    (HERE / "results/model_provenance.json").write_text(
        json.dumps(provenance, indent=2)
    )
    daily = pd.concat(daily_all)
    sites = pd.concat(site_all)
    daily.to_csv(HERE / "results/daily_polygon.csv.gz", index=False)
    daily.loc[
        daily.mean_work_water_nfail_py > 0,
        ["scenario", "date", "mean_work_water_nfail_py", "mean_work_water_nsub_py"],
    ].to_csv(HERE / "results/water_minimum_step_exception_days.csv", index=False)
    sites.to_csv(HERE / "results/daily_sites.csv.gz", index=False)
    annual = pd.DataFrame(annual)
    annual.to_csv(HERE / "results/annual_metrics.csv", index=False)
    pd.DataFrame(init).to_csv(HERE / "results/initialization_audit.csv", index=False)
    pd.concat(modules).to_csv(HERE / "results/module_audit.csv", index=False)
    pd.DataFrame(aggregation).to_csv(
        HERE / "results/site_flux_aggregation_audit.csv", index=False
    )
    (HERE / "results/run_audit.json").write_text(json.dumps(audits, indent=2))
    pd.DataFrame(environments).to_csv(
        HERE / "results/environment_runtime_audit.csv", index=False
    )
    if all(n in names for n in MAIN):
        layer_profiles()
        external_validation(sites)
        contrasts = []
        for left, right, label in [
            ("A_heterogeneous", "B_uniform_multisite", "A-B environmental"),
            ("B_uniform_multisite", "C_uniform_single", "B-C grouping"),
            ("A_heterogeneous", "C_uniform_single", "A-C total"),
        ]:
            a = annual[(annual.scenario == left) & (~annual.adjustment_year)].set_index(
                "year"
            )
            b = annual[
                (annual.scenario == right) & (~annual.adjustment_year)
            ].set_index("year")
            for metric in [
                "gpp_kgC_m2_yr",
                "npp_kgC_m2_yr",
                "et_mm_yr",
                "runoff_mm_yr",
                "lai_mean",
                "agb_mean_kgC_m2",
            ]:
                delta = a[metric] - b[metric]
                contrasts.append(
                    dict(
                        contrast=label,
                        metric=metric,
                        left_mean=float(a[metric].mean()),
                        right_mean=float(b[metric].mean()),
                        mean_difference=float(delta.mean()),
                        relative_percent=float(100 * delta.mean() / b[metric].mean()),
                        min_year_difference=float(delta.min()),
                        max_year_difference=float(delta.max()),
                    )
                )
        pd.DataFrame(contrasts).to_csv(
            HERE / "results/contrasts_2012_2017.csv", index=False
        )
    print(json.dumps(audits, indent=2))


if __name__ == "__main__":
    main()
