#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test that token-iʿrāb CLI help works without live qamus_wbw services."""
import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "tools/build_token_irab_decisions.py", "--help"],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "--from" in result.stdout
    assert "--out" in result.stdout
    print("token irab help self-test OK")


if __name__ == "__main__":
    main()
