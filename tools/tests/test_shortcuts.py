"""Regression tests for context, atomic completion, and formatting boundaries."""

import copy
import json
import shutil
import subprocess
import sys
from unittest.mock import patch

from test_lab import EXERCISE, WorkspaceTest
from lab import exercise, state, workflow
from lab.core import FRAMEWORK, LabError, tree_hash
import format_code


class ShortcutTests(WorkspaceTest):
    def passing(self):
        self.planning()
        self.prepare_mocked()
        self.transition("practicing")
        shutil.copyfile(self.teaching / "reference/src/counter.cpp", self.path / "src/counter.cpp")
        with patch("lab.exercise.run_cpp", self.fake_run):
            return exercise.check(self.root, EXERCISE)

    def bundle(self, report):
        explanation = "learner/artifacts/explanation.txt"
        (self.root / explanation).write_text(
            "My bound must protect both available capacity and demand.\n"
        )
        refs = [explanation, f"evidence/{report['id']}/summary.json"]
        return {
            "schema_version": 1,
            "expected_version": state.load_session(self.root)["version"],
            "review": {
                "schema_version": 1,
                "id": "review-shortcut",
                "exercise_id": EXERCISE,
                "exercise_revision": 1,
                "summary": "Explained the bound.",
                "learner_explanation": "The learner explained both limits.",
                "evidence_refs": refs,
                "next_action": "Test transfer in a different context.",
            },
            "evidence": [
                {
                    "schema_version": 1,
                    "id": "observation-shortcut",
                    "timestamp": "2026-09-05T00:00:00Z",
                    "exercise_id": EXERCISE,
                    "exercise_revision": 1,
                    "skill": "capacity bounds",
                    "observation": "Explained both limits.",
                    "evidence_refs": refs,
                    "hint_level": 1,
                    "teacher_interpretation": "Transfer remains untested.",
                    "confidence": "medium",
                    "supersedes": None,
                }
            ],
        }

    def test_context_reuses_current_pass_and_detects_changed_source(self):
        self.passing()
        before = state.load_session(self.root)
        with patch(
            "lab.exercise.run_cpp", side_effect=AssertionError("Context must not execute tests")
        ):
            data = workflow.context(self.root)
        self.assertTrue(data["check_reusable"])
        self.assertEqual(data["workflow"], "teaching/coach.md")
        self.assertIn("src/counter.cpp", data["exercise"]["editable_source"])
        self.assertNotIn("commands", data["last_report"])
        self.assertEqual(state.load_session(self.root), before)
        with (self.path / "src/counter.cpp").open("a") as stream:
            stream.write("\n// student change\n")
        self.assertFalse(workflow.context(self.root)["check_reusable"])

    def test_context_rejects_diagnostic_and_changed_contract(self):
        self.passing()
        with patch("lab.exercise.run_cpp", self.fake_run):
            diagnostic = exercise.check(self.root, EXERCISE, "debug")
        self.transition("practicing", last_report_id=diagnostic["id"])
        self.assertFalse(workflow.context(self.root)["check_reusable"])
        with (self.path / "README.md").open("a") as stream:
            stream.write("\nChanged contract\n")
        data = workflow.context(self.root)
        self.assertFalse(data["check_reusable"])
        self.assertTrue(data["integrity_issues"])

    def test_finish_is_one_atomic_version_change(self):
        report = self.passing()
        bundle = self.bundle(report)
        with patch("lab.state.commit", wraps=state.commit) as commit:
            result = workflow.finish(self.root, bundle)
        self.assertEqual(commit.call_count, 1)
        self.assertEqual(result["session"]["version"], bundle["expected_version"] + 1)
        self.assertEqual(result["session"]["phase"], "planning")
        self.assertEqual(result["session"]["completed_exercises"][0]["report_id"], report["id"])
        self.assertEqual(state.status(self.root)["integrity_issues"], [])

    def test_finish_rejections_leave_no_partial_review_or_state(self):
        report = self.passing()
        good = self.bundle(report)
        before = tree_hash(self.root / "learner")
        bad_version = copy.deepcopy(good)
        bad_version["expected_version"] -= 1
        bad_refs = copy.deepcopy(good)
        bad_refs["evidence"][0]["evidence_refs"] = ["learner/artifacts/missing.txt"]
        no_explanation = copy.deepcopy(good)
        no_explanation["review"]["evidence_refs"] = [f"evidence/{report['id']}/summary.json"]
        for bundle in [bad_version, bad_refs, no_explanation]:
            with self.assertRaises(LabError):
                workflow.finish(self.root, bundle)
            self.assertEqual(tree_hash(self.root / "learner"), before)
        with (self.path / "src/counter.cpp").open("a") as stream:
            stream.write("\n// changed after check\n")
        with self.assertRaisesRegex(LabError, "changed"):
            workflow.finish(self.root, good)
        self.assertEqual(tree_hash(self.root / "learner"), before)

    def test_plain_practicing_to_planning_cannot_skip_completion(self):
        self.passing()
        with self.assertRaisesRegex(LabError, "completed review"):
            self.transition("planning", current_exercise_id=None, exercise_revision=None)

    def test_prepare_assign_checks_version_then_assigns_only_on_success(self):
        self.transition("planning")
        version = state.load_session(self.root)["version"]
        with patch("lab.exercise.run_cpp", self.fake_run):
            with self.assertRaisesRegex(LabError, "conflict"):
                workflow.prepare_and_assign(self.root, EXERCISE, version - 1)
            self.assertEqual(state.load_session(self.root)["phase"], "planning")
            report = workflow.prepare_and_assign(self.root, EXERCISE, version)
        self.assertEqual(report["outcome"], "ready")
        self.assertEqual(report["session"]["phase"], "practicing")

    def test_prepare_assign_failure_is_blocked_not_practicing(self):
        self.transition("planning")
        result = dict(
            commands=[],
            test_summary={"error": "offline"},
            toolchain={},
            outcome="environment_error",
            exit_status=2,
        )
        with patch("lab.exercise.run_cpp", return_value=result):
            with self.assertRaises(LabError):
                workflow.prepare_and_assign(self.root, EXERCISE, 1)
        self.assertEqual(state.load_session(self.root)["phase"], "blocked")

    def test_resume_clears_pause_metadata_and_keeps_exercise(self):
        self.passing()
        s = state.load_session(self.root)
        workflow.transition(
            self.root, "paused", s["version"], "Resume explanation.", reason="Time limit"
        )
        s = state.load_session(self.root)
        workflow.transition(self.root, "resume", s["version"], "Review the supplied explanation.")
        s = state.load_session(self.root)
        self.assertEqual(s["phase"], "practicing")
        self.assertEqual(s["current_exercise_id"], EXERCISE)
        self.assertIsNone(s["reason"])
        self.assertIsNone(s["resume_phase"])


