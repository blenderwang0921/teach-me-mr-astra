"""Exercise contracts, isolated variants, publication gates, and student checks."""

from __future__ import annotations

from pathlib import Path
import shutil
import time

from .core import (
    FRAMEWORK,
    LabError,
    contained,
    digest,
    files,
    identifier,
    now,
    read_json,
    tree_hash,
    valid_id,
    validate,
    write_json,
)
from .runner import run_cpp


def load_exercise(root, exercise_id):
    valid_id(exercise_id)
    path = contained(root, f"exercises/{exercise_id}")
    spec = validate("exercise", read_json(path / "spec.json"))
    if spec["id"] != exercise_id:
        raise LabError("Exercise directory and spec identifier do not match")
    editable, provided = set(spec["editable_paths"]), set(spec["provided_paths"])
    if editable & provided:
        raise LabError("Editable and provided paths must not overlap")
    for relative in editable | provided:
        candidate = contained(path, relative)
        if not candidate.is_file():
            raise LabError(f"Missing exercise file: {candidate}; generate it before prepare")
    if not {"README.md", "spec.json"} <= provided:
        raise LabError("provided_paths must include README.md and spec.json")
    actual = {p.relative_to(path).as_posix() for p in files(path)}
    if actual != editable | provided:
        raise LabError(
            f"Declare every exercise file in editable_paths/provided_paths: {sorted(actual ^ (editable | provided))}"
        )
    if any(
        not (name == "design.md" or name.startswith(("src/", "include/", "experiments/")))
        for name in editable
    ):
        raise LabError(
            "Editable paths must be implementation, design, or experiment files; tests and spec are provided"
        )
    checks = spec["acceptance_checks"]
    if len({c["id"] for c in checks}) != len(checks) or len(
        {c["test_name"] for c in checks}
    ) != len(checks):
        raise LabError("Acceptance check identifiers and test names must be unique")
    if any(c["requirement"] not in spec["requirements"] for c in checks):
        raise LabError("Acceptance checks must reference an exact requirement")
    if spec["material_ref"] is not None:
        raise LabError(
            "Upstream material execution is deferred; use a self-contained exercise with material_ref=null"
        )
    return path, spec


def instructor(root, exercise_id):
    return contained(root, f".instructor/{exercise_id}")


def contract_hash(root, exercise_id):
    path, spec = load_exercise(root, exercise_id)
    items = [
        (f"exercise/{name}", contained(path, name).read_bytes()) for name in spec["provided_paths"]
    ]
    teaching = instructor(root, exercise_id)
    items.extend(
        (f"instructor/{p.relative_to(teaching).as_posix()}", p.read_bytes())
        for p in files(teaching)
        if p.relative_to(teaching).as_posix() != "ready.json"
    )
    for relative in [
        "CMakeLists.txt",
        "CMakePresets.json",
        "cmake/LabExercise.cmake",
        "pyproject.toml",
        "uv.lock",
    ]:
        items.append((f"framework/{relative}", (FRAMEWORK / relative).read_bytes()))
    for directory in ["tools/lab", "schemas"]:
        items.extend(
            (f"framework/{p.relative_to(FRAMEWORK).as_posix()}", p.read_bytes())
            for p in files(FRAMEWORK / directory)
            if "__pycache__" not in p.parts
        )
    return digest(items)


def require_ready(root, exercise_id, revision=None):
    path, spec = load_exercise(root, exercise_id)
    marker = validate("ready", read_json(instructor(root, exercise_id) / "ready.json"))
    if (marker["exercise_id"], marker["revision"]) != (exercise_id, spec["revision"]):
        raise LabError("Ready marker does not match the exercise revision; run prepare")
    if revision is not None and revision != spec["revision"]:
        raise LabError("Session revision differs from the exercise; revise the session explicitly")
    if marker["contract_hash"] != contract_hash(root, exercise_id):
        raise LabError(
            "Exercise contract changed; increment revision and run prepare before practicing"
        )
    from .state import report_for

    report = report_for(root, marker["report_id"])
    if (
        report["target_kind"] != "validation"
        or report["exit_status"] != 0
        or report["contract_hash"] != marker["contract_hash"]
        or report["exercise_id"] != exercise_id
        or report["exercise_revision"] != spec["revision"]
    ):
        raise LabError("Ready marker lacks a matching successful validation report")
    for child_id in report["child_reports"]:
        child = report_for(root, child_id)
        snapshot = contained(root, child["source_snapshot"] or "missing")
        if tree_hash(snapshot) != child["source_hash"]:
            raise LabError(f"Validation evidence snapshot is missing or changed: {child_id}")
    return path, spec, marker


