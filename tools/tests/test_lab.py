"""Behavioral checks; real C++ integration is opt-in via LAB_CPP_TESTS=1."""

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab import cli, exercise, runner, state
from lab.core import (
    FRAMEWORK,
    LabError,
    atomic_text,
    json_text,
    read_json,
    tree_hash,
    validate,
    write_json,
    writer,
)

FIXTURE = Path(__file__).parent / "fixtures" / "workspace"
EXERCISE = "counter-fixture"


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="learning-lab-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(FIXTURE, self.root, dirs_exist_ok=True)
        state.init(self.root)
        self.path = self.root / "exercises" / EXERCISE
        self.teaching = self.root / ".instructor" / EXERCISE

    def transition(self, phase, **kwargs):
        session = state.load_session(self.root)
        session.update(phase=phase, version=session["version"] + 1, **kwargs)
        return state.apply(
            self.root,
            {"schema_version": 1, "expected_version": session["version"] - 1, "session": session},
        )

    def planning(self):
        self.transition("planning", next_action="Generate the fixture.")
        self.transition(
            "preparing",
            current_exercise_id=EXERCISE,
            exercise_revision=1,
            next_action="Validate the fixture.",
        )

    @staticmethod
    def fake_run(root, source, spec, report_id, preset):
        # Simulate execution only. Real hashing, publication, transactions, and artifacts still run.
        text = (source / "src/counter.cpp").read_text()
        if "return requested < capacity" in text:
            failed = []
        elif "return requested;" in text:
            failed = ["capacity boundary", "extra capacity combinations"]
        elif "missing_value" in text:
            return {
                "commands": [],
                "test_summary": {"failed": [], "diagnostics": [{"tail": "missing_value"}]},
                "toolchain": {},
                "outcome": "compile_failure",
                "exit_status": 1,
            }
        else:
            failed = ["within capacity", "capacity boundary"]
        return {
            "commands": [],
            "test_summary": {"failed": failed, "total": 6},
            "toolchain": {},
            "outcome": "test_failure" if failed else "passed",
            "exit_status": 1 if failed else 0,
        }

    def prepare_mocked(self):
        with patch("lab.exercise.run_cpp", self.fake_run):
            result = exercise.prepare(self.root, EXERCISE)
        self.assertEqual(result["exit_status"], 0, result)
        return result


