from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from . import _cli  # noqa: F401
from ._cli import MclArgs  # noqa: F401
from .utils import ClusterSummarizer, SummaryArgs, iload, load  # noqa: F401


def mcxload(file: Path, tabfile: Path, matfile: Path):
    input = f"-abc {file}"
    output = f"-write-tab {tabfile}"
    matoutput = f"-o {matfile}"

    command = f"mcxload {input} {output} {matoutput}"
    command = shlex.split(command)
    subprocess.run(command)


def mcl(
    tabfile: Path,
    matfile: Path,
    output: Path,
    inflation: float = 2.0,
):
    usetab = f"-use-tab {tabfile}"
    out = f"-o {output}"

    command = f"mcl {matfile} {usetab} -I {inflation} {out}"
    command = shlex.split(command)
    subprocess.run(command)


def run(file: Path, tabfile: Path, matfile: Path, output: Path, inflation: float = 2.0):
    mcxload(file=file, tabfile=tabfile, matfile=matfile)
    mcl(tabfile=tabfile, matfile=matfile, output=output, inflation=inflation)
