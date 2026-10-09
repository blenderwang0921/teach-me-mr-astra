"""Behavior of the derived current/ workspace shortcut; no C++ execution."""

import json
from pathlib import Path
import shutil
from unittest.mock import patch

from test_lab import EXERCISE, WorkspaceTest
from lab import cli, current, state
from lab.core import LabError, json_text, write_json


class CurrentTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.root = self.root.resolve()
        self.path = self.path.resolve()
        self.teaching = self.teaching.resolve()

    def command(self, *args):
        return cli.dispatch(cli.parser().parse_args(["--root", str(self.root), *args]))

    def test_new_workspace_has_no_shortcut(self):
        data, code = self.command("init")
        self.assertEqual(code, 0)
        self.assertIsNone(data["current_workspace"])
        self.assertFalse((self.root / "current").is_symlink())

    def test_context_repairs_link_without_validation_or_state_changes(self):
        self.planning()
        before = (self.root / "learner/session.json").read_bytes()
        with patch("lab.exercise.run_cpp", side_effect=AssertionError("No builds")):
            data, _ = self.command("context")
        link = self.root / "current"
        self.assertEqual(link.readlink(), Path("exercises") / EXERCISE)
        self.assertTrue(data["current_workspace"]["active"])
        source = link / "src/counter.cpp"
        self.assertTrue(source.samefile(self.path / "src/counter.cpp"))
        source.write_text("// edited through current\n")
        self.assertEqual((self.path / "src/counter.cpp").read_text(), "// edited through current\n")
        link.unlink()
        link.symlink_to("exercises/missing")
        self.command("status", "--compact")
        self.assertEqual(link.resolve(), self.path)
        self.assertEqual((self.root / "learner/session.json").read_bytes(), before)

    def test_switch_pause_and_resume(self):
        self.planning()
        self.command("status")
        other = "second-fixture"
        destination = self.root / "exercises" / other
        shutil.copytree(self.path, destination)
        spec = json.loads((destination / "spec.json").read_text())
        spec["id"] = other
        write_json(destination / "spec.json", spec)
        version = state.load_session(self.root)["version"]
        self.command(
            "session",
            "preparing",
            "--exercise",
            other,
            "--expected-version",
            str(version),
            "--next-action",
            "Prepare.",
        )
        self.assertEqual((self.root / "current").resolve(), destination)
        version = state.load_session(self.root)["version"]
        self.command(
            "session",
            "paused",
            "--reason",
            "Break.",
            "--expected-version",
            str(version),
            "--next-action",
            "Resume.",
        )
        self.assertEqual((self.root / "current").resolve(), destination)
        version = state.load_session(self.root)["version"]
        self.command(
            "session", "resume", "--expected-version", str(version), "--next-action", "Prepare."
        )
        self.assertEqual((self.root / "current").resolve(), destination)

    def test_completed_exercise_is_rebuilt_for_review(self):
        session = state.load_session(self.root)
        session["completed_exercises"] = [{"id": EXERCISE, "revision": 1, "report_id": "run-test"}]
        write_json(self.root / "learner/session.json", session)
        data, _ = self.command("status")
        self.assertFalse(data["current_workspace"]["active"])
        self.assertEqual((self.root / "current").resolve(), self.path)

    def test_recovery_rebuilds_shortcut(self):
        self.planning()
        session = state.load_session(self.root)
        write_json(
            self.root / "learner/.transaction.json",
            {"schema_version": 1, "files": {"learner/session.json": json_text(session)}},
        )
        data, _ = self.command("status")
        self.assertTrue(data["recovered_transaction"])
        self.assertEqual((self.root / "current").resolve(), self.path)

    def test_conflicting_real_paths_are_preserved(self):
        self.planning()
        link = self.root / "current"
        link.write_text("keep me")
        with self.assertRaisesRegex(LabError, "existing file or directory"):
            self.command("status")
        self.assertEqual(link.read_text(), "keep me")
        link.unlink()
        link.mkdir()
        (link / "keep.txt").write_text("keep me")
        with self.assertRaisesRegex(LabError, "existing file or directory"):
            self.command("status")
        self.assertEqual((link / "keep.txt").read_text(), "keep me")

    def test_missing_or_symlinked_target_is_rejected(self):
        self.planning()
        shutil.rmtree(self.path)
        with self.assertRaisesRegex(LabError, "missing exercise directory"):
            current.sync(self.root)
        self.assertFalse((self.root / "current").is_symlink())
        self.path.symlink_to(self.root / "learner", target_is_directory=True)
        with self.assertRaisesRegex(LabError, "Symlink is not allowed"):
            current.sync(self.root)

    def test_link_is_relative_and_survives_workspace_move(self):
        self.planning()
        self.command("status")
        moved = self.root / "moved"
        moved.mkdir()
        (self.root / "current").rename(moved / "current")
        (self.root / "exercises").rename(moved / "exercises")
        self.assertTrue((moved / "current/README.md").is_file())

    def test_stale_validation_does_not_prevent_shortcut_repair(self):
        self.planning()
        self.prepare_mocked()
        self.transition("practicing")
        with (self.path / "README.md").open("a") as stream:
            stream.write("\nChanged contract\n")
        data, code = self.command("context")
        self.assertEqual(code, 2)
        self.assertTrue(data["integrity_issues"])
        self.assertEqual((self.root / "current").resolve(), self.path)
