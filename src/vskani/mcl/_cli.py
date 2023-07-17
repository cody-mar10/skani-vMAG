from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from vskani.utils import register_argument_adder, register_parser

_MODULE_NAME = "mcl"


@dataclass
class MclArgs:
    input: Path
    output: Path
    inflation: float

    def __post_init__(self):
        self.tabfile = self.input.with_suffix(".mcxload")
        self.matfile = self.input.with_suffix(".mci")


@register_parser(_MODULE_NAME)
def parse_args(ap_args: argparse.Namespace) -> Optional[MclArgs]:
    try:
        if hasattr(ap_args, "output_processed"):
            input = ap_args.output_processed
        else:
            input = ap_args.input

        args = MclArgs(
            input=input,
            output=ap_args.mcl_output,
            inflation=ap_args.inflation,
        )
    except AttributeError:
        args = None
    return args


@register_argument_adder(_MODULE_NAME)
def add_args(parser: argparse.ArgumentParser, add_input: bool = True):
    group = parser.add_argument_group("MCL")
    if add_input:
        group.add_argument(
            "-i",
            "--input",
            type=Path,
            metavar="FILE",
            required=True,
            help="processed tab-delimited skani file",
        )

    group.add_argument(
        "-mo",
        "--mcl-output",
        type=Path,
        metavar="FILE",
        default=Path("dereplicated_virus.clusters"),
        help=(
            "output clusters file, where each tab-delimited row is all the "
            "members of the cluster (default: %(default)s)"
        ),
    )
    group.add_argument(
        "-I",
        "--inflation",
        type=float,
        metavar="FLOAT",
        default=2.0,
        help=(
            "mcl inflation value. higher = more strict clustering, meaning clustered "
            "genomes have more ANI (default: %(default)s)"
        ),
    )