def copy_tree(source, destination):
    destination.mkdir(parents=True, exist_ok=False)
    for path in files(source):
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def overlay(source, destination, editable):
    actual = {p.relative_to(source).as_posix() for p in files(source)}
    if actual != set(editable):
        raise LabError(
            f"Variant must supply exactly editable_paths: {source}; difference {sorted(actual ^ set(editable))}"
        )
    for name in editable:
        shutil.copyfile(contained(source, name), contained(destination, name))


def new_report(spec, kind, contract, preset):
    return {
        "schema_version": 1,
        "id": identifier(),
        "timestamp": now(),
        "exercise_id": spec["id"],
        "exercise_revision": spec["revision"],
        "source_hash": contract,
        "contract_hash": contract,
        "target_kind": kind,
        "toolchain": {},
        "commands": [],
        "exit_status": 2,
        "test_summary": {},
        "seeds": spec["seeds"],
        "failure_artifacts": [],
        "duration": 0.0,
        "sanitizer": preset,
        "usage_if_available": None,
        "outcome": "incomplete",
        "source_snapshot": None,
        "student_source_hash": None,
        "child_reports": [],
    }


def save_report(root, report):
    write_json(contained(root, f"evidence/{report['id']}/summary.json"), report, "report")
    return report


def run_variant(root, path, spec, contract, kind, preset="debug", variant=None, extra_tests=False):
    report = new_report(spec, kind, contract, preset)
    start = time.monotonic()
    snapshot_relative = f"evidence/{report['id']}/source"
    snapshot = contained(root, snapshot_relative)
    copy_tree(path, snapshot)
    student_hash = tree_hash(snapshot) if kind == "student" else None
    if variant:
        overlay(variant, snapshot, spec["editable_paths"])
    if extra_tests:
        extra = instructor(root, spec["id"]) / "tests"
        if extra.exists():
            for test in files(extra):
                target = snapshot / "tests" / "instructor" / test.relative_to(extra)
                if target.exists():
                    raise LabError("Instructor tests collide with a provided test file")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(test, target)
    report["source_snapshot"] = snapshot_relative
    if kind == "student":
        report["student_source_hash"] = student_hash
    report["source_hash"] = tree_hash(snapshot)
    report.update(run_cpp(root, snapshot, spec, report["id"], preset))
    if tree_hash(snapshot) != report["source_hash"]:
        report.update(exit_status=2, outcome="source_modified_during_run")
    report["duration"] = time.monotonic() - start
    report["failure_artifacts"] = [c["log"] for c in report["commands"] if c["exit_status"]]
    # Retain bounded compiler/error diagnostics even if the full logs are later removed.
    if report["exit_status"]:
        report["test_summary"]["diagnostics"] = [
            {"command": c["argv"], "tail": Path(c["log"]).read_text(errors="replace")[-8000:]}
            for c in report["commands"]
            if c["exit_status"]
        ]
    return save_report(root, report)


def prepare(root, exercise_id):
    try:
        return _prepare(root, exercise_id)
    except (LabError, OSError) as exc:
        from .state import commit, load_session
        from .core import json_text

        session = load_session(root)
        if session["phase"] == "preparing" and session["current_exercise_id"] == exercise_id:
            session.update(
                phase="blocked",
                resume_phase="preparing",
                reason=str(exc),
                last_report_id=None,
                version=session["version"] + 1,
            )
            commit(root, {"learner/session.json": json_text(validate("session", session))})
        raise


