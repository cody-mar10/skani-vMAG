#!/usr/bin/env python3
import argparse
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Args:
    input: Path
    output: Path
    threads: int
    min_ani: float
    min_cov: float


def check_range(value: float, min_: float, max_: float, name):
    if not (min_ <= value <= max_):
        raise ValueError(f"{name} ({value}) not in inclusive range [{min_}, {max_}]")


def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        description="Preprocess skani output for MCL clustering"
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="input tab-delimited skani ANI summary file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("skani_processed.tsv"),
        help="output processed ANI file for MCL clustering (default: %(default)s)",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=10,
        help="number of polars threads (default: %(default)s)",
    )
    parser.add_argument(
        "-a",
        "--min-ani",
        type=float,
        default=0.95,
        help="minimum ANI to consider for clustering (default: %(default)s) range: [0.0, 1.0]",
    )
    parser.add_argument(
        "-c",
        "--min-cov",
        type=float,
        default=0.5,
        help="minimum coverage for aligned fractions to consider for clustering (default: %(default)s) range: [0.0, 1.0]",
    )

    args = parser.parse_args()
    check_range(args.min_ani, 0.0, 1.0, "--min-ani")
    check_range(args.min_cov, 0.0, 1.0, "--min-cov")

    return Args(
        input=args.input,
        output=args.output,
        threads=args.threads,
        min_ani=args.min_ani * 100,
        min_cov=args.min_cov * 100,
    )


def main():
    args = parse_args()

    (
        pl.read_csv(args.input, sep="\t")
        .drop(["Ref_file", "Query_file"])
        .filter(
            (pl.col("Ref_name") != pl.col("Query_name"))
            & (pl.col("ANI") >= args.min_ani)
            & (
                (pl.col("Align_fraction_ref") >= args.min_cov)
                | (pl.col("Align_fraction_query") >= args.min_cov)
            )
        )
        .select(
            [
                "Ref_name",
                "Query_name",
                "ANI",
                "Align_fraction_ref",
                "Align_fraction_query",
            ]
        )
        .with_columns(
            pl.min(["Align_fraction_query", "Align_fraction_ref"]).alias("AF"),
        )
        .with_columns((pl.col("AF") * pl.col("ANI") / 100).alias("MCL"))
        .select(["Ref_name", "Query_name", "MCL"])
        .write_csv(args.output, has_header=False, sep="\t")
    )


if __name__ == "__main__":
    threads = parse_args().threads
    os.environ["POLARS_MAX_THREADS"] = str(threads)
    import polars as pl

    main()
