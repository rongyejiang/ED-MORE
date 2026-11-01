#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run one BCI design and save monthly cohort states with their patch weights."""

from pathlib import Path
import argparse, datetime, hashlib, json, os, subprocess, sys, time

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
sys.path.insert(0, str(MODEL / "python"))
from edmore.config import load_toml, write_toml


def worker(path):
    import resource

    resource.setrlimit(
        resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
    )
    import numpy as np
    import pandas as pd
    from edmore.model import Run, COMPLETED

    config = load_toml(path)
    os.chdir(HERE)
    out = Path(config["output"]["dir"])
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    history = []

    def snapshot(run, label):
        cohort = pd.DataFrame(
            run.cohorts(
                "dbh",
                "height",
                "pft",
                "nplant",
                "agb",
                "leaf_area",
                "owner_patch",
                "global_id",
                "growth_avg",
                "leaf_carbon",
                "wood_carbon",
                "storage_carbon",
            )
        )
        patch = pd.DataFrame(run.patches())
        patch.index = np.arange(1, len(patch) + 1)
        patch.index.name = "owner_patch"
        cohort = cohort.join(patch, on="owner_patch")
        assert np.isfinite(cohort.select_dtypes("number")).all().all()
        assert np.isclose(patch.share.sum(), 1.0, atol=1e-10)
        cohort.to_csv(out / ("stand_" + label + ".csv.gz"), index=False)
        item = dict(
            date=str(run.date),
            elapsed_seconds=time.time() - started,
            n_sites=run.n_site,
            n_patches=run.n_patch,
            n_cohorts=run.n_cohort,
            agb_kgC_m2=run.total_agb,
            lai=run.total_lai,
            nplant_m2=run.total_nplant,
            basal_area_m2_ha=run.total_basal_area * 10000,
            soil_carbon_kgC_m2=run.soil_carbon,
        )
        history.append(item)
        (out / "progress.json").write_text(json.dumps(history, indent=2))
        print("PROGRESS " + json.dumps(item), flush=True)

    with Run(path) as run:
        snapshot(run, "initial")
        for step in run:
            if step.is_new_month:
                snapshot(run, str(step.date))
        run.finalize()
        snapshot(run, "final")
    (out / "completed.json").write_text(
        json.dumps(
            dict(
                config=str(path),
                finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                elapsed_seconds=time.time() - started,
                final=history[-1],
            ),
            indent=2,
        )
    )
    print(COMPLETED, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--scenario",
        default="A_heterogeneous",
        choices=[
            "A_heterogeneous",
            "B_uniform_multisite",
            "C_uniform_single",
            "S_wetland_aquifer",
            "S_no_cue",
            "S_single_patch_budget",
            "S_equal_depth",
        ],
    )
    ap.add_argument(
        "--library",
        type=Path,
        default=Path(os.environ.get("EDMORE_LIB", MODEL / "build-dev/libedmore.so")),
    )
    ap.add_argument("--days", type=int)
    ap.add_argument("--dt", type=int, default=300)
    ap.add_argument("--suffix", default="")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--restart", type=Path)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument(
        "--io-config",
        type=Path,
        help="optional output selection for an hourly process window",
    )
    ap.add_argument("--worker", type=Path)
    args = ap.parse_args()
    if args.worker:
        worker(args.worker)
        return
    tag = args.scenario + ("_" + args.suffix if args.suffix else "")
    out = HERE / "output" / tag
    if (out / "completed.json").exists():
        print(tag + " already completed; retained")
        return
    if out.exists() and any(out.glob("*.nc")):
        raise SystemExit(
            "Existing incomplete output is retained. Use a fresh --suffix or an explicit restart."
        )
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_toml(HERE / "configs" / (args.scenario + ".toml"))
    if args.start:
        cfg["run"]["start_time"] = args.start
    if args.end:
        cfg["run"]["end_time"] = args.end
    if args.days:
        cfg["run"]["end_time"] = str(
            datetime.date.fromisoformat(cfg["run"]["start_time"])
            + datetime.timedelta(days=args.days)
        )
    if args.restart:
        cfg["init"].update(init_mode=2, restart_file=str(args.restart.resolve()))
    cfg["run"]["n_threads"] = args.threads
    cfg["fast"]["dt_fast"] = str(args.dt) + "s"
    if args.io_config:
        cfg["output"]["io_config"] = str(args.io_config.resolve())
        cfg["output"]["fast"].update(enabled=True, file_chunk="all")
        cfg["output"]["fast_interval_steps"] = 3600 // args.dt
    cfg["output"].update(
        dir=str(out), state_file_dir=str(out), prefix=tag, state_file_prefix=tag
    )
    config = out / "run.toml"
    write_toml(config, cfg)
    env = os.environ.copy()
    env.update(
        EDMORE_LIB=str(args.library.resolve()),
        OMP_NUM_THREADS=str(args.threads),
        OPENBLAS_NUM_THREADS="1",
        KMP_STACKSIZE="64M",
        OMP_STACKSIZE="64M",
    )
    library = Path(env["EDMORE_LIB"]).resolve()
    (out / "execution_manifest.json").write_text(
        json.dumps(
            dict(
                recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                library=str(library),
                library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
                run_config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
                python=sys.executable,
                threads=args.threads,
                source_commit=subprocess.check_output(
                    ["git", "-C", str(MODEL), "rev-parse", "HEAD"], text=True
                ).strip(),
            ),
            indent=2,
        )
    )
    print("START " + tag, flush=True)
    with (out / "run.log").open("w") as log:
        p = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker", str(config)],
            cwd=HERE,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    print("END " + tag + " status=" + str(p.returncode), flush=True)
    if p.returncode:
        print((out / "run.log").read_text()[-5000:], flush=True)
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