class WorkflowTests(WorkspaceTest):
    def test_check_defaults_to_active_exercise_and_accepts_explicit_id(self):
        self.planning()
        with patch("lab.cli.exercise.check", return_value={"exit_status": 0}) as check:
            cli.dispatch(cli.parser().parse_args(["--root", str(self.root), "check"]))
            check.assert_called_once_with(self.root.resolve(), EXERCISE, None)
            check.reset_mock()
            cli.dispatch(
                cli.parser().parse_args(
                    ["--root", str(self.root), "check", "another", "--preset", "debug"]
                )
            )
            check.assert_called_once_with(self.root.resolve(), "another", "debug")

    def test_check_without_active_exercise_has_actionable_error(self):
        with self.assertRaisesRegex(LabError, "No active exercise"):
            cli.dispatch(cli.parser().parse_args(["--root", str(self.root), "check"]))

    def test_compact_status_omits_nested_logs(self):
        report = dict(
            id="run-example",
            outcome="passed",
            exit_status=0,
            exercise_revision=1,
            source_snapshot="evidence/run-example/source",
            commands=["verbose"],
        )
        with patch(
            "lab.cli.state.status",
            return_value={
                "session": state.load_session(self.root),
                "last_report": report,
                "integrity_issues": [],
            },
        ):
            data, code = cli.dispatch(
                cli.parser().parse_args(["--root", str(self.root), "status", "--compact", "--json"])
            )
        self.assertEqual(code, 0)
        self.assertEqual(data["last_report"]["outcome"], "passed")
        self.assertNotIn("commands", data["last_report"])

    def test_preparation_stops_after_first_environment_failure(self):
        self.planning()
        result = dict(
            commands=[],
            test_summary={"error": "offline"},
            toolchain={},
            outcome="environment_error",
            exit_status=2,
        )
        with patch("lab.exercise.run_cpp", return_value=result) as run:
            with self.assertRaisesRegex(LabError, "Preparation stopped.*offline"):
                exercise.prepare(self.root, EXERCISE)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(state.load_session(self.root)["phase"], "blocked")
        self.assertFalse((self.teaching / "ready.json").exists())

    def test_cached_annotated_tag_works_offline_and_rejects_dirty_tree(self):
        checkout = self.root / ".cache/dependencies/Catch2"
        checkout.mkdir(parents=True)

        def git(*args):
            return subprocess.check_output(["git", "-C", str(checkout), *args], text=True).strip()

        git("init", "-q")
        (checkout / "asset.txt").write_text("original")
        git("add", "asset.txt")
        identity = ("-c", "user.name=Lab Test", "-c", "user.email=lab@example.invalid")
        git(*identity, "commit", "-qm", "fixture")
        git(*identity, "tag", "-a", "pinned", "-m", "annotated pin")
        tag = git("rev-parse", "pinned")
        self.assertNotEqual(tag, git("rev-parse", "HEAD"))
        original_execute = runner.execute

        def offline(argv, *args, **kwargs):
            self.assertNotIn("fetch", argv, "Valid annotated-tag cache must not use network")
            return original_execute(argv, *args, **kwargs)

        logs = self.root / "reports/cache-test"
        with (
            patch("lab.runner.CATCH_COMMIT", tag),
            patch("lab.runner.execute", side_effect=offline),
        ):
            self.assertEqual(runner.ensure_catch(self.root, [], logs, 10), checkout.resolve())
            (checkout / "asset.txt").write_text("modified")
            with self.assertRaisesRegex(LabError, "Catch2 preparation failed"):
                runner.ensure_catch(self.root, [], logs, 10)


