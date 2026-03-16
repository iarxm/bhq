#!/usr/bin/env python3
"""Render a tree-style metadata view for Borg repositories."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable


DEFAULT_ITEM_FIELDS = (
    "path",
    "type",
    "size",
    "mtime",
    "user",
    "group",
    "mode",
    "healthy",
)


@dataclass
class TreeNode:
    name: str
    node_type: str = "dir"
    metadata: dict[str, object] = field(default_factory=dict)
    children: dict[str, "TreeNode"] = field(default_factory=dict)

    def add_path(self, parts: list[str], metadata: dict[str, object]) -> None:
        if not parts:
            self.metadata = metadata
            self.node_type = str(metadata.get("type", self.node_type))
            return

        head = parts[0]
        child = self.children.get(head)
        if child is None:
            child_type = "dir" if len(parts) > 1 else str(metadata.get("type", "dir"))
            child = TreeNode(name=head, node_type=child_type)
            self.children[head] = child

        if len(parts) == 1:
            child.metadata = metadata
            child.node_type = str(metadata.get("type", child.node_type))
            return

        child.add_path(parts[1:], metadata)


@dataclass
class ArchiveSnapshot:
    name: str
    start: str | None
    archive_id: str | None
    hostname: str | None
    username: str | None
    command_line: str | None
    root: TreeNode = field(default_factory=lambda: TreeNode(name=""))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a tree-like metadata view for all archives in a Borg repository."
    )
    parser.add_argument("repository", help="Borg repository path or remote target.")
    parser.add_argument(
        "--glob-archives",
        help="Only include archives matching Borg's glob-archives filter.",
    )
    parser.add_argument("--first", type=int, help="Only inspect the first N matching archives.")
    parser.add_argument("--last", type=int, help="Only inspect the last N matching archives.")
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Limit displayed depth inside each archive tree.",
    )
    parser.add_argument(
        "--metadata",
        choices=("none", "compact", "full"),
        default="compact",
        help="Metadata density for archive and file entries.",
    )
    parser.add_argument(
        "--archives-only",
        action="store_true",
        help="List archive metadata without traversing file trees.",
    )
    parser.add_argument(
        "--include-checkpoints",
        action="store_true",
        help="Include Borg checkpoint archives.",
    )
    parser.add_argument(
        "--show-command-line",
        action="store_true",
        help="Include the archive command line in archive metadata.",
    )
    parser.add_argument(
        "--borg-bin",
        default="borg",
        help="Path to the Borg binary to execute.",
    )
    return parser.parse_args(argv)


def run_borg_json(borg_bin: str, args: list[str]) -> object:
    cmd = [borg_bin, *args]
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"Borg binary not found: {borg_bin}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or "unknown Borg error"
        raise SystemExit(f"Borg command failed: {' '.join(cmd)}\n{stderr}") from exc

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse Borg JSON output from: {' '.join(cmd)}") from exc


def run_borg_json_lines(borg_bin: str, args: list[str]) -> list[dict[str, object]]:
    cmd = [borg_bin, *args]
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"Borg binary not found: {borg_bin}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or "unknown Borg error"
        raise SystemExit(f"Borg command failed: {' '.join(cmd)}\n{stderr}") from exc

    items: list[dict[str, object]] = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Failed to parse Borg JSON lines from: {' '.join(cmd)}") from exc
    return items


def fetch_archives(args: argparse.Namespace) -> list[ArchiveSnapshot]:
    borg_args = ["list", "--json"]
    if args.include_checkpoints:
        borg_args.append("--consider-checkpoints")
    if args.glob_archives:
        borg_args.extend(["--glob-archives", args.glob_archives])
    if args.first is not None:
        borg_args.extend(["--first", str(args.first)])
    if args.last is not None:
        borg_args.extend(["--last", str(args.last)])
    borg_args.append(args.repository)

    payload = run_borg_json(args.borg_bin, borg_args)
    archives = payload.get("archives", []) if isinstance(payload, dict) else []
    snapshots: list[ArchiveSnapshot] = []
    for archive in archives:
        if not isinstance(archive, dict):
            continue
        snapshots.append(
            ArchiveSnapshot(
                name=str(archive.get("archive", "")),
                start=_as_optional_str(archive.get("start") or archive.get("time")),
                archive_id=_as_optional_str(archive.get("id")),
                hostname=_as_optional_str(archive.get("hostname")),
                username=_as_optional_str(archive.get("username")),
                command_line=_as_optional_str(archive.get("command_line")),
            )
        )
    return snapshots


def fetch_archive_items(args: argparse.Namespace, archive_name: str) -> list[dict[str, object]]:
    format_fields = "".join(f"{{{field}}}" for field in DEFAULT_ITEM_FIELDS)
    repo_archive = f"{args.repository}::{archive_name}"
    borg_args = ["list", "--json-lines", "--format", format_fields, repo_archive]
    return run_borg_json_lines(args.borg_bin, borg_args)


def build_archive_tree(snapshot: ArchiveSnapshot, items: Iterable[dict[str, object]]) -> None:
    for item in items:
        path = item.get("path")
        if not isinstance(path, str) or not path:
            continue
        parts = [part for part in path.split("/") if part and part != "."]
        if not parts:
            continue
        snapshot.root.add_path(parts, item)


def format_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def format_size(value: object) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    size = float(value)
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    unit = units[0]
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            break
        size /= 1024.0
    if unit == "B":
        return f"{int(size)}{unit}"
    return f"{size:.1f}{unit}"


def metadata_suffix(node_type: str, metadata: dict[str, object], mode: str) -> str:
    if mode == "none":
        return ""

    parts: list[str] = []
    if mode in {"compact", "full"}:
        type_label = {
            "d": "dir",
            "f": "file",
            "l": "link",
            "h": "hardlink",
        }.get(node_type, node_type)
        parts.append(type_label)

    if mode == "compact":
        size = format_size(metadata.get("size"))
        if size:
            parts.append(size)
        mtime = format_time(_as_optional_str(metadata.get("mtime")))
        if mtime:
            parts.append(mtime)
        return f" [{' | '.join(parts)}]" if parts else ""

    for key in ("mode", "user", "group", "healthy"):
        value = metadata.get(key)
        if value not in (None, ""):
            parts.append(f"{key}={value}")
    size = format_size(metadata.get("size"))
    if size:
        parts.append(f"size={size}")
    mtime = format_time(_as_optional_str(metadata.get("mtime")))
    if mtime:
        parts.append(f"mtime={mtime}")
    return f" [{' | '.join(parts)}]" if parts else ""


def archive_suffix(snapshot: ArchiveSnapshot, mode: str, show_command_line: bool) -> str:
    if mode == "none":
        return ""

    parts: list[str] = []
    if snapshot.start:
        parts.append(format_time(snapshot.start) or snapshot.start)
    if snapshot.hostname:
        parts.append(snapshot.hostname)
    if snapshot.username:
        parts.append(snapshot.username)
    if mode == "full" and snapshot.archive_id:
        parts.append(f"id={snapshot.archive_id[:12]}")
    if show_command_line and snapshot.command_line:
        parts.append(f"cmd={snapshot.command_line}")
    return f" [{' | '.join(parts)}]" if parts else ""


def render_tree(
    node: TreeNode,
    lines: list[str],
    prefix: str,
    max_depth: int | None,
    metadata_mode: str,
    depth: int,
) -> None:
    children = sorted(node.children.values(), key=lambda child: (child.node_type != "d", child.name))
    for index, child in enumerate(children):
        connector = "└── " if index == len(children) - 1 else "├── "
        suffix = metadata_suffix(child.node_type, child.metadata, metadata_mode)
        lines.append(f"{prefix}{connector}{child.name}{suffix}")
        if child.children and (max_depth is None or depth < max_depth):
            extension = "    " if index == len(children) - 1 else "│   "
            render_tree(
                child,
                lines,
                prefix + extension,
                max_depth=max_depth,
                metadata_mode=metadata_mode,
                depth=depth + 1,
            )


def render_output(
    repository: str,
    snapshots: list[ArchiveSnapshot],
    metadata_mode: str,
    max_depth: int | None,
    show_command_line: bool,
    archives_only: bool,
) -> str:
    lines = [repository]
    for index, snapshot in enumerate(snapshots):
        connector = "└── " if index == len(snapshots) - 1 else "├── "
        lines.append(f"{connector}{snapshot.name}{archive_suffix(snapshot, metadata_mode, show_command_line)}")
        if archives_only:
            continue

        archive_lines: list[str] = []
        render_tree(
            snapshot.root,
            archive_lines,
            prefix="    " if index == len(snapshots) - 1 else "│   ",
            max_depth=max_depth,
            metadata_mode=metadata_mode,
            depth=1,
        )
        lines.extend(archive_lines)
    return "\n".join(lines)


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    snapshots = fetch_archives(args)
    if not args.archives_only:
        for snapshot in snapshots:
            items = fetch_archive_items(args, snapshot.name)
            build_archive_tree(snapshot, items)

    output = render_output(
        repository=args.repository,
        snapshots=snapshots,
        metadata_mode=args.metadata,
        max_depth=args.max_depth,
        show_command_line=args.show_command_line,
        archives_only=args.archives_only,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