def _prepare(root, exercise_id):
    path, spec = load_exercise(root, exercise_id)
    teaching = instructor(root, exercise_id)
    instructions = validate("validation", read_json(teaching / "validation.json"))
    contract = contract_hash(root, exercise_id)
    ready_path = teaching / "ready.json"
    if ready_path.exists():
        old = validate("ready", read_json(ready_path))
        if old["revision"] > spec["revision"] or (
            old["revision"] == spec["revision"] and old["contract_hash"] != contract
        ):
            raise LabError(
                "Published contract changed without a new revision; increment spec.revision"
            )
    check_names = {c["id"]: c["test_name"] for c in spec["acceptance_checks"]}
    if set(instructions["semantic_review"]["requirements_reviewed"]) != set(spec["requirements"]):
        raise LabError(
            "Semantic review must cover every requirement, including non-executable promises"
        )
    for item in [instructions["skeleton_expectation"], *instructions["mutants"]]:
        if not set(item["checks"]) <= set(check_names):
            raise LabError("Validation expectation references an unknown acceptance check")
    expectation = instructions["skeleton_expectation"]
    if expectation["kind"] == "test_failure" and not expectation["checks"]:
        raise LabError("Skeleton test_failure must identify expected failing checks")
    if expectation["kind"] == "compile_failure" and (
        spec["template"] != "debugging" or not expectation["diagnostic"]
    ):
        raise LabError(
            "Compile-failure skeleton requires a debugging exercise and diagnostic substring"
        )
    mutant_ids = [m["id"] for m in instructions["mutants"]]
    if len(mutant_ids) != len(set(mutant_ids)):
        raise LabError("Mutant identifiers must be unique")
    # Validate complete overlays before running anything; never fill a missing student file implicitly.
    for folder in [
        teaching / "reference",
        teaching / "skeleton",
        *[teaching / "mutants" / m for m in mutant_ids],
    ]:
        actual = {p.relative_to(folder).as_posix() for p in files(folder)}
        if actual != set(spec["editable_paths"]):
            raise LabError(f"Variant {folder} must contain exactly editable_paths")
    aggregate = new_report(spec, "validation", contract, "required")
    start = time.monotonic()
    children = []
    failures = []
    for preset in ["debug", *spec["sanitizers"]]:
        report = run_variant(
            root, path, spec, contract, "reference", preset, teaching / "reference", True
        )
        children.append(report)
        if report["outcome"] == "environment_error":
            ready_path.unlink(missing_ok=True)
            raise LabError(
                f"Preparation stopped at {preset}: {report['test_summary'].get('error', 'environment unavailable')}; evidence/{report['id']}/summary.json"
            )
        if report["exit_status"]:
            failures.append(f"Reference failed under {preset}: {report['outcome']}")
    skeleton = run_variant(root, path, spec, contract, "skeleton", variant=teaching / "skeleton")
    children.append(skeleton)
    if expectation["kind"] == "test_failure":
        expected = {check_names[c] for c in expectation["checks"]}
        if (
            skeleton["outcome"] != "test_failure"
            or set(skeleton["test_summary"]["failed"]) != expected
        ):
            failures.append("Skeleton must fail exactly its declared functional checks")
    else:
        diagnostics = str(skeleton["test_summary"].get("diagnostics", []))
        if skeleton["outcome"] != "compile_failure" or expectation["diagnostic"] not in diagnostics:
            failures.append("Skeleton did not produce the declared compilation diagnostic")
    for mutant in instructions["mutants"]:
        report = run_variant(
            root,
            path,
            spec,
            contract,
            "mutant",
            variant=teaching / "mutants" / mutant["id"],
            extra_tests=True,
        )
        children.append(report)
        expected = {check_names[c] for c in mutant["checks"]}
        if report["outcome"] != "test_failure" or not expected <= set(
            report["test_summary"]["failed"]
        ):
            failures.append(f"Mutant {mutant['id']} was not caught by its expected tests")
    if contract_hash(root, exercise_id) != contract:
        failures.append("Contract changed during preparation")
    aggregate.update(
        child_reports=[r["id"] for r in children],
        duration=time.monotonic() - start,
        exit_status=2 if failures else 0,
        outcome="validation_failed" if failures else "ready",
        test_summary={
            "failures": failures,
            "semantic_review": instructions["semantic_review"],
            "acceptance_checks": spec["acceptance_checks"],
        },
    )
    save_report(root, aggregate)
    if not failures:
        write_json(
            ready_path,
            {
                "schema_version": 1,
                "exercise_id": exercise_id,
                "revision": spec["revision"],
                "contract_hash": contract,
                "report_id": aggregate["id"],
            },
            "ready",
        )
    else:
        # A previously successful marker must not survive a failed revalidation.
        if ready_path.exists():
            ready_path.unlink()
        from .state import commit, load_session
        from .core import json_text

        session = load_session(root)
        if session["phase"] == "preparing" and session["current_exercise_id"] == exercise_id:
            session.update(
                phase="blocked",
                resume_phase="preparing",
                reason="; ".join(failures),
                last_report_id=aggregate["id"],
                version=session["version"] + 1,
            )
            commit(root, {"learner/session.json": json_text(validate("session", session))})
    return aggregate


