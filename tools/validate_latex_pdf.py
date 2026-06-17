#!/usr/bin/env python3
"""Check the LaTeX-generated PDF for font and text-extraction regressions."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_NEEDLES = [
    "#eval 1 + 2",
    "String.append",
]


def run(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit(f"missing command: {command[0]}")
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        raise SystemExit(exc.returncode)
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--needle", action="append", default=[])
    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"missing PDF: {args.pdf}")
    for tool in ("pdffonts", "pdftotext"):
        if not shutil.which(tool):
            raise SystemExit(f"{tool} is not on PATH")

    fonts = run(["pdffonts", str(args.pdf)])
    text = run(["pdftotext", str(args.pdf), "-"])
    needles = args.needle or DEFAULT_NEEDLES

    failures: list[str] = []
    if "Type 3" in fonts or "Type3" in fonts:
        failures.append("Type 3 font found")
    for needle in needles:
        if needle not in text:
            failures.append(f"missing extracted text: {needle}")

    print("Font check:")
    print(fonts.strip())
    print()
    print(f"Text extraction length: {len(text)} characters")
    for needle in needles:
        print(f"Needle {needle!r}: {'ok' if needle in text else 'missing'}")

    if failures:
        print()
        print("FAILED:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print()
    print("PDF validation passed.")


if __name__ == "__main__":
    main()
