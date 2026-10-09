"""Rebuild the local current/ shortcut from authoritative session state."""

from pathlib import Path
import tempfile

from .core import LabError, contained, valid_id
from .state import load_session


def sync(root):
    """Called under the CLI writer lock; never change session or exercise files."""
    root = Path(root).resolve()
    session = load_session(root)
    exercise_id = session["current_exercise_id"]
    if not exercise_id and session["completed_exercises"]:
        exercise_id = session["completed_exercises"][-1]["id"]
    link = root / "current"
    if link.exists() and not link.is_symlink():
        raise LabError("Cannot update current/: an existing file or directory must be moved first")
    if not exercise_id:
        if link.is_symlink():
            link.unlink()
        return None
    valid_id(exercise_id)
    relative = Path("exercises") / exercise_id
    target = contained(root, relative.as_posix())
    if not target.is_dir():
        raise LabError(f"Cannot update current/: missing exercise directory {relative}")
    if not link.is_symlink() or link.readlink() != relative:
        with tempfile.TemporaryDirectory(prefix=".current-", dir=root) as temporary:
            replacement = Path(temporary) / "link"
            replacement.symlink_to(relative, target_is_directory=True)
            replacement.replace(link)
    return {
        "path": str(link),
        "target": relative.as_posix(),
        "active": bool(session["current_exercise_id"]),
    }
