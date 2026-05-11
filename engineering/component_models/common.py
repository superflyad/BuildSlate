#!/usr/bin/env python3
"""Shared reporting helpers for first-pass component physics models."""

from __future__ import annotations

import argparse
from collections.abc import Iterable


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be zero or greater")
    return parsed


def fraction(value: str) -> float:
    parsed = float(value)
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("value must be between 0 and 1")
    return parsed


def percent(value: str) -> float:
    parsed = float(value)
    if not 0 <= parsed <= 100:
        raise argparse.ArgumentTypeError("value must be between 0 and 100")
    return parsed


def bool_arg(value: str) -> bool:
    normalized = value.lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("value must be true or false")


def print_section(title: str, rows: Iterable[str]) -> None:
    print(f"{title}:")
    for row in rows:
        print(f"  {row}")


def mm3_to_cm3(volume_mm3: float) -> float:
    return volume_mm3 / 1000.0


def mm2_to_cm2(area_mm2: float) -> float:
    return area_mm2 / 100.0
