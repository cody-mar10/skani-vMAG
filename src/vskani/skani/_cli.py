from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from vskani.utils import register_argument_adder, register_parser

_MODULE_NAME = "skani"


def check_range(value: float, range: tuple[float, float], name: str):
    minval, maxval = range
    if not (minval <= value <= maxval):
        raise ValueError(
            f"{name} ({value}) not in inclusive range [{minval}, {maxval}]"
        )


@dataclass
class IOArgs:
    contigs: Optional[Path]
    vmag_dir: Optional[Path]
    outdir: Path
    skani_output: Path
    processed_output: Path
    ext: str


@dataclass
class LogArgs:
    command_log: Path
    log: Path


@dataclass
class SkaniArgs:
    compression_factor: int
    marker: int
    screen: float
    min_af: float


@dataclass
class PreprocessingArgs:
    min_ani: float
    min_cov: float

    def __post_init__(self):
        valrange = (0.0, 1.0)
        check_range(self.min_ani, valrange, "--min-ani")
        check_range(self.min_cov, valrange, "--min-cov")

        # skani outputs values in range [0.0, 100.0]
        self.min_ani *= 100.0
        self.min_cov *= 100.0


@dataclass
class VSkaniArgs:
    io: IOArgs
    skani: SkaniArgs
    logger: LogArgs
    preprocessing: PreprocessingArgs
    threads: int

    def __post_init__(self):
        if self.io.contigs is None and self.io.vmag_dir is None:
            msg = "One of --contigs or --vmag-dir is required."
            raise RuntimeError(msg)


@register_parser(_MODULE_NAME)
def parse_args(ap_args: argparse.Namespace) -> Optional[VSkaniArgs]:
    try:
        outdir: Path = ap_args.outdir

        io_args = IOArgs(
            contigs=ap_args.contigs,
            vmag_dir=ap_args.vmag_dir,
            outdir=outdir,
            skani_output=ap_args.output,
            processed_output=ap_args.output_processed,
            ext=ap_args.ext,
        )
        skani_args = SkaniArgs(
            compression_factor=ap_args.compression_factor,
            marker=ap_args.marker,
            screen=ap_args.screen,
            min_af=ap_args.min_af,
        )
        log_args = LogArgs(
            command_log=outdir.joinpath(ap_args.command_log),
            log=outdir.joinpath(ap_args.log),
        )
        preprocessing_args = PreprocessingArgs(
            min_ani=ap_args.min_ani,
            min_cov=ap_args.min_cov,
        )

        args = VSkaniArgs(
            io=io_args,
            skani=skani_args,
            logger=log_args,
            preprocessing=preprocessing_args,
            threads=ap_args.threads,
        )
    except AttributeError:
        args = None

    return args


def _add_io_args(parser: argparse.ArgumentParser):
    io_args = parser.add_argument_group(
        "I/O -- AT LEAST ONE OF CONTIGS OR VMAGS REQUIRED"
    )
    io_args.add_argument(
        "-c",
        "--contigs",
        metavar="FILE",
        type=Path,
        help="path to a single fasta genome fasta file of unbinned viral scaffolds/contigs",  # noqa: E501
    )
    io_args.add_argument(
        "-d",
        "--vmag-dir",
        metavar="DIR",
        type=Path,
        help="directory containing all vMAG genome fasta files, where each file is a separate vMAG",  # noqa: E501
    )
    io_args.add_argument(
        "-x",
        "--ext",
        default=".fna",
        help="file extension for vMAG fasta files (default: %(default)s)",
    )
    io_args.add_argument(
        "--outdir",
        metavar="DIR",
        type=Path,
        default=Path.cwd(),
        help="output name (default cwd: %(default)s)",
    )
    io_args.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        type=Path,
        default=Path("skani_ANI.tsv"),
        help="output skani ANI file from all comparisons (default: %(default)s)",
    )


def _add_skani_args(parser: argparse.ArgumentParser):
    skani_args = parser.add_argument_group("SKANI")
    skani_args.add_argument(
        "-cm",
        "--compression-factor",
        default=125,
        type=int,
        help=(
            "Memory usage and runtime is inversely proportional to cm. Lower cm "
            "allows for ANI comparison of more distant genomes. (default: %(default)s)"
        ),
    )
    skani_args.add_argument(
        "-m",
        "--marker",
        default=1000,
        type=int,
        help=(
            "Marker k-mer compression factor. Markers are used for filtering. "
            "You want at least ~100 markers, so genome_size/marker_c > 100 is highly "
            "recommended. Higher value is more time/memory efficient. "
            "(default: %(default)s)"
        ),
    )
    skani_args.add_argument(
        "-s",
        "--screen",
        default=80.0,
        type=float,
        help=(
            "Screen out pairs with LESS THAN this percent identity using a hash "
            "table in constant time. (default: %(default)s)"
        ),
    )
    skani_args.add_argument(
        "-f",
        "--min-af",
        default=15.0,
        type=float,
        help=(
            "Only output ANI values where one genome has aligned fraction >= this "
            "value. (default: %(default)s)"
        ),
    )
    skani_args.add_argument(
        "-t",
        "--threads",
        default=15,
        type=int,
        help="number of threads to use (default: %(default)s)",
    )


def _add_logging_args(parser: argparse.ArgumentParser):
    log_args = parser.add_argument_group("LOGGING")
    log_args.add_argument(
        "-cl",
        "--command-log",
        metavar="FILE",
        type=Path,
        default=Path("commands.log"),
        help="file to log skani commands to (default: %(default)s)",
    )
    log_args.add_argument(
        "-l",
        "--log",
        metavar="FILE",
        type=Path,
        default=Path("skani.log"),
        help="file to log skani command outputs to (default: %(default)s)",
    )


def _add_preprocessing_args(parser: argparse.ArgumentParser):
    preprocessing_args = parser.add_argument_group(
        "PREPROCESSING AFTER SKANI BEFORE MCL"
    )

    preprocessing_args.add_argument(
        "-op",
        "--output-processed",
        type=Path,
        default=Path("skani_processed.tsv"),
        help="output processed ANI file for MCL clustering (default: %(default)s)",
    )
    preprocessing_args.add_argument(
        "-ma",
        "--min-ani",
        type=float,
        default=0.95,
        help="minimum ANI to consider for clustering (default: %(default)s) range: [0.0, 1.0]",  # noqa: E501
    )
    preprocessing_args.add_argument(
        "-mc",
        "--min-cov",
        type=float,
        default=0.5,
        help="minimum coverage for aligned fractions to consider for clustering (default: %(default)s) range: [0.0, 1.0]",  # noqa: E501
    )


@register_argument_adder(_MODULE_NAME)
def add_args(parser: argparse.ArgumentParser):
    _add_io_args(parser)
    _add_skani_args(parser)
    _add_logging_args(parser)
    _add_preprocessing_args(parser)
