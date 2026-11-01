#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the BCI site assignments, hydraulic profiles and run configurations."""

from pathlib import Path
import copy, io, json, sys, zipfile
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
sys.path.insert(0, str(MODEL / "python"))
from edmore.config import load_toml, write_toml as model_write_toml


def write_toml(path, obj):
    model_write_toml(path, json.loads(json.dumps(obj, default=lambda v: v.item())))


def dump(path, obj):
    path.write_text(
        json.dumps(obj, indent=2, allow_nan=False, default=lambda v: v.item())
    )


def theta(psi, alpha, n):
    head = np.abs(np.asarray(psi)) * 1e6 / 9806.65
    return 0.1 + 0.5 * (1 + (alpha * head) ** n) ** (-(1 - 1 / n))


def fit_curve(psi, target, weights=None):
    weights = np.ones_like(target) if weights is None else weights
    opt = least_squares(
        lambda p: (theta(psi, np.exp(p[0]), p[1]) - target) * weights,
        [np.log(2), 1.23],
        bounds=([np.log(0.02), 1.03], [np.log(200), 2.5]),
    )
    return float(np.exp(opt.x[0])), float(opt.x[1])


def normal_slope(g):
    normals = np.c_[-g.grad_x.to_numpy(), -g.grad_y.to_numpy(), np.ones(len(g))]
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    normal = normals.mean(axis=0)
    normal /= np.linalg.norm(normal)
    return float(np.degrees(np.arccos(normal[2]))), float(
        np.degrees(np.arctan2(normal[0], normal[1])) % 360
    )


