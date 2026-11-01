#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent checks of spatial coverage, census conservation and controlled contrasts."""

from pathlib import Path
import json, sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "python"))
from edmore.config import load_toml


def main():
    q = pd.read_csv(HERE / "data/quadrat_assignment.csv")
    trees = pd.read_csv(HERE / "data/tree_assignment.csv")
    a = pd.read_csv(HERE / "data/census_multisite.csv")
    c = pd.read_csv(HERE / "data/census_single_site.csv")
    checks = []

    def check(name, condition):
        checks.append(dict(check=name, passed=bool(condition)))
        assert condition, name

    check(
        "all 1250 distinct 20-m quadrats, no overlap or omitted boundary",
        set(zip(q.x, q.y))
        == set((x, y) for x in range(0, 1000, 20) for y in range(0, 500, 20)),
    )
    check(
        "all 207254 census trees uniquely assigned",
        len(trees) == 207254 and trees.treeID.nunique() == 207254,
    )
    check(
        "global patch identities identical in multisite and single-site inputs",
        a.drop(columns="site_id").equals(c.drop(columns="site_id")),
    )
    check(
        "every exact diameter/PFT/patch multiplicity is preserved",
        np.allclose(
            trees.groupby(["site_id", "patch_id", "pft", "dbh_cm"]).size().to_numpy(),
            a.set_index(["site_id", "patch_id", "pft", "dbh"])
            .sort_index()
            .nplant.to_numpy()
            * 400,
            rtol=0,
            atol=1e-10,
        ),
    )
    area = q.groupby("site_id").size() / 1250
    patch_counts = q.groupby("site_id").size()
    check(
        "nested site x patch areas recover each quadrat global weight",
        np.allclose(area / patch_counts, 1 / 1250, rtol=0, atol=1e-15),
    )
    check(
        "whole-plot stem density preserved",
        np.isclose(a.nplant.sum() / 1250, len(trees) / 500000, rtol=0, atol=1e-14),
    )
    cfg = {
        s: load_toml(HERE / "configs" / (s + ".toml"))
        for s in [
            "A_heterogeneous",
            "B_uniform_multisite",
            "C_uniform_single",
            "S_wetland_aquifer",
            "S_no_cue",
            "S_single_patch_budget",
            "S_equal_depth",
        ]
    }
    eq = cfg["C_uniform_single"]["sites"][0]
    envkeys = set(eq) - {"area_fraction", "census_site_id"}
    check(
        "B and C environmental values are identical",
        all(
            all(s[k] == eq[k] for k in envkeys)
            for s in cfg["B_uniform_multisite"]["sites"]
        ),
    )
    for key in [
        "run",
        "fast",
        "trait_dynamics",
        "demography",
        "leaf_physiology",
        "forcing",
        "soil_carbon",
    ]:
        check(
            key + " unchanged across A, B, C",
            cfg["A_heterogeneous"][key]
            == cfg["B_uniform_multisite"][key]
            == cfg["C_uniform_single"][key],
        )
    check(
        "A and B identical site areas and census assignment",
        all(
            a["area_fraction"] == b["area_fraction"]
            and a["census_site_id"] == b["census_site_id"]
            for a, b in zip(
                cfg["A_heterogeneous"]["sites"], cfg["B_uniform_multisite"]["sites"]
            )
        ),
    )
    za = sum(s["area_fraction"] * s["depth"] for s in cfg["A_heterogeneous"]["sites"])
    check(
        "equivalent soil preserves depth-integrated initial and saturated water capacity",
        abs(za - eq["depth"]) < 1e-12,
    )
    check(
        "main contrasts have the same free-drainage boundary",
        all(
            s["water_bottom_bc"] == "free_drain"
            for name in ["A_heterogeneous", "B_uniform_multisite", "C_uniform_single"]
            for s in cfg[name]["sites"]
        ),
    )
    w = cfg["S_wetland_aquifer"]
    base = cfg["A_heterogeneous"]
    check(
        "aquifer sensitivity changes only swamp boundary among site properties",
        w["sites"][:-1] == base["sites"][:-1]
        and dict(w["sites"][-1], water_bottom_bc="free_drain") == base["sites"][-1],
    )
    p = load_toml(HERE / "pft_parameters.toml")
    equal_depth = cfg["S_equal_depth"]
    depth_keys = {"depth", "deep_depth", "layer_bottoms"}
    check(
        "equal-depth diagnostic redistributes only profile geometry and preserves total soil volume",
        all(
            {k: v for k, v in s.items() if k not in depth_keys}
            == {k: v for k, v in a.items() if k not in depth_keys}
            and all(s[k] == eq[k] for k in depth_keys)
            for s, a in zip(equal_depth["sites"], base["sites"])
        )
        and {k: v for k, v in equal_depth.items() if k not in {"sites", "output"}}
        == {k: v for k, v in base.items() if k not in {"sites", "output"}}
        and abs(sum(s["area_fraction"] * s["depth"] for s in equal_depth["sites"]) - za)
        < 1e-12,
    )
    no_cue = load_toml(HERE / "pft_parameters_no_cue.toml")
    check(
        "no-cue sensitivity preserves every non-phenology PFT parameter",
        {k: v for k, v in p.items() if k != "phenology"} == no_cue,
    )
    budget = cfg["S_single_patch_budget"]
    single = cfg["C_uniform_single"]
    check(
        "patch-budget sensitivity changes only max_patch in demography and preserves the single-site input",
        dict(budget["demography"], max_patch=single["demography"]["max_patch"])
        == single["demography"]
        and budget["sites"] == single["sites"]
        and budget["init"] == single["init"]
        and budget["demography"]["max_patch"] == 200,
    )
    check(
        "all three PFTs have the intended light/water phenology cues",
        p["phenology"]["flush_cue_mask"] == [4] * 3
        and p["phenology"]["shed_cue_mask"] == [6] * 3,
    )
    check(
        "fast, slow, canopy interception, soil carbon, plasticity and demography enabled",
        base["run"]["slow_on"]
        and base["fast"]["fast_biophysics_on"]
        and base["fast"]["canopy_water_on"]
        and base["soil_carbon"]["soil_carbon_on"]
        and base["trait_dynamics"]["trait_plasticity_on"]
        and all(
            base["demography"][k]
            for k in [
                "demography_on",
                "recruitment_on",
                "patch_disturbance_on",
                "cohort_fusion_on",
                "patch_fusion_on",
                "cohort_fission_on",
            ]
        ),
    )
    (HERE / "results/design_checks.json").write_text(json.dumps(checks, indent=2))
    print(str(len(checks)) + " scientific design checks passed")


if __name__ == "__main__":
    main()