class StateTests(WorkspaceTest):
    def test_corrupt_journal_is_not_partially_replayed(self):
        before = (self.root / "learner/session.json").read_bytes()
        session = state.load_session(self.root)
        session["version"] = 1
        write_json(
            self.root / "learner/.transaction.json",
            {
                "schema_version": 1,
                "files": {
                    "learner/session.json": json_text(session),
                    "learner/profile.json": "{broken",
                },
            },
        )
        with self.assertRaises(LabError):
            state.recover(self.root)
        self.assertEqual((self.root / "learner/session.json").read_bytes(), before)
        self.assertTrue((self.root / "learner/.transaction.json").exists())

    def test_init_preserves_progress_and_empty_profile(self):
        self.transition("planning")
        before = (self.root / "learner/session.json").read_bytes()
        self.assertEqual(state.init(self.root)["created"], [])
        self.assertEqual((self.root / "learner/session.json").read_bytes(), before)
        self.assertEqual(read_json(self.root / "learner/profile.json")["goals"], [])

    def test_rejects_stale_version_and_invalid_transition(self):
        self.transition("planning")
        with self.assertRaisesRegex(LabError, "conflict"):
            state.apply(self.root, {"schema_version": 1, "expected_version": 0})
        with self.assertRaisesRegex(LabError, "transition"):
            self.transition("reviewing")

    def test_atomic_transaction_recovers_after_partial_write(self):
        current = state.load_session(self.root)
        current.update(version=1, phase="planning", next_action="Continue after recovery.")
        changes = {"learner/session.json": json_text(current), "learner/evidence.jsonl": ""}
        with patch("lab.state.atomic_text", side_effect=OSError("simulated interrupted write")):
            with self.assertRaises(OSError):
                state.commit(self.root, changes)
        with writer(self.root):
            self.assertTrue(state.recover(self.root))
        self.assertEqual(state.load_session(self.root), current)
        self.assertFalse(state.recover(self.root))

    def test_lock_rejects_a_second_process(self):
        script = "from pathlib import Path; from lab.core import writer;\nwith writer(Path(__import__('sys').argv[1])): pass"
        env = dict(os.environ, PYTHONPATH=str(FRAMEWORK / "tools"))
        with writer(self.root):
            result = subprocess.run(
                [sys.executable, "-c", script, str(self.root)],
                env=env,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Another lab writer", result.stderr)

    def test_pause_resume_and_ready_gate(self):
        self.planning()
        with self.assertRaises(LabError):
            self.transition("practicing")
        self.prepare_mocked()
        self.transition("practicing")
        self.transition("paused", resume_phase="practicing", reason="End of session")
        self.transition("practicing", resume_phase=None, reason=None)

    def test_ephemeral_or_missing_evidence_is_rejected(self):
        for reference in [
            "reports/deleted.log",
            "learner/artifacts/missing.txt",
            "evidence/../outside.txt",
        ]:
            with self.assertRaises(LabError):
                state.verify_refs(self.root, [reference])

    def test_unknown_schema_fields_are_rejected(self):
        value = state.load_session(self.root)
        value["mastered"] = True
        with self.assertRaisesRegex(LabError, "Additional properties"):
            validate("session", value)


class PublicationTests(WorkspaceTest):
    def test_missing_assets_block_the_active_preparation(self):
        self.planning()
        (self.teaching / "validation.json").unlink()
        with self.assertRaises(LabError):
            exercise.prepare(self.root, EXERCISE)
        session = state.load_session(self.root)
        self.assertEqual(session["phase"], "blocked")
        self.assertIn("validation.json", session["reason"])

    def test_templates_require_explicit_semantic_approval(self):
        for name in ["implementation", "debugging"]:
            value = read_json(FRAMEWORK / "templates" / name / "instructor/validation.json")
            with self.assertRaises(LabError):
                validate("validation", value)

    def test_changed_student_during_snapshot_is_not_reported_as_current(self):
        self.prepare_mocked()
        original_copy = exercise.copy_tree

        def changing_copy(source, destination):
            original_copy(source, destination)
            atomic_text(
                source / "src/counter.cpp",
                (self.teaching / "reference/src/counter.cpp").read_text(),
            )

        with (
            patch("lab.exercise.copy_tree", changing_copy),
            patch("lab.exercise.run_cpp", self.fake_run),
        ):
            report = exercise.check(self.root, EXERCISE, "debug")
        self.assertEqual(report["exit_status"], 2)
        self.assertEqual(report["outcome"], "source_changed_during_check")

    def test_completed_snapshot_can_be_checked_after_live_revision_changes(self):
        self.prepare_mocked()
        shutil.copyfile(self.teaching / "reference/src/counter.cpp", self.path / "src/counter.cpp")
        with patch("lab.exercise.run_cpp", self.fake_run):
            passing = exercise.check(self.root, EXERCISE)
        item = {"id": EXERCISE, "revision": 1, "report_id": passing["id"]}
        spec = read_json(self.path / "spec.json")
        spec["revision"] = 2
        write_json(self.path / "spec.json", spec)
        atomic_text(self.path / "src/counter.cpp", "// new incomplete attempt\n")
        with patch("lab.exercise.run_cpp", self.fake_run):
            result = exercise.check_completed(self.root, item)
        self.assertEqual(result["exit_status"], 0)
        for report_id in result["report_ids"]:
            self.assertEqual(state.report_for(self.root, report_id)["exercise_revision"], 1)

    def test_status_finds_missing_source_behind_a_retained_summary(self):
        self.planning()
        self.prepare_mocked()
        self.transition("practicing")
        with patch("lab.exercise.run_cpp", self.fake_run):
            report = exercise.check(self.root, EXERCISE)
        (self.root / report["source_snapshot"] / "src/counter.cpp").unlink()
        self.assertTrue(state.status(self.root)["integrity_issues"])

    def test_completed_recheck_never_executes_inside_original_evidence(self):
        self.prepare_mocked()
        shutil.copyfile(self.teaching / "reference/src/counter.cpp", self.path / "src/counter.cpp")
        with patch("lab.exercise.run_cpp", self.fake_run):
            passing = exercise.check(self.root, EXERCISE)
        original = self.root / passing["source_snapshot"]
        original_hash = tree_hash(original)

        def mutating_test(root, source, spec, report_id, preset):
            self.assertNotEqual(source, original)
            result = self.fake_run(root, source, spec, report_id, preset)
            atomic_text(source / "test-created-file.txt", "unexpected test side effect\n")
            return result

        with patch("lab.exercise.run_cpp", mutating_test):
            result = exercise.check_completed(
                self.root, {"id": EXERCISE, "revision": 1, "report_id": passing["id"]}
            )
        self.assertEqual(result["exit_status"], 2)
        self.assertEqual(tree_hash(original), original_hash)

    def test_ready_binds_contract_but_allows_student_edits(self):
        self.prepare_mocked()
        original = tree_hash(self.path)
        atomic_text(
            self.path / "src/counter.cpp", (self.teaching / "reference/src/counter.cpp").read_text()
        )
        self.assertNotEqual(original, tree_hash(self.path))
        exercise.require_ready(self.root, EXERCISE)
        atomic_text(self.path / "tests/counter_test.cpp", "// Changed acceptance contract\n")
        with self.assertRaisesRegex(LabError, "contract changed"):
            exercise.require_ready(self.root, EXERCISE)
        with self.assertRaisesRegex(LabError, "new revision"):
            exercise.prepare(self.root, EXERCISE)

    def test_prepare_never_overwrites_student_work(self):
        atomic_text(self.path / "src/counter.cpp", "// My unfinished work\n")
        before = tree_hash(self.path)
        self.prepare_mocked()
        self.prepare_mocked()
        self.assertEqual(tree_hash(self.path), before)

    def test_wrong_mutant_failure_blocks_publication(self):
        self.planning()

        def wrong_failure(root, source, spec, report_id, preset):
            result = self.fake_run(root, source, spec, report_id, preset)
            if "return requested;" in (source / "src/counter.cpp").read_text():
                result.update(outcome="compile_failure", exit_status=1)
            return result

        with patch("lab.exercise.run_cpp", wrong_failure):
            report = exercise.prepare(self.root, EXERCISE)
        self.assertEqual(report["exit_status"], 2)
        self.assertFalse((self.teaching / "ready.json").exists())
        self.assertEqual(state.load_session(self.root)["phase"], "blocked")
        self.assertEqual(state.read_evidence(self.root), [])

    def test_missing_file_or_escaping_path_rejected(self):
        with self.assertRaises(LabError):
            exercise.load_exercise(self.root, "../counter-fixture")
        (self.path / "src/counter.cpp").unlink()
        with self.assertRaisesRegex(LabError, "Missing exercise file"):
            exercise.prepare(self.root, EXERCISE)

    def test_symlink_rejected(self):
        (self.path / "escape").symlink_to(self.root / "learner/profile.json")
        with self.assertRaisesRegex(LabError, "Symlink"):
            exercise.load_exercise(self.root, EXERCISE)

    def test_removed_validation_snapshot_invalidates_ready(self):
        report = self.prepare_mocked()
        child = state.report_for(self.root, report["child_reports"][0])
        (self.root / child["source_snapshot"] / "src/counter.cpp").unlink()
        with self.assertRaisesRegex(LabError, "snapshot"):
            exercise.require_ready(self.root, EXERCISE)

    def test_student_failure_does_not_change_phase_or_source(self):
        self.planning()
        self.prepare_mocked()
        self.transition("practicing")
        before = tree_hash(self.path)
        with patch("lab.exercise.run_cpp", self.fake_run):
            report = exercise.check(self.root, EXERCISE)
        self.assertEqual(report["exit_status"], 1)
        self.assertEqual(tree_hash(self.path), before)
        self.assertEqual(state.load_session(self.root)["phase"], "practicing")
        self.assertEqual(state.load_session(self.root)["last_report_id"], report["id"])
        self.assertEqual(state.read_evidence(self.root), [])

    def test_diagnostic_profile_does_not_qualify_for_completion(self):
        self.planning()
        self.prepare_mocked()
        self.transition("practicing")
        with patch("lab.exercise.run_cpp", self.fake_run):
            exercise.check(self.root, EXERCISE, "debug")
        self.assertIsNone(state.load_session(self.root)["last_report_id"])


class ProcessTests(unittest.TestCase):
    def test_zero_discovered_tests_are_never_success(self):
        spec = read_json(FIXTURE / "exercises/counter-fixture/spec.json")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def successful_process(argv, log, timeout=120, cwd=None):
                atomic_text(
                    log, '{"tests": []}' if "--show-only=json-v1" in argv else "fixture compiler\n"
                )
                return {
                    "argv": list(map(str, argv)),
                    "exit_status": 0,
                    "duration": 0.0,
                    "log": str(log),
                    "timed_out": False,
                }

            with (
                patch("lab.runner.execute", successful_process),
                patch(
                    "lab.runner.probe",
                    return_value={"supported": True, "detail": "fixture library"},
                ),
                patch("lab.runner.ensure_catch", return_value=root),
                patch("lab.runner.compiler", return_value="fixture-compiler"),
            ):
                report = runner.run_cpp(root, root, spec, "test-run", "debug")
        self.assertEqual(report["exit_status"], 2)
        self.assertEqual(report["outcome"], "discovery_error")

    def test_required_sanitizer_unavailable_is_not_skipped(self):
        spec = read_json(FIXTURE / "exercises/counter-fixture/spec.json")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def version_process(argv, log, timeout=120, cwd=None):
                atomic_text(log, "fixture compiler\n")
                return {
                    "argv": list(map(str, argv)),
                    "exit_status": 0,
                    "duration": 0.0,
                    "log": str(log),
                    "timed_out": False,
                }

            with (
                patch(
                    "lab.runner.probe",
                    return_value={"supported": False, "detail": "runtime unavailable"},
                ),
                patch("lab.runner.compiler", return_value="fixture-compiler"),
                patch("lab.runner.execute", version_process),
            ):
                report = runner.run_cpp(root, root, spec, "test-run", "asan")
        self.assertEqual(report["exit_status"], 2)
        self.assertEqual(report["outcome"], "environment_error")

    def test_timeout_stops_a_process_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = runner.execute(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                Path(temporary) / "timeout.log",
                timeout=0.1,
            )
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["exit_status"], 124)

    def test_missing_executable_is_an_environment_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = runner.execute(["/nonexistent/lab-compiler"], Path(temporary) / "missing.log")
        self.assertEqual(result["exit_status"], 127)

    def test_json_errors_use_stable_exit_code(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()) as output:
            result = cli.main(["--root", temporary, "status", "--json"])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(output.getvalue())["exit_code"], 2)


