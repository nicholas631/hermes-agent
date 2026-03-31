"""
Name: test_qwen.py
Description: Compatibility wrapper that runs the canonical Qwen 27B preflight tool.
Primary Functions:
  - Preserves the existing entrypoint for local Qwen endpoint checks.
  - Delegates to scripts/qwen27b_preflight.py with passthrough CLI args.
Revision: 0.1.0
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    project_root = Path(__file__).resolve().parent
    preflight = project_root / "scripts" / "qwen27b_preflight.py"
    command = [sys.executable, str(preflight), *argv]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
