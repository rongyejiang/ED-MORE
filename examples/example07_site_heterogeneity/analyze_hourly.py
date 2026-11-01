#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Extract the common-restart hourly process windows at both outer step lengths."""

from pathlib import Path
import argparse
import hashlib
import json
import tomllib
import netCDF4 as nc
import numpy as np
import pandas as pd
from analyze_results import values

HERE = Path(__file__).resolve().parent


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract(output_root):
    frames, provenance, restart_hashes = [], [], []
    for dt in (300, 150):
        folder = output_root / f"A_heterogeneous_window_dt{dt}"
        assert (folder / "completed.json").exists(), (
            f"Incomplete hourly run: {folder.name}"
        )
        config = tomllib.loads((folder / "run.toml").read_text())
        restart = Path(config["init"]["restart_file"])
        if not restart.is_absolute():
            restart = folder / restart
        restart_hashes.append(digest(restart))
        assert config["fast"]["dt_fast"] == f"{dt}s"
        files = sorted(folder.glob("*-F.nc"))
        assert len(files) == 1, f"Expected one hourly file: {folder.name}"
        path = files[0]
        with nc.Dataset(path) as dataset:
            time = dataset["time"]
            dates = pd.to_datetime(
                [
                    v.strftime("%Y-%m-%d %H:%M:%S")
                    for v in nc.num2date(time[:], time.units, time.calendar)
                ]
            )
            seconds = np.diff(values(dataset["time_bnds"]), axis=1)[:, 0] * 86400
            assert np.allclose(seconds, 3600, atol=1e-5, rtol=0)
            frame = pd.DataFrame(
                {
                    "date": dates,
                    "dt_seconds": dt,
                    "gpp_umol": values(dataset["mean_gpp_py"])[:, 0],
                    "et_mm_hour": values(dataset["mean_et_py"])[:, 0] * 3600,
                    "precip_mm_hour": values(dataset["mean_precip_py"])[:, 0] * 3600,
                    "sw_W_m2": values(dataset["mean_sw_in_py"])[:, 0],
                }
            )
            for sid, n in enumerate(values(dataset["n_soil_si"])[0].astype(int)):
                depth = -values(dataset["soil_z"])[0, sid, :n]
                assert np.all(np.diff(depth) > 0) and depth[0] <= 0.15 <= depth[-1]
                for key, prefix in [
                    ("mean_soil_psi_layer_si", "psi"),
                    ("mean_soil_temp_layer_si", "temp"),
                ]:
                    field = values(dataset[key])[:, 0, sid, :n]
                    frame[f"{prefix}_15cm_site{sid + 1}"] = [
                        np.interp(0.15, depth, row) for row in field
                    ]
        expected = pd.date_range(
            config["run"]["start_time"],
            config["run"]["end_time"],
            freq="h",
            inclusive="left",
        )
        assert np.array_equal(frame.date.to_numpy(), expected.to_numpy()), (
            "Incomplete hourly intervals"
        )
        assert np.isfinite(frame.select_dtypes("number")).all().all()
        frames.append(frame)
        provenance.append(
            {
                "run": folder.name,
                "file": path.name,
                "sha256": digest(path),
                "restart_sha256": restart_hashes[-1],
                "hourly_intervals": len(frame),
            }
        )
    assert restart_hashes[0] == restart_hashes[1], (
        "The windows must share the same restart state"
    )
    assert np.array_equal(frames[0].date.to_numpy(), frames[1].date.to_numpy())
    target = HERE / "results"
    target.mkdir(exist_ok=True)
    pd.concat(frames).to_csv(target / "hourly_window.csv", index=False)
    (target / "hourly_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )
    print(
        f"Extracted {len(frames)} common-restart windows with {len(frames[0])} hourly intervals each."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=HERE / "output")
    extract(parser.parse_args().output_root)