@unittest.skipUnless(
    os.environ.get("LAB_CPP_TESTS") == "1", "Set LAB_CPP_TESTS=1 for real C++ integration"
)
class CppIntegrationTests(WorkspaceTest):
    def test_completed_snapshot_real_recheck(self):
        self.prepare_mocked()
        shutil.copyfile(self.teaching / "reference/src/counter.cpp", self.path / "src/counter.cpp")
        with patch("lab.exercise.run_cpp", self.fake_run):
            original = exercise.check(self.root, EXERCISE)
        # Recheck runs real CMake/Catch2 from a copy of the recorded version.
        atomic_text(
            self.path / "src/counter.cpp",
            "// The live workspace is now an unrelated unfinished revision.\n",
        )
        result = exercise.check_completed(
            self.root, {"id": EXERCISE, "revision": 1, "report_id": original["id"]}
        )
        self.assertEqual(result["exit_status"], 0, result)
        for report_id in result["report_ids"]:
            report = state.report_for(self.root, report_id)
            self.assertNotEqual(report["source_snapshot"], original["source_snapshot"])
            self.assertEqual(report["source_hash"], original["source_hash"])

    def test_debugging_compile_failure_skeleton(self):
        spec = read_json(self.path / "spec.json")
        spec.update(template="debugging", sanitizers=[], seeds=[17])
        write_json(self.path / "spec.json", spec, "exercise")
        broken = '#include "counter.hpp"\nstd::size_t admit(std::size_t, std::size_t) { return missing_value; }\n'
        atomic_text(self.path / "src/counter.cpp", broken)
        atomic_text(self.teaching / "skeleton/src/counter.cpp", broken)
        instructions = read_json(self.teaching / "validation.json")
        instructions["skeleton_expectation"] = {
            "kind": "compile_failure",
            "checks": [],
            "diagnostic": "missing_value",
        }
        write_json(self.teaching / "validation.json", instructions, "validation")
        self.planning()
        ready = exercise.prepare(self.root, EXERCISE)
        self.assertEqual(ready["exit_status"], 0, ready)
        self.transition("practicing")
        original = tree_hash(self.path)
        report = exercise.check(self.root, EXERCISE)
        self.assertEqual(report["exit_status"], 1, report)
        self.assertEqual(report["test_summary"]["runs"][0]["outcome"], "compile_failure")
        self.assertEqual(tree_hash(self.path), original)

    def test_complete_learning_loop_and_restart(self):
        self.planning()
        report = exercise.prepare(self.root, EXERCISE)
        self.assertEqual(report["exit_status"], 0, report)
        self.transition("practicing", next_action="Implement the capacity bound.")
        original = tree_hash(self.path)
        failed = exercise.check(self.root, EXERCISE)
        self.assertEqual(failed["exit_status"], 1, failed)
        self.assertEqual(tree_hash(self.path), original)
        self.assertEqual(state.load_session(self.root)["phase"], "practicing")
        hint = {
            "schema_version": 1,
            "id": "hint-1",
            "timestamp": "2026-09-05T00:00:00Z",
            "exercise_id": EXERCISE,
            "exercise_revision": 1,
            "skill": "capacity bounds",
            "observation": "The learner used an always-zero placeholder.",
            "evidence_refs": [f"evidence/{failed['id']}/summary.json"],
            "hint_level": 1,
            "teacher_interpretation": "Ask the learner to predict admit(3, 5).",
            "confidence": "low",
            "supersedes": None,
        }
        state.apply(
            self.root,
            {
                "schema_version": 1,
                "expected_version": state.load_session(self.root)["version"],
                "evidence": [hint],
            },
        )
        # This isolated fixture simulates a student's edit; it never changes a real learner's files.
        shutil.copyfile(self.teaching / "reference/src/counter.cpp", self.path / "src/counter.cpp")
        passing = exercise.check(self.root, EXERCISE)
        self.assertEqual(passing["exit_status"], 0, passing)
        self.transition("reviewing", next_action="Explain the bound.")
        explanation = self.root / "learner/artifacts/explanation.txt"
        atomic_text(explanation, "The accepted count cannot exceed either demand or capacity.\n")
        review = {
            "schema_version": 1,
            "id": "review-1",
            "exercise_id": EXERCISE,
            "exercise_revision": 1,
            "summary": "Completed with a level-one hint; transfer is untested.",
            "learner_explanation": explanation.read_text(),
            "evidence_refs": [
                "learner/artifacts/explanation.txt",
                f"evidence/{passing['id']}/summary.json",
            ],
            "next_action": "Choose a new context with less assistance.",
        }
        session = state.load_session(self.root)
        expected_version = session["version"]
        session.update(
            version=expected_version + 1,
            phase="planning",
            current_exercise_id=None,
            exercise_revision=None,
            next_action=review["next_action"],
            completed_exercises=[{"id": EXERCISE, "revision": 1, "report_id": passing["id"]}],
        )
        state.apply(
            self.root,
            {
                "schema_version": 1,
                "expected_version": expected_version,
                "session": session,
                "reviews": [review],
            },
        )
        shutil.rmtree(self.root / "reports")
        result = subprocess.run(
            [
                sys.executable,
                str(FRAMEWORK / "tools/lab.py"),
                "--root",
                str(self.root),
                "status",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        restored = json.loads(result.stdout)["data"]
        self.assertEqual(restored["session"]["next_action"], review["next_action"])
        self.assertEqual(restored["integrity_issues"], [])
        self.assertEqual(len(state.read_evidence(self.root)), 1)


if __name__ == "__main__":
    unittest.main()
