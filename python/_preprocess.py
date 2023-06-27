#!/usr/bin/env python3
import argparse
import os


def main(file: str, output: str):
    SEL_COLUMNS = [
        "Ref_name",
        "Query_name",
        "ANI",
        "Align_fraction_ref",
        "Align_fraction_query",
    ]
    data = (
        pl.read_csv(file, sep="\t", columns=SEL_COLUMNS)
        .filter(pl.col("Ref_name") != pl.col("Query_name"))
        .with_column(
            pl.max(["Align_fraction_query", "Align_fraction_ref"]).alias("AF"),
        )
    )

    (
        data.with_column((pl.col("AF") * pl.col("ANI") / 100).alias("MCL"))
        .select(["Ref_name", "Query_name", "MCL"])
        .write_csv(
            output,
            has_header=False,
            sep="\t",
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Preprocess skani resutlts before clustering")

    parser.add_argument(
        "-i", "--input", required=True, help="raw tab-delimited results file from skani"
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="output tab-delimited graph file with the third columm being ANI * AF",
    )
    parser.add_argument(
        "-t",
        "--threads",
        default=10,
        type=int,
        help="number of threads (default: %(default)s)",
    )

    args = parser.parse_args()
    os.environ["POLARS_MAX_THREADS"] = str(args.threads)

    import polars as pl

    main(args.input, args.output)
