#!/usr/bin/env python3
"""Bump Mac and/or engine versions from release_manager/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as script without install
sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_bump.apply import execute_bump
from release_bump.archive import restore_from_archive
from release_bump.guide import print_release_guide
from release_bump.log import append_event, find_run_files, tail_jsonl
from release_bump.manifest import load_manifest
from release_bump.paths import REPO_ROOT
from release_bump.versions import read_engine_version, read_mac_version


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bump-versions",
        description="Bump Web Audit Mac and/or engine versions (manifest-driven).",
    )
    p.add_argument("--dry-run", action="store_true", help="Preview only; log as dry_run")
    p.add_argument("--yes", action="store_true", help="Skip double confirmation")
    p.add_argument("--mac", metavar="VERSION", help="New Mac app version")
    p.add_argument("--engine", metavar="VERSION", help="New engine version")
    p.add_argument(
        "--both",
        nargs=2,
        metavar=("MAC", "ENGINE"),
        help="Bump Mac and engine together",
    )
    p.add_argument("--release-guide", action="store_true", help="Print tag/smoke/GHCR steps")
    p.add_argument("--show", action="store_true", help="Show current versions from repo")
    p.add_argument("--log-tail", type=int, metavar="N", help="Print last N JSONL entries")
    p.add_argument("--restore", metavar="RUN_ID", help="Restore files from archive run_id")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = load_manifest()

    if args.release_guide:
        print_release_guide(manifest)
        return 0

    if args.show:
        print(f"Mac:    {read_mac_version(manifest)}")
        print(f"Engine: {read_engine_version(manifest)}")
        print(f"Root:   {REPO_ROOT}")
        return 0

    if args.log_tail is not None:
        for entry in tail_jsonl(args.log_tail):
            print(json.dumps(entry, indent=2))
        return 0

    if args.restore:
        files = find_run_files(args.restore)
        restored = restore_from_archive(args.restore, files)
        append_event(
            {
                "run_id": args.restore,
                "status": "restored",
                "mode": "restore",
                "files_touched": restored,
            }
        )
        print(f"Restored {len(restored)} file(s) from {args.restore}")
        for rel in restored:
            print(f"  {rel}")
        return 0

    mac_to = args.mac
    engine_to = args.engine
    if args.both:
        mac_to, engine_to = args.both

    if not mac_to and not engine_to:
        build_parser().print_help()
        return 2

    execute_bump(
        manifest,
        mac_to=mac_to,
        engine_to=engine_to,
        dry_run=args.dry_run,
        assume_yes=args.yes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
