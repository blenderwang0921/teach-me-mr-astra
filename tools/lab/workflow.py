"""Compact teaching context and guarded workflow shortcuts."""

from . import exercise, runner, state
from .core import LabError, contained, read_json, tree_hash, validate

ROUTES = {
    "onboarding": "teaching/interview.md",
    "planning": "teaching/generate.md",
    "preparing": "teaching/generate.md",
    "practicing": "teaching/coach.md",
    "reviewing": "teaching/review.md",
}


def report_summary(report):
    if report is None:
        return None
    result = {
        key: report[key]
        for key in (
            "id",
            "target_kind",
            "exercise_id",
            "exercise_revision",
            "outcome",
            "exit_status",
            "sanitizer",
            "source_snapshot",
        )
    }
    result["path"] = f"evidence/{report['id']}/summary.json"
    result["profiles"] = [
        {
            "preset": run["preset"],
            "outcome": run["outcome"],
            "failed": run["summary"].get("failed", []),
        }
        for run in report["test_summary"].get("runs", [])
    ]
    return result


def context(root):
    """Read state, audit evidence, and check freshness once; never run tests."""
    data = state.status(root)
    session = data["session"]
    phase = session["resume_phase"] or session["phase"]
    report = data["last_report"]
    result = {
        "session": session,
        "profile": validate("profile", read_json(contained(root, "learner/profile.json"))),
        "workflow": ROUTES.get(phase),
        "last_report": report_summary(report),
        "integrity_issues": data["integrity_issues"],
        "exercise": None,
        "check_reusable": False,
        "check_reason": "No active exercise with a current successful default check.",
    }
    active = session["current_exercise_id"]
    observations = state.read_evidence(root)
    relevant = [e for e in observations if e["exercise_id"] == active] if active else observations
    result["recent_evidence"] = relevant[-2:]
    if not active:
        return result
    path, spec = exercise.load_exercise(root, active)
    sources = {}
    remaining = 12000
    for name in spec["editable_paths"]:
        content = contained(path, name).read_text()
        sources[name] = content[:remaining]
        remaining -= len(sources[name])
        if len(sources[name]) < len(content):
            sources[name] += "\n[Truncated; read this workspace file directly.]"
    result["exercise"] = {
        "workspace": str(path),
        "readme": str(path / "README.md"),
        "spec": spec,
        "editable_source": sources,
    }
    if report and (report["exercise_id"], report["exercise_revision"]) == (
        active,
        spec["revision"],
    ):
        source_matches = report["student_source_hash"] == tree_hash(path)
        contract_matches = report["contract_hash"] == exercise.contract_hash(root, active)
        result["last_report"].update(
            source_matches=source_matches, contract_matches=contract_matches
        )
        result["check_reusable"] = bool(
            source_matches
            and contract_matches
            and not result["integrity_issues"]
            and report["target_kind"] == "student"
            and report["outcome"] == "passed"
            and report["exit_status"] == 0
            and report["sanitizer"] == "required"
            and session["phase"] in {"practicing", "reviewing"}
        )
        result["check_reason"] = (
            "Reuse this pass; review the learner explanation without rerunning tests."
            if result["check_reusable"]
            else "No reusable pass: inspect freshness, outcome, phase, and integrity fields."
        )
    return result


def configure_ide(root):
    """Prepare IntelliSense for the active exercise without running tests."""
    session = state.load_session(root)
    exercise_id = session["current_exercise_id"]
    if not exercise_id:
        raise LabError("No active exercise; IntelliSense is prepared after assignment")
    path, spec = exercise.load_exercise(root, exercise_id)
    if session["exercise_revision"] != spec["revision"]:
        raise LabError("Active exercise revision differs from its specification")
    return {"exercise_id": exercise_id, **runner.configure_ide(root, path, spec)}


def transition(root, phase, expected_version, next_action, exercise_id=None, reason=None):
    session = state.load_session(root)
    if phase == "resume":
        if session["phase"] != "paused":
            raise LabError("Resume requires a paused session")
        phase = session["resume_phase"]
    if exercise_id:
        if phase != "preparing":
            raise LabError("--exercise is only valid when entering preparing")
        _, spec = exercise.load_exercise(root, exercise_id)
        session.update(
            current_exercise_id=exercise_id, exercise_revision=spec["revision"], last_report_id=None
        )
    if phase == "paused":
        if not reason:
            raise LabError("Pause requires --reason")
        resume = session["resume_phase"] or session["phase"]
        session.update(resume_phase=resume, reason=reason)
    else:
        if reason:
            raise LabError("--reason is only valid for pause")
        session.update(resume_phase=None, reason=None)
    session.update(version=expected_version + 1, phase=phase, next_action=next_action)
    return state.apply(
        root, {"schema_version": 1, "expected_version": expected_version, "session": session}
    )


def finish(root, bundle):
    """Commit an authored review, evidence and completion in one transaction."""
    validate("completion", bundle)
    session = state.load_session(root)
    if session["phase"] not in {"practicing", "reviewing"}:
        raise LabError("Finish requires practicing or reviewing; resume a paused session first")
    review = bundle["review"]
    identity = (session["current_exercise_id"], session["exercise_revision"])
    if (review["exercise_id"], review["exercise_revision"]) != identity:
        raise LabError("Review must describe the active exercise revision")
    if not any(ref.startswith("learner/artifacts/") for ref in review["evidence_refs"]):
        raise LabError("Save the raw learner explanation in learner/artifacts and reference it")
    for entry in bundle["evidence"]:
        if (entry["exercise_id"], entry["exercise_revision"]) != identity:
            raise LabError("Completion observations must describe the active exercise revision")
    session["completed_exercises"].append(
        {
            "id": identity[0],
            "revision": identity[1],
            "report_id": session["last_report_id"],
        }
    )
    session.update(
        version=bundle["expected_version"] + 1,
        phase="planning",
        current_exercise_id=None,
        exercise_revision=None,
        pending_questions=[],
        next_action=review["next_action"],
    )
    return state.apply(
        root,
        {
            "schema_version": 1,
            "expected_version": bundle["expected_version"],
            "session": session,
            "reviews": [review],
            "evidence": bundle["evidence"],
        },
    )


def prepare_and_assign(root, exercise_id, expected_version):
    session = state.load_session(root)
    if session["version"] != expected_version:
        raise LabError(
            f"State conflict: expected version {expected_version}, current {session['version']}"
        )
    if session["phase"] == "planning":
        transition(
            root,
            "preparing",
            expected_version,
            "Validate the authored exercise before assignment.",
            exercise_id,
        )
    elif not (session["phase"] == "preparing" and session["current_exercise_id"] == exercise_id):
        raise LabError("prepare --assign requires planning or the same active preparing exercise")
    report = exercise.prepare(root, exercise_id)
    if report["exit_status"] == 0:
        ide_setup = configure_ide(root)
        session = state.load_session(root)
        updated = transition(
            root,
            "practicing",
            session["version"],
            f"Learner should edit exercises/{exercise_id}/ using its README, then run ./lab check. Await learner work; do not poll or edit their implementation.",
        )
        report = {**report, "ide_setup": ide_setup, "session": updated["session"]}
    return report