def check(root, exercise_id, preset=None):
    from .state import record_report

    path, spec, marker = require_ready(root, exercise_id)
    presets = [preset] if preset else ["debug", *spec["sanitizers"]]
    if preset and preset not in ["debug", "release", *spec["sanitizers"]]:
        raise LabError("Requested sanitizer is not declared in the exercise spec")
    reports = [
        run_variant(root, path, spec, marker["contract_hash"], "student", profile, extra_tests=True)
        for profile in presets
    ]
    aggregate = new_report(spec, "student", marker["contract_hash"], preset or "required")
    aggregate.update(
        source_hash=reports[0]["source_hash"],
        source_snapshot=reports[0]["source_snapshot"],
        student_source_hash=reports[0]["student_source_hash"],
        child_reports=[r["id"] for r in reports],
        duration=sum(r["duration"] for r in reports),
        commands=[c for r in reports for c in r["commands"]],
        toolchain=reports[0]["toolchain"],
        exit_status=max(r["exit_status"] for r in reports),
        test_summary={
            "runs": [
                {
                    "id": r["id"],
                    "preset": r["sanitizer"],
                    "outcome": r["outcome"],
                    "summary": r["test_summary"],
                }
                for r in reports
            ]
        },
        failure_artifacts=[p for r in reports for p in r["failure_artifacts"]],
    )
    if (
        any(r["source_hash"] != aggregate["source_hash"] for r in reports)
        or tree_hash(path) != aggregate["student_source_hash"]
    ):
        aggregate.update(exit_status=2, outcome="source_changed_during_check")
    elif contract_hash(root, exercise_id) != marker["contract_hash"]:
        aggregate.update(exit_status=2, outcome="contract_changed_during_check")
    else:
        aggregate["outcome"] = "passed" if aggregate["exit_status"] == 0 else "check_failed"
    save_report(root, aggregate)
    # Partial profile runs are useful diagnostics, but cannot qualify a session for completion.
    if preset is None:
        record_report(root, aggregate)
    return aggregate


def check_completed(root, item):
    """Recheck the exact completed snapshot, even after the live task is revised."""
    from .state import audit_report, report_for

    audit_report(root, item["report_id"])
    original = report_for(root, item["report_id"])
    if (
        (original["exercise_id"], original["exercise_revision"]) != (item["id"], item["revision"])
        or original["target_kind"] != "student"
        or original["exit_status"] != 0
        or original["sanitizer"] != "required"
        or not original["source_snapshot"]
    ):
        raise LabError(
            "Completed record must reference its successful required-profile student snapshot"
        )
    source = contained(root, original["source_snapshot"])
    spec = validate("exercise", read_json(source / "spec.json"))
    reports = []
    for preset in ["debug", *spec["sanitizers"]]:
        report = new_report(spec, "student", original["contract_hash"], preset)
        snapshot_relative = f"evidence/{report['id']}/source"
        snapshot = contained(root, snapshot_relative)
        copy_tree(source, snapshot)
        report.update(
            source_hash=original["source_hash"],
            source_snapshot=snapshot_relative,
            student_source_hash=original["student_source_hash"],
        )
        started = time.monotonic()
        report.update(run_cpp(root, snapshot, spec, report["id"], preset))
        report["duration"] = time.monotonic() - started
        if tree_hash(snapshot) != original["source_hash"]:
            report.update(exit_status=2, outcome="source_modified_during_run")
        save_report(root, report)
        reports.append(report)
    return {
        "report_ids": [r["id"] for r in reports],
        "exit_status": max(r["exit_status"] for r in reports),
    }
