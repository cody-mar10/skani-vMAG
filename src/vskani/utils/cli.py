from __future__ import annotations

from argparse import ArgumentParser, Namespace
from copy import copy
from typing import Callable, TypeVar

_T = TypeVar("_T")

_ARG_CALLBACK_TYPE = Callable[[ArgumentParser], None]
_ARG_CALLBACKS: dict[str, _ARG_CALLBACK_TYPE] = dict()

_ARG_PARSER_CALLBACK_TYPE = Callable[[Namespace], _T]
_ARG_PARSER_CALLBACKS: dict[str, _ARG_PARSER_CALLBACK_TYPE] = dict()


def register_argument_adder(key: str):
    def _register(callback: _ARG_CALLBACK_TYPE):
        _ARG_CALLBACKS[key] = callback
        return callback

    return _register


def register_parser(key: str):
    def _register(callback: _ARG_PARSER_CALLBACK_TYPE):
        _ARG_PARSER_CALLBACKS[key] = callback
        return callback

    return _register


def get_argument_adder_callbacks() -> dict[str, _ARG_CALLBACK_TYPE]:
    return copy(_ARG_CALLBACKS)


def get_parser_callbacks() -> dict[str, _ARG_PARSER_CALLBACK_TYPE]:
    return copy(_ARG_PARSER_CALLBACKS)
