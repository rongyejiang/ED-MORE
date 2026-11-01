#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare the unused 2015 census round and field-data metadata for external diagnostics."""

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    raw = HERE / "data/raw"
    wd = (
        pd.read_csv(ROOT / "examples/example03_demography/bci_wood_density.csv")
        .set_index("sp")
        .rho
    )
    taxonomy = pd.read_csv(raw / "species_2019.csv").set_index("sp")
    q = pd.read_csv(HERE / "data/quadrat_assignment.csv")
    provenance = []
    summaries = []
    all_stand = []
    for year in (2010, 2015):
        path = raw / f"bci_{year}.csv"
        d = pd.read_csv(path)
        a = d[(d.status == "A") & (d.dbh >= 10) & d.gx.notna() & d.gy.notna()].copy()
        missing = set(a.sp) - set(wd.index)
        for code in missing:
            assert pd.notna(taxonomy.at[code, "wsg"])
            wd.loc[code] = taxonomy.at[code, "wsg"]
            provenance.append(
                dict(
                    year=year,
                    code=code,
                    wood_density=float(wd[code]),
                    level=taxonomy.at[code, "wsglevel"],
                    n=int((a.sp == code).sum()),
                )
            )
        a["pft"] = np.digitize(a.sp.map(wd), [0.42, 0.58]) + 1
        a["patch_id"] = (a.gx // 20 * 25 + a.gy // 20 + 1).astype(int)
        a = a.merge(q[["patch_id", "site_id"]], on="patch_id", validate="many_to_one")
        a["dbh_cm"] = a.dbh / 10
        h = np.exp(0.8898 + 0.7908 * np.log(a.dbh_cm) - 0.04923 * np.log(a.dbh_cm) ** 2)
        a["ba_m2"] = np.pi * (a.dbh_cm / 200) ** 2
        a["model_agb_kgC"] = (
            0.03365
            * (np.array([0.36, 0.50, 0.68])[a.pft - 1] * a.dbh_cm**2 * h) ** 0.976
        )
        dt = pd.to_datetime(a.ExactDate, errors="coerce")
        summaries.append(
            dict(
                year=year,
                n_trees=len(a),
                status_counts=d.status.value_counts().to_dict(),
                alive_without_dbh=int(((d.status == "A") & d.dbh.isna()).sum()),
                alternative_alive_with_dbh=int(
                    (d.status.isin(["AD", "AR"]) & d.dbh.notna()).sum()
                ),
                multistem_trees=int((a.nostems > 1).sum()),
                dbh_threshold_cm=1,
                date_min=str(dt.min().date()),
                date_median=str(dt.median().date()),
                date_max=str(dt.max().date()),
                records_after_model_start=int((dt > "2011-01-01").sum())
                if year == 2010
                else None,
                ba_m2_ha=float(a.ba_m2.sum() / 50),
                original_all_stem_ba_m2_ha=float(a.ba.sum() / 50),
                original_all_stem_agb_Mg_ha=float(a.agb.sum() / 50),
                agb_model_kgC_m2=float(a.model_agb_kgC.sum() / 500000),
            )
        )
        s = (
            a.groupby(["site_id", "pft"])
            .agg(
                n_trees=("treeID", "size"),
                basal_area_m2=("ba_m2", "sum"),
                model_agb_kgC=("model_agb_kgC", "sum"),
                original_all_stem_ba_m2=("ba", "sum"),
                original_all_stem_agb_Mg=("agb", "sum"),
            )
            .reset_index()
        )
        s["census_year"] = year
        all_stand.append(s)
    pd.concat(all_stand).to_csv(
        HERE / "data/census_validation_by_site_pft.csv", index=False
    )
    (HERE / "data/census_round_metadata.json").write_text(
        json.dumps(
            dict(rounds=summaries, density_lookup_additions=provenance), indent=2
        )
    )
    names = [
        "bci.tree8.rdata",
        "bci_2015.csv",
        "species_2019.csv",
    ]
    if (raw / "bci.tree7.rdata").exists():
        names.append("bci.tree7.rdata")
    (HERE / "data/validation_source_manifest.json").write_text(
        json.dumps(
            [
                dict(
                    file="data/raw/" + n,
                    sha256=hashlib.sha256((raw / n).read_bytes()).hexdigest(),
                    bytes=(raw / n).stat().st_size,
                )
                for n in names
            ],
            indent=2,
        )
    )
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