class FormattingTests(WorkspaceTest):
    def test_history_symlinks_and_published_assets_are_protected(self):
        self.prepare_mocked()
        self.assertTrue(format_code.allowed(self.path / "src/counter.cpp", self.root))
        self.assertFalse(format_code.allowed(self.path / "tests/counter_test.cpp", self.root))
        self.assertFalse(
            format_code.allowed(self.teaching / "reference/src/counter.cpp", self.root)
        )
        history = self.root / "evidence/example.py"
        history.write_text("x=1\n")
        self.assertFalse(format_code.allowed(history, self.root))
        (self.root / "tools").mkdir()
        (self.root / "tools/link.py").symlink_to(history)
        self.assertFalse(format_code.allowed(self.root / "tools/link.py", self.root))

    def test_patch_hook_selects_only_edited_and_moved_files(self):
        event = {
            "tool_name": "apply_patch",
            "cwd": str(self.root),
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: tools/old.py\n*** Move to: tools/new.py\n*** Delete File: tools/delete.py\n*** End Patch"
            },
        }
        self.assertEqual(
            format_code.patch_paths(event), [self.root / "tools/old.py", self.root / "tools/new.py"]
        )
        self.assertEqual(
            format_code.patch_paths({"tool_name": "Bash", "tool_input": {"command": "echo hello"}}),
            [],
        )

    def test_python_formatting_is_idempotent_and_hook_is_silent(self):
        folder = self.root / "tools"
        folder.mkdir()
        source = folder / "example.py"
        source.write_text("def f( x ):\n return x+1\n")
        (self.root / ".venv").symlink_to(FRAMEWORK / ".venv", target_is_directory=True)
        format_code.format_paths([source], root=self.root)
        formatted = source.read_bytes()
        self.assertIn(b"def f(x):", formatted)
        format_code.format_paths([source], root=self.root)
        self.assertEqual(source.read_bytes(), formatted)
        result = subprocess.run(
            [sys.executable, str(FRAMEWORK / "tools/format_code.py"), "--hook"],
            input=json.dumps({"tool_name": "Bash"}),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
