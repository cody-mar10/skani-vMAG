from __future__ import annotations

import os
from typing import cast

TOTAL_CPUS = cast(int, os.cpu_count())


class PolarsManager:
    """Manage the import of the `polars` package by limiting the size of the
    `polars` threadpool. Access to the `polars` module is provided by the
    `self.pl` attribute."""

    def __init__(self, threads: int = TOTAL_CPUS):
        self._threads = threads
        os.environ["POLARS_MAX_THREADS"] = str(threads)
        import polars as pl

        self.pl = pl

    def __repr__(self) -> str:
        name = f"{self.__class__.__name__}(threads={self._threads})"
        return name
