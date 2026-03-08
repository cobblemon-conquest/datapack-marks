#!/usr/bin/env python3
"""Set a JSON field to an empty array in all JSON files of a directory.

Usage:
    python3 scripts/set_json_field_empty_array.py <directory> <field>

Examples:
    # Top-level field
    python3 scripts/set_json_field_empty_array.py data/legendary_spawns_atm/spawn_pool_world buckets

    # Nested field with dot notation
    python3 scripts/set_json_field_empty_array.py data/some_folder "outer.inner.buckets"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set one field to [] in every JSON file inside a directory."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory that contains JSON files.",
    )
    parser.add_argument(
        "field",
        type=str,
        help="Field name to update. Supports dot notation (e.g. a.b.c).",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Also process JSON files in subdirectories.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show files that would be changed without writing them.",
    )
    return parser.parse_args()


def set_field_path_to_empty_array(payload: dict[str, Any], field_path: str) -> bool:
    parts = [p for p in field_path.split(".") if p]
    if not parts:
        raise ValueError("Field path cannot be empty.")

    current: Any = payload
    for key in parts[:-1]:
        if not isinstance(current, dict):
            return False
        next_value = current.get(key)
        if next_value is None:
            next_value = {}
            current[key] = next_value
        if not isinstance(next_value, dict):
            return False
        current = next_value

    if not isinstance(current, dict):
        return False

    leaf = parts[-1]
    changed = current.get(leaf) != []
    current[leaf] = []
    return changed


def iter_json_files(directory: Path, recursive: bool) -> list[Path]:
    if recursive:
        return sorted(p for p in directory.rglob("*.json") if p.is_file())
    return sorted(p for p in directory.glob("*.json") if p.is_file())


def main() -> int:
    args = parse_args()
    directory = args.directory

    if not directory.exists() or not directory.is_dir():
        print(f"Error: '{directory}' is not a valid directory.")
        return 1

    files = iter_json_files(directory, args.recursive)
    if not files:
        print("No JSON files found.")
        return 0

    changed_count = 0
    skipped_count = 0

    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            print(f"Skipping {file_path}: invalid JSON ({exc})")
            skipped_count += 1
            continue
        except OSError as exc:
            print(f"Skipping {file_path}: read error ({exc})")
            skipped_count += 1
            continue

        if not isinstance(data, dict):
            print(f"Skipping {file_path}: root JSON is not an object")
            skipped_count += 1
            continue

        try:
            changed = set_field_path_to_empty_array(data, args.field)
        except ValueError as exc:
            print(f"Error: {exc}")
            return 1

        if not changed:
            continue

        changed_count += 1
        if args.dry_run:
            print(f"Would update: {file_path}")
            continue

        try:
            file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Updated: {file_path}")
        except OSError as exc:
            print(f"Skipping {file_path}: write error ({exc})")
            skipped_count += 1

    print(
        f"Done. Changed: {changed_count}, Skipped: {skipped_count}, Total JSON files: {len(files)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
