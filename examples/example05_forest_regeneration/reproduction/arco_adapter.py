# SPDX-License-Identifier: Apache-2.0
"""Prepare a BCI ARCO point archive with the pinned ED-MORE writers.

Inputs are already de-accumulated hourly amounts, never forecast accumulations.
No downloads or model runs are performed. Output must be a new directory.
"""
import argparse
import datetime as dt
import hashlib
import importlib
import json
from pathlib import Path
import sys

import numpy as np

PINNED = "f49d50c89f01e5747eee2950a9cbe1d8e08371a5"
HERE = Path(__file__).resolve().parent


def native_modules(source):
    """Check the helper bytes, rather than trusting a checkout's label."""
    folder = source / "scripts/prepare_input/era5"
    manifest = json.loads((HERE / "provenance.json").read_text())
    for relative, expected in manifest["native_script_sha256"].items():
        path = source / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Native helper does not match {PINNED}: {relative}")
    sys.path.insert(0, str(folder))
    return tuple(importlib.import_module(name) for name in
                 ("era5land_common", "build_era5land_archive", "build_era5land_static"))


def read_points(raw_root, variable_names):
    """Require the complete common UTC end-stamp axis and all eight series."""
    expected = np.arange(np.datetime64("2003-01-01T01", "h"),
                         np.datetime64("2023-01-01T01", "h"))
    series = {}
    files = sorted(raw_root.glob("*/point_2003_2022.npz"))
    if not files:
        raise ValueError("No point_2003_2022.npz inputs found")
    for path in files:
        with np.load(path, allow_pickle=False) as data:
            if not np.array_equal(data["time"], expected):
                raise ValueError(f"Missing, shifted or duplicated hours in {path.name}")
            for name in variable_names:
                if name not in data:
                    continue
                if name in series:
                    raise ValueError(f"Duplicate input variable: {name}")
                values = data[name].astype("f4")
                if values.shape != expected.shape or not np.isfinite(values).all():
                    raise ValueError(f"Invalid point series: {name}")
                series[name] = values
    if set(series) != set(variable_names):
        raise ValueError("The eight input variables are required")
    return expected, series


def convert_hourly(values, spec):
    """Use native float32 factors and clipping, without another difference."""
    result = np.asarray(values, dtype="f4").copy()
    if spec["kind"] == "accum":
        if spec["clip_negative"]:
            np.maximum(result, 0, out=result)
        result *= np.float32(spec["factor"])
    return result


def build_archive(source, raw_root, output):
    common, builder, static_builder = native_modules(source)
    dates, series = read_points(raw_root, common.VARIABLES)
    # mkdir without exist_ok refuses even a partly populated previous run.
    output.mkdir(parents=True)
    cell = json.loads((HERE / "provenance.json").read_text())["selected_cell"]
    static_builder.write_static(
        str(output / "ED_ERA5land_static.nc"), np.array([cell["cell"][0]]),
        np.array([cell["cell"][1]]), np.ones((1, 1), dtype="i1"),
        np.array([[cell["geopotential_m2_s2"] / 9.80665]], dtype="f4"),
        np.array([[cell["land_fraction"]]], dtype="f4"),
        "finite BCI t2m probe and complete hourly series; see provenance.json",
    )
    static = builder.load_static(str(output))
    old_chunk = builder.CHUNK
    builder.CHUNK = 1
    try:
        for year in range(2003, 2023):
            for month in range(1, 13):
                first, last = common.month_interval(year, month)
                stamps = [first + dt.timedelta(hours=i)
                          for i in range(common.stamps_between(first, last))]
                indices = np.searchsorted(dates, np.array(stamps, dtype="datetime64[s]"))
                if not np.array_equal(dates[indices], np.array(stamps, dtype="datetime64[s]")):
                    raise ValueError("Monthly time axis mismatch")
                for name, spec in common.ARCHIVE_VARIABLES.items():
                    values = convert_hourly(series[spec["raw"]][indices, None, None], spec)
                    builder.check_band(values, static[2], spec["bounds"], 0, 1, static[0], static[1])
                    final = common.archive_file(str(output), name, year, month)
                    part = final + ".part"
                    dataset, variable = builder.create_output(part, name, spec, static, stamps)
                    try:
                        variable[:] = values
                        builder.finish_output(
                            dataset, name, year, month,
                            "ECMWF ERA5-Land ARCO hourly point; already de-accumulated",
                            "ARCO point inputs; public provenance.json", [],
                        )
                    finally:
                        if dataset.isopen():
                            dataset.close()
                    builder.publish(part, final)
    finally:
        builder.CHUNK = old_chunk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Pinned ED-MORE checkout")
    parser.add_argument("--raw-root", type=Path, required=True, help="Folder with four point NPZ subfolders")
    parser.add_argument("--output", type=Path, required=True, help="New one-cell archive directory")
    args = parser.parse_args()
    build_archive(args.source.resolve(), args.raw_root.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
