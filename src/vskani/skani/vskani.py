#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import shlex
import subprocess
from functools import partial
from glob import glob
from pathlib import Path
from shutil import copyfileobj, which
from typing import Iterator, Optional


def run_and_log_command(cmd: str, logfile: Path):
    logging.info(f"COMMAND: {cmd}")
    with logfile.open("ab") as fp:
        subprocess.run(shlex.split(cmd), stdout=fp, stderr=fp)


def glob_all_vmags(vmag_dir: Path, ext: str) -> Iterator[Path]:
    return vmag_dir.glob(f"*{ext}")


def sketch(
    vmag_dir: Path,
    outdir: Path,
    ext: str,
    cmp: int,
    marker: int,
    threads: int,
    logfile: Path,
):
    vMAGs = outdir.joinpath("vMAGs_filenames.txt")
    with open(vMAGs, "w") as fp:
        for vMAG in glob_all_vmags(vmag_dir, ext):
            fp.write(f"{vMAG}\n")

    sketchdir = outdir.joinpath("vMAGs_sketches")
    opts = f"-c {cmp} -m {marker} -t {threads}"
    cmd = f"skani sketch {opts} -o {sketchdir} -l {vMAGs}"

    run_and_log_command(cmd, logfile)

    sketchfile = outdir.joinpath("vMAGs_sketches.txt")
    with open(sketchfile, "w") as fp:
        for file in glob(f"{sketchdir}/*.sketch"):
            fp.write(f"{file}\n")


def skani(
    contigfile: Optional[Path],
    vmag_dir: Optional[Path],
    outdir: Path,
    cmp: int,
    marker: int,
    screen: float,
    min_af: float,
    threads: int,
    logfile: Path,
) -> Path:
    # vmag_dir =
    if vmag_dir is not None:
        sketchfile = outdir.joinpath("vMAGs_sketches.txt")
        ref = f"--rl {sketchfile}"

        if contigfile is not None:
            # vMAG vs unbinned
            query = f"--qi {contigfile}"
            output = "unbinned-vMAGs_skani_ANI.tsv"
        else:
            # vMAG vs vMAG
            query = f"--ql {sketchfile}"
            output = "vMAGs-vMAGs_skani_ANI.tsv"
    else:
        # unbinned vs unbinned
        ref = f"--ri {contigfile}"
        query = f"--qi {contigfile}"
        output = "unbinned-unbinned_skani_ANI.tsv"

    output = outdir.joinpath(output)
    opts = f"-c {cmp} -m {marker} -s {screen} --min-af {min_af} -t {threads}"
    cmd = f"skani dist {ref} {query} -o {output} {opts}"

    run_and_log_command(cmd, logfile)

    return output


def cleanup():
    ...


def main(
    contigfile: Optional[Path],
    vmag_dir: Optional[Path],
    output: Path,
    outdir: Path,
    ext: str,
    cmp: int,
    marker: int,
    screen: float,
    min_af: float,
    threads: int,
    command_log: Path,
    log: Path,
):
    outdir.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=command_log,
        level=logging.DEBUG,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if contigfile is None and vmag_dir is None:
        raise RuntimeError(
            "At least one of -c and -d flags need to be supplied for input "
            "genomes to query."
        )

    if which("skani") is None:
        raise RuntimeError(
            "Cannot find path to `skani`. Make sure `skani` is installed and in $PATH."
        )

    skani_runner = partial(
        skani,
        outdir=outdir,
        cmp=cmp,
        marker=marker,
        screen=screen,
        min_af=min_af,
        threads=threads,
        logfile=log,
    )

    results: list[Path] = list()
    # TODO: save to tmpdir and delete optionally

    # vMAG-vMAG comparison
    if vmag_dir is not None:
        sketch(vmag_dir, outdir, ext, cmp, marker, threads, log)
        result = skani_runner(contigfile=None, vmag_dir=vmag_dir)
        results.append(result)

    # unbinned-unbinned comparison
    if contigfile is not None:
        result = skani_runner(contigfile=contigfile, vmag_dir=None)
        results.append(result)

    # unbinned-vMAG comparison
    if contigfile is not None and vmag_dir is not None:
        result = skani_runner(contigfile=contigfile, vmag_dir=vmag_dir)
        results.append(result)

    # TODO: mv to cleanup logic
    with outdir.joinpath(output).open("wb") as fdst:
        for i, result in enumerate(results):
            with open(result, "rb") as fsrc:
                if i != 0:
                    # skip headers of remaining files
                    fsrc.readline()
                copyfileobj(fsrc, fdst)
            os.remove(result)
