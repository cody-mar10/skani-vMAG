from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from vskani.utils import PolarsManager, register_argument_adder, register_parser

_MODULE_NAME = "summarize"


@dataclass
class SummaryArgs:
    skani_input: Path
    mcl_output: Path
    output: Path
    threads: int


@register_parser(_MODULE_NAME)
def parse_args(ap_args: argparse.Namespace) -> Optional[SummaryArgs]:
    try:
        if hasattr(ap_args, "output_processed"):
            # pipeline command
            skani_input = ap_args.output
            summary_output = ap_args.summary_output
        else:
            skani_input = ap_args.input
            summary_output = ap_args.output

        mcl_output = ap_args.mcl_output
        threads = ap_args.threads
    except AttributeError:
        return None

    return SummaryArgs(
        skani_input=skani_input,
        mcl_output=mcl_output,
        output=summary_output,
        threads=threads,
    )


@register_argument_adder(_MODULE_NAME)
def add_args(parser: argparse.ArgumentParser, add_input: bool = True):
    group = parser.add_argument_group("SUMMARY")
    if add_input:
        group.add_argument(
            "-i",
            "--input",
            type=Path,
            metavar="FILE",
            required=True,
            help="original skani output file (before preprocessing for mcl)",
        )
        group.add_argument(
            "-t",
            "--threads",
            default=15,
            type=int,
            help="number of threads to use (default: %(default)s)",
        )
        group.add_argument(
            "-mo",
            "--mcl-output",
            type=Path,
            metavar="FILE",
            required=True,
            help=(
                "output clusters file, where each tab-delimited row is all the "
                "members of the cluster"
            ),
        )
        group.add_argument(
            "-o",
            "--output",
            type=Path,
            metavar="FILE",
            default=Path("ani_per_cluster.tsv"),
            help=("output ani per cluster summary file (default: %(default)s)"),
        )
    else:
        group.add_argument(
            "--summary-output",
            type=Path,
            metavar="FILE",
            default=Path("ani_per_cluster.tsv"),
            help=("output ani per cluster summary file (default: %(default)s)"),
        )


def iload(file: Path, min_cluster_size: int = 2) -> Iterator[list[str]]:
    # each cluster is on a single tab-delimited line in the mcl format
    with file.open() as fp:
        for line in fp:
            cluster = line.rstrip().split("\t")
            if len(cluster) >= min_cluster_size:
                yield cluster


def load(file: Path, min_cluster_size: int = 2) -> list[list[str]]:
    loader = iload(file=file, min_cluster_size=min_cluster_size)
    clusters = [cluster for cluster in loader]
    return clusters


class ClusterSummarizer:
    def __init__(
        self,
        manager: PolarsManager,
        skani_file: Path,
        clusters_file: Path,
        min_cluster_size: int = 2,
    ):
        self.manager = manager
        self.pl = manager.pl
        self.ani_data = self.pl.read_csv(skani_file, separator="\t")
        self.clusters_file = clusters_file
        self.min_cluster_size = min_cluster_size

        self._merge_cluster_ids()

    def _map_members_to_cluster_ids(self) -> dict[str, int]:
        loader = iload(file=self.clusters_file, min_cluster_size=self.min_cluster_size)

        member2cluster = {
            member: cluster_id
            for cluster_id, cluster in enumerate(loader)
            for member in cluster
        }

        return member2cluster

    def _merge_cluster_ids(self):
        records = list(self._map_members_to_cluster_ids().items())
        clusters = self.pl.from_records(records, schema=["name", "cluster"])

        self.ani_data = (
            self.ani_data.join(
                clusters.rename({"name": "Ref_name", "cluster": "Ref_cluster"}),
                on="Ref_name",
            )
            .join(
                clusters.rename({"name": "Query_name", "cluster": "Query_cluster"}),
                on="Query_name",
            )
            .filter(self.pl.col("Ref_cluster") == self.pl.col("Query_cluster"))
        )

    def average_ANI_per_cluster(self):
        summary = (
            self.ani_data.groupby("Ref_cluster")
            .agg(self.pl.col("ANI").mean().alias("avg_ANI"))
            .rename({"Ref_cluster": "cluster"})
            .sort(by="avg_ANI")
        )

        return summary

    def summarize_and_save(self, output: Path):
        summary = self.average_ANI_per_cluster()
        summary.write_csv(output, separator="\t")
