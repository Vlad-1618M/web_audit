from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .archive import archive_run_dir, new_run_id, snapshot_files
from .confirm import double_confirm
from .log import append_event
from .manifest import Manifest
from .paths import REPO_ROOT
from .versions import (
    apply_line_rule,
    read_engine_version,
    read_mac_version,
    replace_version_literal,
    whole_file_version,
)


@dataclass
class PlannedChange:
    path: str
    old_snippet: str
    new_snippet: str
    replacements: int


@dataclass
class BumpPlan:
    mode: str
    run_id: str
    mac_from: str | None = None
    mac_to: str | None = None
    engine_from: str | None = None
    engine_to: str | None = None
    changes: list[PlannedChange] = field(default_factory=list)

    @property
    def files(self) -> list[str]:
        return [c.path for c in self.changes]


def _unique_ordered(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def plan_bump(manifest: Manifest, *, mac_to: str | None, engine_to: str | None,) -> BumpPlan:
    
    if mac_to and engine_to:
        mode = "both"
    elif mac_to:
        mode = "mac"
    elif engine_to:
        mode = "engine"
    else:
        raise ValueError("Specify --mac, --engine, or --both")

    plan = BumpPlan(mode=mode, run_id=new_run_id())
    changes_by_path: dict[str, PlannedChange] = {}

    if mac_to:
        plan.mac_from = read_mac_version(manifest)
        plan.mac_to = mac_to
        if plan.mac_from == mac_to:
            raise ValueError(f"Mac version already {mac_to}")

        for rel in manifest.mac_replace_files:
            path = REPO_ROOT / rel
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            if rel == manifest.mac_version_file:
                new_content = whole_file_version(content, mac_to)
                count = 1 if content.strip() != mac_to else 0
            else:
                new_content, count = replace_version_literal(content, plan.mac_from, mac_to)
            if count or new_content != content:
                changes_by_path[rel] = PlannedChange(
                    path=rel,
                    old_snippet=plan.mac_from,
                    new_snippet=mac_to,
                    replacements=max(count, 1) if new_content != content else 0,
                )

    if engine_to:
        plan.engine_from = read_engine_version(manifest)
        plan.engine_to = engine_to
        if plan.engine_from == engine_to:
            raise ValueError(f"Engine version already {engine_to}")

        for rule in manifest.engine_version_rules:
            path = REPO_ROOT / rule.path
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            new_content, count = apply_line_rule(content, rule, plan.engine_from, engine_to)
            if count:
                changes_by_path[rule.path] = PlannedChange(
                    path=rule.path,
                    old_snippet=plan.engine_from,
                    new_snippet=engine_to,
                    replacements=count,
                )

        for rel in manifest.engine_replace_files:
            if rel in changes_by_path:
                path = REPO_ROOT / rel
                content = path.read_text(encoding="utf-8")
                new_content, count = replace_version_literal(
                    content, plan.engine_from, engine_to
                )
                if count:
                    existing = changes_by_path[rel]
                    changes_by_path[rel] = PlannedChange(
                        path=rel,
                        old_snippet=plan.engine_from,
                        new_snippet=engine_to,
                        replacements=existing.replacements + count,
                    )
                continue
            path = REPO_ROOT / rel
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            new_content, count = replace_version_literal(content, plan.engine_from, engine_to)
            if count:
                changes_by_path[rel] = PlannedChange(
                    path=rel,
                    old_snippet=plan.engine_from,
                    new_snippet=engine_to,
                    replacements=count,
                )

    plan.changes = [changes_by_path[k] for k in sorted(changes_by_path)]
    if not plan.changes:
        raise ValueError("No files would change — check manifest paths and current versions")
    return plan


def print_plan(plan: BumpPlan, *, dry_run: bool) -> None:
    label = "DRY RUN" if dry_run else "APPLY"
    print(f"\n=== {label}: {plan.mode} bump (run_id={plan.run_id}) ===")
    if plan.mac_to:
        print(f"Mac:    {plan.mac_from} → {plan.mac_to}")
    if plan.engine_to:
        print(f"Engine: {plan.engine_from} → {plan.engine_to}")
    print(f"Files ({len(plan.changes)}):")
    for ch in plan.changes:
        print(f"  {ch.path}  ({ch.replacements} replacement(s))")
    print()


def _write_changes(plan: BumpPlan, manifest: Manifest) -> None:
    for ch in plan.changes:
        path = REPO_ROOT / ch.path
        content = path.read_text(encoding="utf-8")

        if plan.mac_to and ch.path in manifest.mac_replace_files:
            if ch.path == manifest.mac_version_file:
                content = whole_file_version(content, plan.mac_to)
            elif plan.mac_from:
                content, _ = replace_version_literal(content, plan.mac_from, plan.mac_to)

        if plan.engine_to:
            for rule in manifest.engine_version_rules:
                if ch.path == rule.path and plan.engine_from:
                    content, _ = apply_line_rule(content, rule, plan.engine_from, plan.engine_to)
            if ch.path in manifest.engine_replace_files and plan.engine_from:
                content, _ = replace_version_literal(content, plan.engine_from, plan.engine_to)

        path.write_text(content, encoding="utf-8")


def execute_bump(
    manifest: Manifest, *, mac_to: str | None, 
    engine_to: str | None, dry_run: bool = False, assume_yes: bool = False,) -> BumpPlan:
    
    plan = plan_bump(manifest, mac_to=mac_to, engine_to=engine_to)
    print_plan(plan, dry_run=dry_run)

    if not double_confirm(
        mode=plan.mode,
        mac_from=plan.mac_from,
        mac_to=plan.mac_to,
        engine_from=plan.engine_from,
        engine_to=plan.engine_to,
        file_count=len(plan.changes),
        dry_run=dry_run,
        assume_yes=assume_yes,
    ):
        append_event(
            {
                "run_id": plan.run_id,
                "status": "aborted",
                "mode": plan.mode,
                "dry_run": dry_run,
                "mac": {"from": plan.mac_from, "to": plan.mac_to} if plan.mac_to else None,
                "engine": {"from": plan.engine_from, "to": plan.engine_to}
                if plan.engine_to
                else None,
                "files_touched": plan.files,
            }
        )
        raise SystemExit(1)

    status = "dry_run" if dry_run else "completed"
    try:
        if not dry_run:
            snapshot_files(plan.run_id, plan.files)
            _write_changes(plan, manifest)
    except Exception as exc:
        append_event(
            {
                "run_id": plan.run_id,
                "status": "failed",
                "mode": plan.mode,
                "dry_run": dry_run,
                "error": str(exc),
                "mac": {"from": plan.mac_from, "to": plan.mac_to} if plan.mac_to else None,
                "engine": {"from": plan.engine_from, "to": plan.engine_to}
                if plan.engine_to
                else None,
                "files_touched": plan.files,
            }
        )
        raise

    append_event(
        {
            "run_id": plan.run_id,
            "status": status,
            "mode": plan.mode,
            "dry_run": dry_run,
            "mac": {"from": plan.mac_from, "to": plan.mac_to} if plan.mac_to else None,
            "engine": {"from": plan.engine_from, "to": plan.engine_to}
            if plan.engine_to
            else None,
            "files_touched": plan.files,
            "archive": str(archive_run_dir(plan.run_id)) if not dry_run else None,
        }
    )

    if dry_run:
        print("Dry run complete — no files modified.")
    else:
        print(f"Done. Archive: {archive_run_dir(plan.run_id)}")
        print(f"Log: release_manager/releases/release-history.jsonl")
    return plan
