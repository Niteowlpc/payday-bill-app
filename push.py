#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n> {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, text=True)


def main() -> int:
    # Safety: must be inside a git repo
    if not (Path(".git").exists()):
        print("ERROR: No .git folder found. Run this from your repo root.")
        return 1

    # Show status first
    run(["git", "status", "--short"], check=False)

    # Ask for commit message
    msg = input("\nCommit message (leave blank to cancel): ").strip()
    if not msg:
        print("Canceled.")
        return 0

    # Stage, commit, push
    run(["git", "add", "."])
    try:
        run(["git", "commit", "-m", msg])
    except subprocess.CalledProcessError:
        print("\nNo commit created (possibly no changes).")
        # still try push in case branch is behind/ahead
    run(["git", "push", "origin", "main"])

    print("\nDone. Pushed to origin/main.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCanceled by user.")
        raise SystemExit(1)