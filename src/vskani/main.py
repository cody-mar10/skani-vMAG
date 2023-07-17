from __future__ import annotations

import argparse
from dataclasses import dataclass
from pprint import pprint
from typing import Literal, Optional

from vskani.mcl import ClusterSummarizer, MclArgs, SummaryArgs
from vskani.mcl import run as mcl
from vskani.skani import SkaniPreprocessor, VSkaniArgs
from vskani.skani.vskani import main as skani
from vskani.utils import (
    PolarsManager,
    get_argument_adder_callbacks,
    get_parser_callbacks,
)


@dataclass
class Args:
    skani: Optional[VSkaniArgs]
    mcl: Optional[MclArgs]
    summary: Optional[SummaryArgs]
    command: Literal["skani", "mcl", "all", "summarize"]


def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        description=(
            "use skani to perform all pairwise virus ANI computations, vMAG inclusive."
        )
    )
    subparsers = parser.add_subparsers(dest="command")
    skani_parser = subparsers.add_parser(
        "skani", help="Pairwise ANI calculations using skani"
    )
    mcl_parser = subparsers.add_parser(
        "mcl",
        help="Graph clustering of pairwise ANI values using mcl",
    )
    summary_parser = subparsers.add_parser(
        "summarize", help="Summarize ANI per cluster"
    )
    pipeline_parser = subparsers.add_parser(
        "all", help="Perform both ANI calculations and then cluster immediately"
    )

    argument_adders = get_argument_adder_callbacks()
    argument_adders["skani"](skani_parser)
    argument_adders["skani"](pipeline_parser)
    argument_adders["mcl"](mcl_parser, add_input=True)  # type: ignore
    argument_adders["mcl"](pipeline_parser, add_input=False)  # type: ignore
    argument_adders["summarize"](summary_parser, add_input=True)  # type: ignore
    argument_adders["summarize"](pipeline_parser, add_input=False)  # type: ignore

    args = parser.parse_args()
    argument_parsers = get_parser_callbacks()
    skani_args: Optional[VSkaniArgs] = argument_parsers["skani"](args)
    mcl_args: Optional[MclArgs] = argument_parsers["mcl"](args)
    summary_args: Optional[SummaryArgs] = argument_parsers["summarize"](args)

    cli_args = Args(
        skani=skani_args,
        mcl=mcl_args,
        summary=summary_args,
        command=args.command,
    )

    return cli_args


def main():
    args = parse_args()
    pprint(args)

    if args.command in ["all", "skani"]:
        manager = PolarsManager(args.skani.threads)
    elif args.command == "summarize":
        manager = PolarsManager(args.summary.threads)

    match args.command:
        case "all":
            skani(
                contigfile=args.skani.io.contigs,
                vmag_dir=args.skani.io.vmag_dir,
                output=args.skani.io.skani_output,
                outdir=args.skani.io.outdir,
                ext=args.skani.io.ext,
                cmp=args.skani.skani.compression_factor,
                marker=args.skani.skani.marker,
                screen=args.skani.skani.screen,
                min_af=args.skani.skani.min_af,
                threads=args.skani.threads,
                command_log=args.skani.logger.command_log,
                log=args.skani.logger.log,
            )
            preprocessor = SkaniPreprocessor(
                manager=manager, file=args.skani.io.skani_output
            )
            preprocessor.process_and_save(
                min_ani=args.skani.preprocessing.min_ani,
                min_af=args.skani.preprocessing.min_cov,
                output=args.skani.io.processed_output,
            )
            mcl(
                file=args.skani.io.processed_output,
                tabfile=args.mcl.tabfile,
                matfile=args.mcl.matfile,
                output=args.mcl.output,
                inflation=args.mcl.inflation,
            )
            # ANI-per cluster
            summarizer = ClusterSummarizer(
                manager=manager,
                skani_file=args.skani.io.processed_output,
                clusters_file=args.mcl.output,
            )
            summarizer.summarize_and_save(output=args.summary.output)
        case "skani":
            skani(
                contigfile=args.skani.io.contigs,
                vmag_dir=args.skani.io.vmag_dir,
                output=args.skani.io.skani_output,
                outdir=args.skani.io.outdir,
                ext=args.skani.io.ext,
                cmp=args.skani.skani.compression_factor,
                marker=args.skani.skani.marker,
                screen=args.skani.skani.screen,
                min_af=args.skani.skani.min_af,
                threads=args.skani.threads,
                command_log=args.skani.logger.command_log,
                log=args.skani.logger.log,
            )
            preprocessor = SkaniPreprocessor(
                manager=manager, file=args.skani.io.skani_output
            )
            preprocessor.process_and_save(
                min_ani=args.skani.preprocessing.min_ani,
                min_af=args.skani.preprocessing.min_cov,
                output=args.skani.io.processed_output,
            )
        case "mcl":
            mcl(
                file=args.skani.io.processed_output,
                tabfile=args.mcl.tabfile,
                matfile=args.mcl.matfile,
                output=args.mcl.output,
                inflation=args.mcl.inflation,
            )
        case "summarize":
            summarizer = ClusterSummarizer(
                manager=manager,
                skani_file=args.summary.skani_input,
                clusters_file=args.summary.mcl_output,
            )
            summarizer.summarize_and_save(output=args.summary.output)


if __name__ == "__main__":
    main()
