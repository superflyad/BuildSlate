#!/usr/bin/env python3
"""Shared helpers for first-pass interconnect screening scripts."""
from __future__ import annotations

import argparse


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def print_section(title: str, lines: list[str]) -> None:
    print(f"\n{title}:")
    if not lines:
        print("- none")
        return
    for line in lines:
        print(f"- {line}")
