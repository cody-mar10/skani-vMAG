#!/usr/bin/env python3
from pathlib import Path

from vskani.utils import PolarsManager


class SkaniPreprocessor:
    def __init__(self, manager: PolarsManager, file: Path, **kwargs):
        self.manager = manager
        self.pl = manager.pl
        self.data = self.read_data(file, **kwargs)
        self.edge_weight_name = "weight"

    def read_data(self, file: Path, **kwargs):
        return self.pl.read_csv(source=file, separator="\t", **kwargs)

    def _preprocess(self, min_ani: float, min_af: float):
        filter_self_comparisons = self.pl.col("Ref_name") != self.pl.col("Query_name")

        filter_min_ani = self.pl.col("ANI") >= min_ani
        filter_min_af = (self.pl.col("Align_fraction_ref") >= min_af) | (
            self.pl.col("Align_fraction_query") >= min_af
        )

        self.data = self.data.filter(
            filter_self_comparisons & filter_min_ani & filter_min_af
        )
        return self

    def _create_edge_weights(self):
        # take min AF from reference and query perspective, ie worst case
        directional_min_af = self.pl.min(
            ["Align_fraction_query", "Align_fraction_ref"]
        ).alias("AF")

        # edge weights range from [0.0, 1.0]
        scale = 100**2
        edge_weights = self.pl.Expr.alias(
            self.pl.col("AF") * self.pl.col("ANI") / scale, self.edge_weight_name
        )

        self.data = self.data.with_columns(directional_min_af).with_columns(
            edge_weights
        )
        return self

    def process(self, min_ani: float, min_af: float):
        return self._preprocess(min_ani=min_ani, min_af=min_af)._create_edge_weights()

    def save(self, output: Path):
        select_cols = ["Ref_name", "Query_name", self.edge_weight_name]
        self.data.select(select_cols).write_csv(
            file=output, has_header=False, separator="\t"
        )

    def process_and_save(self, min_ani: float, min_af: float, output: Path):
        self.process(min_ani=min_ani, min_af=min_af).save(output=output)
