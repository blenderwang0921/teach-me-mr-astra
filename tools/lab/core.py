"""Validated files, contained paths, immutable evidence, and writer coordination."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

FRAMEWORK = Path(__file__).resolve().parents[2]


class LabError(Exception):
    """An actionable configuration, environment, or integrity failure."""


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(prefix="run"):
    return f"{prefix}-{uuid.uuid4().hex}"


def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", value):
        raise LabError(f"Invalid identifier: {value!r}")
    return value


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise LabError(f"Cannot read JSON {path}: {exc}") from exc


def validate(kind, value):
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as exc:
        raise LabError("Missing jsonschema; run uv sync --frozen and use .venv/bin/python") from exc
    registry = Registry()
    for path in (FRAMEWORK / "schemas").glob("*.schema.json"):
        schema = read_json(path)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    schema = read_json(FRAMEWORK / "schemas" / f"{kind}.schema.json")
    errors = sorted(Draft202012Validator(schema, registry=registry).iter_errors(value), key=str)
    if errors:
        error = errors[0]
        location = ".".join(map(str, error.absolute_path)) or "<root>"
        raise LabError(f"Invalid {kind} at {location}: {error.message}")
    return value


def contained(root, relative):
    """Reject absolute paths, traversal, and symlinks (including dangling ones)."""
    root = Path(root).resolve()
    part = Path(relative)
    if not relative or part.is_absolute() or ".." in part.parts or str(part) == ".":
        raise LabError(f"Expected a relative file path: {relative!r}")
    candidate = root
    for component in part.parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise LabError(f"Symlink is not allowed: {candidate}")
    if not candidate.resolve().is_relative_to(root):
        raise LabError(f"Path escapes workspace: {relative}")
    return candidate


def files(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise LabError(f"Expected a real directory: {root}")
    result = []
    for path in sorted(root.rglob("*")):
        contained(root, path.relative_to(root).as_posix())
        if path.is_file():
            result.append(path)
    return result


def digest(items):
    hasher = hashlib.sha256()
    for name, data in sorted(items):
        hasher.update(name.encode() + b"\0" + len(data).to_bytes(8, "big") + data)
    return hasher.hexdigest()


def tree_hash(root):
    return digest((p.relative_to(root).as_posix(), p.read_bytes()) for p in files(root))


def atomic_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def json_text(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def write_json(path, value, kind=None):
    if kind:
        validate(kind, value)
    atomic_text(path, json_text(value))


@contextmanager
def writer(root):
    """OS-held lock: crashes release it; the lock file itself can remain."""
    path = contained(root, "learner/.write.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LabError("Another lab writer is active; retry when it finishes") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)

