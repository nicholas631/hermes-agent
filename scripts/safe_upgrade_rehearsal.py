#!/usr/bin/env python3
"""
Name: scripts/safe_upgrade_rehearsal.py
Description: Read-only helper that prepares a non-destructive Hermes upgrade rehearsal plan.
Primary Functions:
  - Captures branch/divergence state needed before upgrading.
  - Prints safe branch/worktree-first commands with rollback guidance.
  - Exports the rehearsal plan as JSON for reporting.
Revision: 0.1.0
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class UpgradeSnapshot:
    repo_root: str
    branch_line: str
    behind_count: int
    ahead_count: int
    head_sha: str


def _git(repo_root: Path, *args: str) -> str:
    command = ["git", *args]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def capture_snapshot(repo_root: Path) -> UpgradeSnapshot:
    status = _git(repo_root, "status", "--short", "--branch")
    branch_line = status.splitlines()[0] if status else "unknown"
    behind = int(_git(repo_root, "rev-list", "--count", "HEAD..origin/main"))
    ahead = int(_git(repo_root, "rev-list", "--count", "origin/main..HEAD"))
    sha = _git(repo_root, "rev-parse", "--short", "HEAD")
    return UpgradeSnapshot(
        repo_root=str(repo_root),
        branch_line=branch_line,
        behind_count=behind,
        ahead_count=ahead,
        head_sha=sha,
    )


def _print_plan(snapshot: UpgradeSnapshot) -> None:
    print("Safe Hermes upgrade rehearsal")
    print("=" * 60)
    print(f"Repo root:   {snapshot.repo_root}")
    print(f"Branch:      {snapshot.branch_line}")
    print(f"Behind/Ahead {snapshot.behind_count}/{snapshot.ahead_count}")
    print(f"HEAD SHA:    {snapshot.head_sha}")
    print()
    print("Recommended non-destructive rehearsal steps (PowerShell):")
    print("1) git fetch origin")
    print("2) git log --oneline --decorate HEAD..origin/main")
    print("3) git log --oneline --decorate origin/main..HEAD")
    print("4) git branch backup/qwen27b-safe-upgrade")
    print("5) git worktree add ..\\Hermes_Agent_upgrade_rehearsal origin/main")
    print("6) cd ..\\Hermes_Agent_upgrade_rehearsal")
    print("7) .\\.venv\\Scripts\\python.exe -m pytest tests\\agent -q")
    print("8) .\\.venv\\Scripts\\python.exe -m pytest tests\\hermes_cli -q")
    print()
    print("Fallback handling:")
    print("- If upstream diverged, keep the main tree untouched and continue testing in worktree.")
    print("- If tests fail in worktree, delete rehearsal tree and keep current branch intact.")
    print("- Only apply merge/rebase in primary tree after rehearsal pass.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare non-destructive upgrade rehearsal steps")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to git repository root",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional file path for JSON snapshot output",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    snapshot = capture_snapshot(repo_root)
    _print_plan(snapshot)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(asdict(snapshot), handle, indent=2)
        print(f"JSON snapshot written to: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