def main():
    data = HERE / "data"
    raw = data / "raw"
    configs = HERE / "configs"
    for path in (data, configs, HERE / "results", HERE / "figures"):
        path.mkdir(parents=True, exist_ok=True)
    elev = raw / "BCIelev.tsv"
    habitat = raw / "bci_habitat_observed.tsv"
    zip_path = raw / "Kupers_et_al.zip"
    retention = raw / "BCI_retention_curves.txt"
    swp = raw / "BCI_SWP_SWC.txt"
    census_path = raw / "bci_2010.csv"
    wd_path = MODEL / "examples/example03_demography/bci_wood_density.csv"
    for path in (
        elev,
        habitat,
        zip_path,
        retention,
        swp,
        census_path,
        raw / "bci_era5land_2003-2022.nc",
    ):
        if not path.exists():
            raise SystemExit(f"Missing {path.name}; run fetch_data.py first.")
    z = (
        pd.read_csv(elev, sep="\t")
        .pivot(index="y", columns="x", values="elev")
        .sort_index()
        .sort_index(axis=1)
    )
    assert z.shape == (101, 201) and z.notna().all().all()
    q = pd.read_csv(habitat, sep="\t").sort_values(["x", "y"]).reset_index(drop=True)
    assert len(q) == 1250 and not q.duplicated(["x", "y"]).any()
    q["patch_id"] = (q.x // 20 * 25 + q.y // 20 + 1).astype(int)
    soilzip = zipfile.ZipFile(zip_path)
    soilmember = next(n for n in soilzip.namelist() if n.endswith("BCI_soil_type.txt"))
    soil = pd.read_csv(io.BytesIO(soilzip.read(soilmember)), sep="\t")
    soilgrid = soil.pivot(index="y", columns="x", values="soiltype")
    classes = ["AVA", "Marron", "Fairchild", "Swamp"]
    measures = []
    weights = np.outer([0.5, 1, 1, 1, 0.5], [0.5, 1, 1, 1, 0.5])
    weights /= weights.sum()
    for r in q.itertuples():
        zz = z.loc[r.y : r.y + 20, r.x : r.x + 20].to_numpy()
        # Four triangles of the 20-m survey cell, following Harms; plane gradient for aspect.
        sw, se, nw, ne = zz[0, 0], zz[0, -1], zz[-1, 0], zz[-1, -1]
        gx = ((se - sw) + (ne - nw)) / 40
        gy = ((nw - sw) + (ne - se)) / 40
        corners = [
            (se - sw, nw - sw),
            (se - sw, ne - se),
            (ne - nw, nw - sw),
            (ne - nw, ne - se),
        ]
        sl = np.mean([np.degrees(np.arctan(np.hypot(a, b) / 20)) for a, b in corners])
        ss = soilgrid.loc[r.y : r.y + 20, r.x : r.x + 20].to_numpy().copy()
        ss[(ss == "Swamp") & (r.habitat != "swamp")] = "Marron"
        if r.habitat == "swamp":
            ss[:] = "Swamp"
        fractions = {c: float(weights[ss == c].sum()) for c in classes}
        majority = max(classes, key=fractions.get)
        measures.append(
            dict(
                elevation=float(np.sum(weights * zz)),
                slope_class_deg=float(sl),
                grad_x=float(gx),
                grad_y=float(gy),
                soil_majority=majority,
                **{"fraction_" + c: v for c, v in fractions.items()},
            )
        )
    q = pd.concat([q, pd.DataFrame(measures)], axis=1)
    effective = q.habitat.copy()
    inferred = q.habitat.isin(["mixed", "young"])
    effective.loc[inferred] = np.where(
        q.loc[inferred, "slope_class_deg"] >= 7,
        "slope",
        np.where(q.loc[inferred, "elevation"] >= 152, "hi_plateau", "low_plateau"),
    )
    q["terrain_class"] = effective

    def unit(r):
        if r.habitat == "swamp":
            return "seasonal_swamp"
        if r.habitat == "stream":
            return "stream_corridor"
        if r.soil_majority == "Fairchild":
            return "fairchild"
        if r.terrain_class == "slope":
            return "slope_" + r.soil_majority.lower()
        if r.soil_majority == "Marron":
            return "plateau_marron"
        return "high_ava" if r.terrain_class == "hi_plateau" else "low_ava"

    q["unit"] = q.apply(unit, axis=1)
    order = [
        "high_ava",
        "low_ava",
        "plateau_marron",
        "slope_ava",
        "slope_marron",
        "fairchild",
        "stream_corridor",
        "seasonal_swamp",
    ]
    assert set(q.unit) == set(order), q.unit.value_counts()
    q["site_id"] = q.unit.map({name: i + 1 for i, name in enumerate(order)})
    q.to_csv(data / "quadrat_assignment.csv", index=False)

    # Locations inherit the soil-map class, corrected by the containing observed swamp quadrat.
    def label_points(df):
        t = df.copy()
        t["qx"] = np.minimum(t.x // 20 * 20, 980).astype(int)
        t["qy"] = np.minimum(t.y // 20 * 20, 480).astype(int)
        t = t.merge(
            q[["x", "y", "habitat", "site_id", "unit"]],
            left_on=["qx", "qy"],
            right_on=["x", "y"],
            suffixes=("", "_q"),
            validate="many_to_one",
        )
        t["soiltype"] = [
            soilgrid.at[
                int(np.clip(round(y / 5) * 5, 0, 500)),
                int(np.clip(round(x / 5) * 5, 0, 1000)),
            ]
            for x, y in zip(t.x, t.y)
        ]
        t.loc[(t.soiltype == "Swamp") & (t.habitat != "swamp"), "soiltype"] = "Marron"
        t.loc[t.habitat == "swamp", "soiltype"] = "Swamp"
        return t

    ret = label_points(pd.read_csv(retention, sep="\t"))
    ret.to_csv(data / "retention_labeled.csv", index=False)
    field = label_points(pd.read_csv(swp, sep="\t"))
    field.to_csv(data / "field_swp_labeled.csv", index=False)
    soil_params = []
    for soilclass, g in ret.groupby("soiltype"):
        fit = g[
            g.swp <= -0.05
        ].copy()  # zero/near-zero psychrometer readings cannot constrain porosity.
        w = 1 / np.sqrt(fit.groupby("site").swp.transform("size").to_numpy())
        for rho in (0.8, 0.9, 1.0):
            a, n = fit_curve(fit.swp.to_numpy(), fit.swc.to_numpy() * 0.01 * rho, w)
            soil_params.append(
                dict(
                    soil=soilclass,
                    bulk_density_assumed=rho,
                    alpha=a,
                    n=n,
                    theta_sat=0.6,
                    theta_res=0.1,
                    n_samples=len(fit),
                    n_locations=int(fit.site.nunique()),
                    rmse_theta=float(
                        np.sqrt(
                            np.mean(
                                (theta(fit.swp, a, n) - fit.swc.to_numpy() * 0.01 * rho)
                                ** 2
                            )
                        )
                    ),
                )
            )
    pd.DataFrame(soil_params).to_csv(data / "retention_fits.csv", index=False)
    sp = {s["soil"]: s for s in soil_params if s["bulk_density_assumed"] == 0.9}
    # Profile-depth scenarios (m), METHODS.md: Soil profiles; not fitted to model outputs.
    depth = {"AVA": 2.0, "Marron": 0.8, "Fairchild": 1.0, "Swamp": 2.0}
    psi = -np.geomspace(0.01, 10, 120)
    sites = []
    site_details = []
    for name in order:
        g = q[q.unit == name]
        weights_c = np.array([g["fraction_" + c].mean() for c in classes])
        depths = np.array([depth[c] for c in classes])
        dz = float(weights_c @ depths)
        target = (
            sum(
                w * d * theta(psi, sp[c]["alpha"], sp[c]["n"])
                for w, d, c in zip(weights_c, depths, classes)
            )
            / dz
        )
        a, n = fit_curve(psi, target)
        slope, aspect = normal_slope(g)
        s = dict(
            area_fraction=len(g) / 1250,
            census_site_id=int(g.site_id.iloc[0]),
            elevation=float(g.elevation.mean()),
            slope=slope,
            aspect=aspect,
            depth=dz,
            theta_sat=0.6,
            theta_res=0.1,
            curve_par_a=a,
            curve_par_n=n,
            ksat=1e-5,
            water_bottom_bc="free_drain",
            deep_temp=298.65,
            deep_depth=dz * 0.875 + 1.973 / np.sqrt(2),
            layer_bottoms=(
                np.array([0.025, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1]) * dz
            ).tolist(),
        )
        sites.append(s)
        site_details.append(
            dict(
                name=name,
                n_quadrats=len(g),
                area_ha=len(g) * 0.04,
                **s,
                within_soil_storage_rmse_mm=float(
                    np.sqrt(np.mean((theta(psi, a, n) - target) ** 2)) * dz * 1000
                ),
                soil_fractions=dict(zip(classes, weights_c.tolist())),
            )
        )
    zbar = sum(s["area_fraction"] * s["depth"] for s in sites)
    target = (
        sum(
            s["area_fraction"]
            * s["depth"]
            * theta(psi, s["curve_par_a"], s["curve_par_n"])
            for s in sites
        )
        / zbar
    )
    alpha, n = fit_curve(psi, target)
    sl, asp = normal_slope(q)
    equivalent = copy.deepcopy(sites[0])
    equivalent.update(
        area_fraction=1.0,
        census_site_id=1,
        elevation=float(q.elevation.mean()),
        slope=sl,
        aspect=asp,
        depth=zbar,
        curve_par_a=alpha,
        curve_par_n=n,
        deep_depth=zbar * 0.875 + 1.973 / np.sqrt(2),
        layer_bottoms=(
            np.array([0.025, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1]) * zbar
        ).tolist(),
    )
    dump(data / "sites.json", site_details)
    dump(data / "equivalent_environment.json", equivalent)
    pd.DataFrame(
        {
            "psi_MPa": psi,
            "target_storage_mm": 1000 * zbar * target,
            "equivalent_storage_mm": 1000 * zbar * theta(psi, alpha, n),
        }
    ).to_csv(data / "equivalent_storage.csv", index=False)
    # Identical-size trees share one cohort: this is lossless for every model allometry.
    trees = pd.read_csv(census_path)
    alive = trees[
        (trees.status == "A") & (trees.dbh >= 10) & trees.gx.notna() & trees.gy.notna()
    ].copy()
    assert (
        alive.gx.between(0, 1000, inclusive="left").all()
        and alive.gy.between(0, 500, inclusive="left").all()
    )
    assert not alive.treeID.duplicated().any()
    wd = pd.read_csv(wd_path).set_index("sp").rho
    taxonomy = pd.read_csv(raw / "species_2019.csv").set_index("sp")
    for code in set(alive.sp) - set(wd.index):
        wd.loc[code] = taxonomy.at[code, "wsg"]
    alive["rho"] = alive.sp.map(wd)
    assert alive.rho.notna().all()
    alive["pft"] = np.digitize(alive.rho, [0.42, 0.58]) + 1
    alive["patch_id"] = (alive.gx // 20 * 25 + alive.gy // 20 + 1).astype(int)
    alive = alive.merge(
        q[["patch_id", "site_id", "unit"]], on="patch_id", validate="many_to_one"
    )
    alive["dbh_cm"] = alive.dbh / 10
    alive["ba_m2"] = np.pi * (alive.dbh_cm / 200) ** 2
    # Allometric model biomass is distinct from census species-level biomass.
    h = np.exp(
        0.8898 + 0.7908 * np.log(alive.dbh_cm) - 0.04923 * np.log(alive.dbh_cm) ** 2
    )
    alive["model_agb_kgC"] = (
        0.03365
        * (np.array([0.36, 0.50, 0.68])[alive.pft - 1] * alive.dbh_cm**2 * h) ** 0.976
    )
    cohort = (
        alive.groupby(["site_id", "patch_id", "pft", "dbh_cm"], sort=True)
        .size()
        .rename("count")
        .reset_index()
        .rename(columns={"dbh_cm": "dbh"})
    )
    cohort["nplant"] = cohort["count"] / 400.0
    cohort["patch_area"] = 400.0
    columns = ["site_id", "patch_id", "dbh", "pft", "nplant", "patch_area"]
    cohort[columns].to_csv(
        data / "census_multisite.csv", index=False, float_format="%.12g"
    )
    single = cohort.copy()
    single.site_id = 1
    single[columns].to_csv(
        data / "census_single_site.csv", index=False, float_format="%.12g"
    )
    alive[["treeID", "sp", "patch_id", "site_id", "pft", "dbh_cm", "rho"]].to_csv(
        data / "tree_assignment.csv", index=False
    )
    stand = (
        alive.groupby(["site_id", "unit", "pft"])
        .agg(
            n_trees=("treeID", "size"),
            basal_area_m2=("ba_m2", "sum"),
            model_agb_kgC=("model_agb_kgC", "sum"),
        )
        .reset_index()
    )
    stand.to_csv(data / "initial_stand_by_site_pft.csv", index=False)
    areas = q.groupby("site_id").size() / 1250
    assert np.isclose(sum(areas), 1) and cohort.patch_id.nunique() == 1250
    assert cohort["count"].sum() == len(alive)
    audit = dict(
        n_trees=len(alive),
        n_exact_size_cohorts=len(cohort),
        n_quadrats=1250,
        area_ha=50.0,
        n_sites=len(sites),
        n_species=int(alive.sp.nunique()),
        basal_area_m2_ha=float(alive.ba_m2.sum() / 50),
        model_agb_kgC_m2=float(alive.model_agb_kgC.sum() / 500000),
        nplant_m2=len(alive) / 500000,
        missing_density_proxy_trees=int((alive.sp == "sipacr").sum()),
        equivalent_depth=zbar,
        equivalent_storage_rmse_mm=float(
            np.sqrt(np.mean((target - theta(psi, alpha, n)) ** 2)) * zbar * 1000
        ),
        initial_soil_water_mm=0.42 * zbar * 1000,
        area_weights=areas.to_dict(),
        all_trees_assigned_once=True,
        identical_census_A_B_C_before_model_restructuring=True,
    )
    dump(data / "preparation_audit.json", audit)
    template = load_toml(HERE / "ed_config.toml")
    # The checked-in PFT and output selections are the inherited baseline.
    for name in [
        "A_heterogeneous",
        "B_uniform_multisite",
        "C_uniform_single",
        "S_wetland_aquifer",
        "S_no_cue",
        "S_single_patch_budget",
        "S_equal_depth",
    ]:
        c = copy.deepcopy(template)
        c["run"].update(
            start_time="2011-01-01", end_time="2018-01-01", n_threads=8, slow_on=True
        )
        c["fast"]["dt_fast"] = "300s"
        c["init"].update(
            init_mode=1,
            pft_config="pft_parameters_no_cue.toml"
            if name == "S_no_cue"
            else "pft_parameters.toml",
            census_file="data/census_single_site.csv"
            if name in ["C_uniform_single", "S_single_patch_budget"]
            else "data/census_multisite.csv",
        )
        c["site"].update(
            elevation=equivalent["elevation"],
            apply_elevation_lapse=True,
            lapse_rate_tair=0.0065,
            grid_elevation=72.97434998,
        )
        c["forcing"].update(
            path="data/raw/bci_era5land_2003-2022.nc",
            co2_file="../../data/co2/co2_cmip7_global_annual_1000-2022.txt",
            recycle=False,
        )
        c["forcing"].pop("recycle_start", None)
        c["forcing"].pop("recycle_end", None)
        c["soil_carbon"].update(
            decomp_scheme="ed2",
            step_solver="euler",
            spinup_steady=True,
            spinup_labile_grnd=3.3080e-4,
            spinup_labile_soil=8.0198e-4,
            spinup_struct_grnd=9.2093e-4,
            spinup_struct_soil=6.7763e-4,
        )
        c["soil"]["water_bottom_bc"] = "free_drain"
        c["sites"] = copy.deepcopy(sites)
        if name == "B_uniform_multisite":
            c["sites"] = [
                dict(
                    equivalent,
                    area_fraction=s["area_fraction"],
                    census_site_id=s["census_site_id"],
                )
                for s in sites
            ]
        elif name in ["C_uniform_single", "S_single_patch_budget"]:
            c["sites"] = [equivalent.copy()]
        elif name == "S_wetland_aquifer":
            c["sites"][-1]["water_bottom_bc"] = "aquifer"
        elif name == "S_equal_depth":
            for site in c["sites"]:
                for key in ["depth", "deep_depth", "layer_bottoms"]:
                    site[key] = copy.deepcopy(equivalent[key])
        if name == "S_single_patch_budget":
            c["demography"]["max_patch"] = 200
        out = "output/" + name
        c["output"].update(
            state_interval="1 years",
            state_file_dir=out,
            state_file_prefix=name,
            dir=out,
            prefix=name,
            overwrite=False,
            io_config="io_config.toml",
            cohort_max=32768,
            patch_max=1024,
        )
        c["output"]["daily"].update(enabled=True, file_chunk="year")
        c["output"]["monthly"]["file_chunk"] = "all"
        write_toml(configs / (name + ".toml"), c)
    print(json.dumps(audit, indent=2))
    print(
        pd.DataFrame(site_details)[
            ["name", "n_quadrats", "area_ha", "elevation", "slope", "aspect", "depth"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
