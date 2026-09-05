#!/usr/bin/env python3
"""Local formatting only: no model calls, lint fixes, or history rewrites."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUFFIXES = {".py", ".cpp", ".hpp", ".h", ".cc", ".cxx"}


def allowed(path, root=ROOT):
    """Formatting is never permission to mutate evidence or a published contract."""
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    if path.is_symlink():
        return False
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        return False
    relative = resolved.relative_to(root.resolve())
    if any((root / Path(*relative.parts[:n])).is_symlink() for n in range(1, len(relative.parts))):
        return False
    if resolved.suffix not in SUFFIXES or relative.parts[0] not in {
        "tools",
        "templates",
        "exercises",
        ".instructor",
    }:
        return False
    if any(
        part in {"__pycache__", ".venv", "build", "evidence", "reports", ".cache"}
        for part in relative.parts
    ):
        return False
    if relative.parts[0] in {"exercises", ".instructor"}:
        if len(relative.parts) < 3:
            return False
        exercise_id = relative.parts[1]
        if relative.parts[0] == ".instructor":
            return not (root / ".instructor" / exercise_id / "ready.json").exists()
        spec_path = root / "exercises" / exercise_id / "spec.json"
        if not spec_path.exists():
            return False
        spec = json.loads(spec_path.read_text())
        editable = Path(*relative.parts[2:]).as_posix() in spec["editable_paths"]
        return editable or not (root / ".instructor" / exercise_id / "ready.json").exists()
    return True


def patch_paths(event):
    if event.get("tool_name") != "apply_patch":
        return []
    tool_input = event.get("tool_input", {})
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    cwd = Path(event.get("cwd", ROOT))
    paths = []
    for line in command.splitlines():
        for prefix in ("*** Add File: ", "*** Update File: ", "*** Move to: "):
            if line.startswith(prefix):
                path = Path(line[len(prefix) :])
                paths.append(path if path.is_absolute() else cwd / path)
    return paths


def format_paths(paths, check=False, root=ROOT):
    selected = sorted({Path(p).resolve() for p in paths if allowed(p, root)})
    python = [str(p) for p in selected if p.suffix == ".py"]
    cpp = [str(p) for p in selected if p.suffix != ".py"]
    commands = []
    if python:
        ruff = root / ".venv/bin/ruff"
        if not ruff.is_file():
            raise RuntimeError("Ruff is missing; run uv sync --frozen")
        # stdin mode allows explicitly authorized exercise Python files despite
        # the broad safety exclusions used by the repository-wide Ruff check.
        for filename in python:
            source = Path(filename).read_bytes()
            result = subprocess.run(
                [str(ruff), "format", "--no-force-exclude", "--stdin-filename", filename, "-"],
                input=source,
                capture_output=True,
                cwd=root,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.decode(errors="replace")[-2000:])
            if result.stdout != source:
                if check:
                    raise RuntimeError(f"Needs formatting: {Path(filename).relative_to(root)}")
                # Do not overwrite a concurrent editor save.
                if Path(filename).read_bytes() != source:
                    raise RuntimeError(f"File changed during formatting: {filename}")
                Path(filename).write_bytes(result.stdout)
    if cpp:
        executable = shutil.which("clang-format")
        if not executable:
            candidate = Path("/opt/homebrew/opt/llvm/bin/clang-format")
            executable = str(candidate) if candidate.is_file() else None
        if not executable:
            raise RuntimeError("clang-format is missing; install LLVM or put clang-format on PATH")
        commands.append([executable, *(["--dry-run", "--Werror"] if check else ["-i"]), *cpp])
    for command in commands:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr[-2000:])
    return len(selected)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*", type=Path, help="Explicit files; default: framework Python only"
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--hook",
        action="store_true",
        help="Read a Codex PostToolUse event from stdin; silent on success",
    )
    args = parser.parse_args(argv)
    try:
        if args.hook:
            event = json.load(sys.stdin)
            paths = patch_paths(event)
        else:
            paths = args.paths or list((ROOT / "tools").rglob("*.py"))
            rejected = [str(p) for p in paths if not allowed(p)]
            if rejected:
                raise RuntimeError(
                    "Refusing unsupported, missing, or protected paths: " + ", ".join(rejected)
                )
        count = format_paths(paths, check=args.check)
        if not args.hook:
            print(f"Formatting {'checked' if args.check else 'applied'}: {count} file(s)")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        if args.hook:
            print(json.dumps({"systemMessage": f"Local formatting failed: {exc}"}))
        else:
            print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
