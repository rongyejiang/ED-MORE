# SPDX-License-Identifier: Apache-2.0
"""Compare a completed annual output with the pinned Example 05 README table."""
import argparse
import importlib.util
from pathlib import Path
import re

import numpy as np

from arco_adapter import native_modules


def compare(source, annual):
    native_modules(source)
    example = source / "examples/example05_forest_regeneration"
    spec = importlib.util.spec_from_file_location("native_regeneration_plot", example / "plot_regeneration.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = module.read(annual)
    years = np.asarray(data["year"]).astype(int)
    keys = ["agb_total", "agb_early", "agb_mid", "agb_late", "basal_area", "lai", "stems10", "gpp", "npp"]
    table = (example / "README.md").read_text().split("### Results", 1)[1].split("Yearly values.", 1)[0]
    rows = []
    for line in table.splitlines():
        if not re.match(r"^\|\s*\d{4}\s*\|", line):
            continue
        cells = [item.strip() for item in line.strip("|").split("|")]
        refs = [cells[1], *cells[2].split(" / "), cells[3], cells[4], cells[5], *cells[6].split(" / ")]
        year = int(cells[0])
        positions = np.flatnonzero(years == year)
        if len(positions) != 1 or len(refs) != len(keys):
            raise ValueError("Missing year or unexpected reference table")
        i = int(positions[0])
        for key, reference in zip(keys, refs):
            if key == "agb_total":
                value = float(data["agb"][i].sum())
            elif key.startswith("agb_"):
                value = float(data["agb"][i][["agb_early", "agb_mid", "agb_late"].index(key)])
            elif key == "basal_area":
                value = float(data["ba"][i].sum())
            elif key == "lai":
                value = float(data["lai"][i].sum())
            else:
                value = float(data[key][i])
            digits = len(reference.split(".")[1]) if "." in reference else 0
            match = float(f"{value:.{digits}f}") == float(reference)
            rows.append((year, key, reference, value, value - float(reference), match))
    if len(rows) != 63:
        raise ValueError("Expected the seven-year, nine-metric reference table")
    return rows


def render(rows):
    lines = ["| Year | Metric | README | Local | Local - README | Matches displayed precision |",
             "|---|---|---:|---:|---:|:---:|"]
    lines += [f"| {y} | {key} | {ref} | {v:.12g} | {delta:.12g} | {'yes' if ok else 'no'} |"
              for y, key, ref, v, delta, ok in rows]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--annual", type=Path, required=True)
    args = parser.parse_args()
    print(render(compare(args.source.resolve(), args.annual.resolve())))
