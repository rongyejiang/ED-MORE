#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fetch or verify public inputs, export native R tables, and prepare ERA5-Land forcing."""

from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--copy-from", type=Path, help="folder containing the published downloads"
    )
    parser.add_argument(
        "--rscript", default="Rscript", help="native R executable for census export"
    )
    parser.add_argument(
        "--forcing", type=Path, help="existing Example 05 BCI forcing file"
    )
    parser.add_argument("--era5-archive", default=os.environ.get("ERA5LAND_ARCHIVE"))
    args = parser.parse_args()
    raw = HERE / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    sources = json.loads((HERE / "sources.json").read_text())
    for item in sources:
        target = raw / item["file"]
        if not target.exists():
            local = args.copy_from / item["file"] if args.copy_from else None
            if local is not None and local.exists():
                shutil.copyfile(local, target)
            elif item["automatic_download"]:
                try:
                    with urllib.request.urlopen(item["url"], timeout=60) as response:
                        content = response.read()
                    if hashlib.sha256(content).hexdigest() != item["sha256"]:
                        raise ValueError(
                            "download checksum differs from the published input"
                        )
                    target.write_bytes(content)
                except (OSError, ValueError) as error:
                    raise SystemExit(
                        f"Cannot fetch {item['file']}: {error}. Download it from {item['url']} "
                        "and pass its folder with --copy-from."
                    ) from error
            else:
                raise SystemExit(
                    f"Download {item['file']} from {item['url']}; use --copy-from."
                )
        if digest(target) != item["sha256"]:
            raise SystemExit(f"Checksum mismatch: {target}. Existing file retained.")
        print(f"Verified {item['file']}", flush=True)

    with zipfile.ZipFile(raw / "bci.tree.zip") as archive:
        for round_number in (7, 8):
            name = f"bci.tree{round_number}.rdata"
            (raw / name).write_bytes(archive.read(name))
    # R preserves this archive's factor levels and missing values during export.
    script = raw / "export.R"
    script.write_text("""args <- commandArgs(trailingOnly=TRUE)
setwd(args[1])
for (i in c(7,8)) {
  e <- new.env()
  name <- paste0("bci.tree",i)
  load(paste0(name,".rdata"), envir=e)
  write.csv(e[[name]], paste0("bci_",ifelse(i==7,2010,2015),".csv"),
            row.names=FALSE, na="")
}
e <- new.env()
load("bci.spptable.rdata", envir=e)
write.csv(e[["bci.spptable"]], "species_2019.csv", row.names=FALSE, na="")
""")
    subprocess.run([args.rscript, "--vanilla", str(script), str(raw)], check=True)
    forcing = raw / "bci_era5land_2003-2022.nc"
    if not forcing.exists():
        if args.forcing:
            shutil.copyfile(args.forcing, forcing)
        elif args.era5_archive:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/prepare_input/era5/make_forcing_file.py"),
                    "--data-path",
                    args.era5_archive,
                    "--start",
                    "2003-01-01",
                    "--end",
                    "2022-12-31",
                    "--lat",
                    "9.1568",
                    "--lon",
                    "-79.8486",
                    "--out",
                    str(forcing),
                ],
                check=True,
            )
        else:
            raise SystemExit("Supply --forcing from Example 05 or --era5-archive.")
    # Validate the grid elevation used by the lapse correction, not just the filename.
    import netCDF4
    import numpy as np

    with netCDF4.Dataset(forcing) as dataset:
        if not np.allclose(dataset["elevation"][:], 72.97434998, atol=1e-6, rtol=0):
            raise ValueError(
                "The forcing does not use the documented BCI grid elevation."
            )
    derived = [
        forcing,
        raw / "bci_2010.csv",
        raw / "bci_2015.csv",
        raw / "species_2019.csv",
    ]
    (HERE / "data/source_manifest.json").write_text(
        json.dumps(
            {
                "public_inputs": sources,
                "prepared_files": [
                    {"file": p.name, "sha256": digest(p)} for p in derived
                ],
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
