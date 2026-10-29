# SPDX-License-Identifier: Apache-2.0
"""Extract the BCI point from retained, hash-checked ARCO Zarr chunks; no download."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import zarr


def extract(cache, output):
    records = json.loads((Path(__file__).parent / "arco_sources.json").read_text())
    # Verify all source bytes before opening a sparse cache, where absent chunks
    # would otherwise be represented by fill values.
    for record in records:
        for item in record["requests"]:
            path = cache / item["path"]
            if path.stat().st_size != item["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError(f"Source bytes differ: {item['path']}")
    output.mkdir(parents=True)
    for record in records:
        group = zarr.open_consolidated(str(cache / "arco_raw" / record["group"]), mode="r")
        lat, lon = group["latitude"][:], group["longitude"][:]
        i = int(np.argmin(abs(lat - 9.1568)))
        j = int(np.argmin(abs(((lon + 79.8486 + 180) % 360) - 180)))
        if not np.allclose([lat[i], lon[j]], [9.2, -79.8], rtol=0, atol=1e-8):
            raise ValueError("Unexpected nearest grid cell")
        time = group["time"][:].astype("datetime64[h]")
        first = int(np.searchsorted(time, np.datetime64("2003-01-01T01")))
        last = int(np.searchsorted(time, np.datetime64("2023-01-01T00"), side="right"))
        stamps = time[first:last]
        expected = np.arange(np.datetime64("2003-01-01T01", "h"), np.datetime64("2023-01-01T01", "h"))
        if not np.array_equal(stamps, expected):
            raise ValueError("ARCO time axis mismatch")
        values = {name: group[name][first:last, i, j] for name in record["variables"]}
        if not all(np.isfinite(value).all() for value in values.values()):
            raise ValueError("Non-finite source values")
        folder = output / record["group"]
        folder.mkdir()
        np.savez_compressed(folder / "point_2003_2022.npz", time=stamps, **values)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory")
    args = parser.parse_args()
    extract(args.cache, args.output)
