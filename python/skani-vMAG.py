#!/usr/bin/env python3
import argparse
import logging
import os
import shlex
import subprocess
from functools import partial
from glob import glob
from pathlib import Path
from shutil import copyfileobj, which
from typing import List, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    io_args = parser.add_argument_group(
        "I/O -- AT LEAST ONE OF CONTIGS OR VMAGS REQUIRED"
    )
    io_args.add_argument(
        "-c",
        "--contigs",
        help="path to a single fasta genome fasta file of unbinned viral scaffolds/contigs",
    )
    io_args.add_argument(
        "-d",
        "--vmag-dir",
        help="directory containing all vMAG genome fasta files, where each file is a separate vMAG",
    )
    io_args.add_argument(
        "-x",
        "--ext",
        default=".fna",
        help="file extension for vMAG fasta files (default: %(default)s)",
    )
    io_args.add_argument(
        "--outdir",
        default=Path.cwd(),
        type=Path,
        help="output name (default cwd: %(default)s)",
    )
    io_args.add_argument(
        "-o",
        "--output",
        default="skani_ANI.tsv",
        help="output name (default: %(default)s)",
    )

    skani_args = parser.add_argument_group("SKANI")
    skani_args.add_argument(
        "-cm",
        "--compression-factor",
        default=125,
        type=int,
        help="Memory usage and runtime is inversely proportional to cm. Lower cm allows for ANI comparison of more distant genomes. (default: %(default)s)",
    )
    skani_args.add_argument(
        "-m",
        "--marker",
        default=1000,
        type=int,
        help="Marker k-mer compression factor. Markers are used for filtering. You want at least ~100 markers, so genome_size/marker_c > 100 is highly recommended. Higher value is more time/memory efficient. (default: %(default)s)",
    )
    skani_args.add_argument(
        "-s",
        "--screen",
        default=80.0,
        type=float,
        help="Screen out pairs with LESS THAN this percent identity using a hash table in constant time. (default: %(default)s)",
    )
    skani_args.add_argument(
        "-f",
        "--min-af",
        default=15.0,
        type=float,
        help="Only output ANI values where one genome has aligned fraction >= this value. (default: %(default)s)",
    )
    skani_args.add_argument(
        "-t",
        "--threads",
        default=15,
        type=int,
        help="number of threads to use (default: %(default)s)",
    )

    log_args = parser.add_argument_group("LOGGING")
    log_args.add_argument(
        "-cl",
        "--command-log",
        default="commands.log",
        help="file to log skani commands to (default: %(default)s)",
    )
    log_args.add_argument(
        "-l",
        "--log",
        default="skani.log",
        help="file to log skani command outputs to (default: %(default)s)",
    )

    return parser.parse_args()


def run_and_log_command(cmd: str, logfile: str):
    logging.info(f"COMMAND: {cmd}")
    with open(logfile, "ab") as fp:
        subprocess.run(shlex.split(cmd), stdout=fp, stderr=fp)


def glob_all_vmags(vmag_dir: str, ext: str) -> List[str]:
    pattern = f"{vmag_dir}/*{ext}"
    return glob(pattern)


def sketch(
    vmag_dir: str,
    outdir: Path,
    ext: str,
    cmp: int,
    marker: int,
    threads: int,
    logfile: str,
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
    contigfile: Optional[str],
    vmag_dir: Optional[str],
    outdir: Path,
    cmp: int,
    marker: int,
    screen: float,
    min_af: float,
    threads: int,
    logfile: str,
) -> Path:
    # vmag_dir =
    if vmag_dir is not None:
        sketchfile = outdir.joinpath("vMAGs_sketches.txt")
        ref = f"--rl {sketchfile}"

        if contigfile is not None:
            # vMAG vs unbinned
            query = f"--qi {contigfile}"
            output = "unbinned_vs_vMAGs_skani_ANI.tsv"
        else:
            # vMAG vs vMAG
            query = f"--ql {sketchfile}"
            output = "vMAGs_vs_vMAGs_skani_ANI.tsv"
    else:
        # unbinned vs unbinned
        ref = f"--ri {contigfile}"
        query = f"--qi {contigfile}"
        output = "unbinned_vs_unbinned_skani_ANI.tsv"

    output = outdir.joinpath(output)
    opts = f"-c {cmp} -m {marker} -s {screen} --min-af {min_af} -t {threads}"
    cmd = f"skani dist {ref} {query} -o {output} {opts}"

    run_and_log_command(cmd, logfile)

    return output


def main(
    contigfile: Optional[str],
    vmag_dir: Optional[str],
    output: str,
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
            "At least one of -c and -d flags need to be supplied for input genomes to query."
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

    results: List[Path] = list()

    if vmag_dir is not None:
        vmag_dir = vmag_dir.rstrip("/")
        sketch(vmag_dir, outdir, ext, cmp, marker, threads, log)
        result = skani_runner(contigfile=None, vmag_dir=vmag_dir)
        results.append(result)

    if contigfile is not None:
        result = skani_runner(contigfile=contigfile, vmag_dir=None)
        results.append(result)

    if contigfile is not None and vmag_dir is not None:
        result = skani_runner(contigfile=contigfile, vmag_dir=vmag_dir)
        results.append(result)

    with outdir.joinpath(output).open("wb") as fdst:
        for i, result in enumerate(results):
            with open(result, "rb") as fsrc:
                if i != 0:
                    # skip headers of remaining files
                    fsrc.readline()
                copyfileobj(fsrc, fdst)
            os.remove(result)


if __name__ == "__main__":
    args = parse_args()

    outdir: Path = args.outdir
    main(
        contigfile=args.contigs,
        vmag_dir=args.vmag_dir,
        outdir=outdir,
        output=args.output,
        ext=args.ext,
        cmp=args.compression_factor,
        marker=args.marker,
        screen=args.screen,
        min_af=args.min_af,
        threads=args.threads,
        command_log=outdir.joinpath(args.command_log),
        log=outdir.joinpath(args.log),
    )
