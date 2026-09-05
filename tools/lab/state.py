"""Single-writer, revision-checked state transactions with redo recovery."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from .core import (LabError, atomic_text, contained, json_text, read_json,
                   validate, valid_id, write_json)

TRANSITIONS = {
    "onboarding": {"onboarding", "planning", "paused"},
    "planning": {"planning", "preparing", "paused"},
    "preparing": {"preparing", "practicing", "blocked", "paused"},
    "practicing": {"practicing", "reviewing", "preparing", "paused"},
    "reviewing": {"reviewing", "planning", "preparing", "paused"},
    "paused": {"paused"},
    "blocked": {"blocked", "preparing", "planning", "paused"},
}


def recover(root):
    journal = contained(root, "learner/.transaction.json")
    if not journal.exists():
        return False
    pending = read_json(journal)
    if set(pending) != {"schema_version", "files"} or pending["schema_version"] != 1 or not isinstance(pending["files"], dict):
        raise LabError("Invalid recovery journal; preserve it and restore from backup")
    validated = []
    for relative, content in pending["files"].items():
        if not (relative in {"learner/profile.json", "learner/session.json", "learner/evidence.jsonl"}
                or (relative.startswith("learner/reviews/") and relative.endswith(".json"))):
            raise LabError("Recovery journal contains an invalid state destination")
        path = contained(root, relative)
        if not isinstance(content, str):
            raise LabError("Invalid recovery content")
        try:
            if relative.endswith("evidence.jsonl"):
                for line in content.splitlines():
                    if line.strip():
                        validate("evidence", json.loads(line))
            else:
                kind = "review" if relative.startswith("learner/reviews/") else Path(relative).stem
                validate(kind, json.loads(content))
        except ValueError as exc:
            raise LabError("Recovery journal contains invalid JSON; preserve it and restore from backup") from exc
        validated.append((path, content))
    for path, content in validated:
        atomic_text(path, content)
    journal.unlink()
    return True


def commit(root, changes):
    write_json(contained(root, "learner/.transaction.json"), {"schema_version": 1, "files": changes})
    recover(root)


def init(root):
    defaults = {
        "learner/profile.json": ("profile", {
            "schema_version": 1, "goals": [], "language_standard": 20,
            "platform": sys.platform, "time_budget": None, "preferences": {},
            "preferred_interaction_language": "zh-TW", "self_reported_experience": [],
        }),
        "learner/session.json": ("session", {
            "schema_version": 1, "version": 0, "phase": "onboarding",
            "current_exercise_id": None, "exercise_revision": None,
            "last_report_id": None, "pending_questions": [],
            "next_action": "Ask a short interview before choosing a calibration exercise.",
            "resume_phase": None, "reason": None, "completed_exercises": [],
        }),
        "references/catalog.json": ("catalog", {"schema_version": 1, "materials": []}),
    }
    created = []
    for relative in ["exercises", ".instructor", "learner/reviews", "learner/artifacts", "evidence", "references/materials"]:
        contained(root, relative).mkdir(parents=True, exist_ok=True)
    for relative, (kind, value) in defaults.items():
        path = contained(root, relative)
        if path.exists():
            validate(kind, read_json(path))
        else:
            write_json(path, value, kind)
            created.append(relative)
    evidence = contained(root, "learner/evidence.jsonl")
    if not evidence.exists():
        atomic_text(evidence, "")
        created.append("learner/evidence.jsonl")
    read_evidence(root)
    return {"created": created, "session": load_session(root)}


def load_session(root):
    return validate("session", read_json(contained(root, "learner/session.json")))


def read_evidence(root):
    path = contained(root, "learner/evidence.jsonl")
    try:
        result = [validate("evidence", json.loads(line)) for line in path.read_text().splitlines() if line.strip()]
    except (OSError, ValueError) as exc:
        raise LabError(f"Invalid evidence log: {exc}") from exc
    ids = [item["id"] for item in result]
    if len(ids) != len(set(ids)):
        raise LabError("Duplicate evidence identifiers")
    return result


def verify_refs(root, refs):
    for relative in refs:
        if not relative.startswith(("evidence/", "learner/artifacts/", "learner/reviews/")):
            raise LabError(f"Evidence must reference a durable artifact, not a mutable source or log: {relative}")
        if not contained(root, relative).is_file():
            raise LabError(f"Missing evidence reference: {relative}")


def report_for(root, report_id):
    valid_id(report_id)
    return validate("report", read_json(contained(root, f"evidence/{report_id}/summary.json")))


def audit_report(root, report_id, seen=None):
    from .core import tree_hash
    seen = set() if seen is None else seen
    if report_id in seen:
        return
    seen.add(report_id)
    report = report_for(root, report_id)
    if report["id"] != report_id:
        raise LabError(f"Report identifier does not match its directory: {report_id}")
    if report["source_snapshot"]:
        snapshot = contained(root, report["source_snapshot"])
        if tree_hash(snapshot) != report["source_hash"]:
            raise LabError(f"Evidence source snapshot is missing or changed: {report_id}")
    for child_id in report["child_reports"]:
        audit_report(root, child_id, seen)


def apply(root, update):
    from .exercise import require_ready

    validate("state-update", update)
    previous = load_session(root)
    if update["expected_version"] != previous["version"]:
        raise LabError(f"State conflict: expected version {update['expected_version']}, current {previous['version']}")
    session = update.get("session", dict(previous))
    if session["version"] != previous["version"] + (1 if "session" in update else 0):
        raise LabError("Submitted session.version must equal expected_version + 1")
    session = dict(session, version=previous["version"] + 1)
    before, after = previous["phase"], session["phase"]
    allowed = set(TRANSITIONS[before])
    if before == "paused" and previous["resume_phase"]:
        allowed.add(previous["resume_phase"])
    if after not in allowed:
        raise LabError(f"Invalid phase transition: {before} -> {after}")
    if before in {"practicing", "reviewing"} and after == "preparing":
        if not update.get("reviews"):
            raise LabError("Returning to preparing requires a review explaining the exercise defect and revision")
    if after in {"paused", "blocked"}:
        expected_resume = previous["resume_phase"] if before in {"paused", "blocked"} else before
        if session["resume_phase"] != expected_resume or not session["reason"]:
            raise LabError("Paused/blocked state needs its original resume phase and a reason")
    elif session["resume_phase"] is not None or session["reason"] is not None:
        raise LabError("Active state must clear resume_phase and reason")
    exercise_id, revision = session["current_exercise_id"], session["exercise_revision"]
    if (exercise_id is None) != (revision is None):
        raise LabError("Exercise identifier and revision must be set or cleared together")
    if after in {"preparing", "practicing", "reviewing"} and exercise_id is None:
        raise LabError(f"Phase {after} requires an exercise and revision")
    if after in {"practicing", "reviewing"}:
        require_ready(root, exercise_id, revision)
    if before in {"practicing", "reviewing", "paused"} and after in {"practicing", "reviewing"}:
        if (exercise_id, revision) != (previous["current_exercise_id"], previous["exercise_revision"]):
            raise LabError("Return to planning/preparing before changing the active exercise revision")
    if session["last_report_id"]:
        report = report_for(root, session["last_report_id"])
        if exercise_id and (report["exercise_id"], report["exercise_revision"]) != (exercise_id, revision):
            raise LabError("Last report belongs to a different exercise revision")
    old_completed = {(x["id"], x["revision"], x["report_id"]) for x in previous["completed_exercises"]}
    new_completed = {(x["id"], x["revision"], x["report_id"]) for x in session["completed_exercises"]}
    if len({(x[0], x[1]) for x in new_completed}) != len(session["completed_exercises"]):
        raise LabError("Completed exercise revisions must be unique")
    if not old_completed <= new_completed:
        raise LabError("Completed exercise history is append-only")
    reviews = update.get("reviews", [])
    for item in new_completed - old_completed:
        if before != "reviewing" or after != "planning" or item[:2] != (previous["current_exercise_id"], previous["exercise_revision"]):
            raise LabError("Completion must be recorded when leaving the current exercise review")
        if not any((r["exercise_id"], r["exercise_revision"]) == item[:2] for r in reviews):
            raise LabError("Completion requires a review with the learner's explanation")
        if item[2] != previous["last_report_id"]:
            raise LabError("Completion must retain the current qualifying report identifier")
        latest = report_for(root, previous["last_report_id"] or "missing")
        if latest["target_kind"] != "student" or latest["exit_status"] != 0 or latest["sanitizer"] != "required":
            raise LabError("Completion requires a successful student report")
        require_ready(root, item[0], item[1])
        audit_report(root, latest["id"])
        from .exercise import load_exercise
        from .core import tree_hash
        path, _ = load_exercise(root, item[0])
        if latest["student_source_hash"] != tree_hash(path):
            raise LabError("Student source changed since the passing report; check again")
    changes = {"learner/session.json": json_text(validate("session", session))}
    if "profile" in update:
        changes["learner/profile.json"] = json_text(update["profile"])
    history = read_evidence(root)
    seen = {e["id"] for e in history}
    for entry in update.get("evidence", []):
        verify_refs(root, entry["evidence_refs"])
        if entry["id"] in seen or (entry["supersedes"] and entry["supersedes"] not in seen):
            raise LabError("Evidence identifier is duplicate or supersedes an unknown observation")
        seen.add(entry["id"])
        history.append(entry)
    if update.get("evidence"):
        changes["learner/evidence.jsonl"] = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in history)
    for review in reviews:
        verify_refs(root, review["evidence_refs"])
        relative = f"learner/reviews/{review['id']}.json"
        if contained(root, relative).exists() or relative in changes:
            raise LabError(f"Review already exists: {review['id']}")
        changes[relative] = json_text(review)
    commit(root, changes)
    return {"session": session, "updated": list(changes)}


def record_report(root, report):
    """Record a check without inferring mastery or changing the teaching phase."""
    session = load_session(root)
    if (session["current_exercise_id"], session["exercise_revision"]) == (report["exercise_id"], report["exercise_revision"]):
        session["version"] += 1
        session["last_report_id"] = report["id"]
        commit(root, {"learner/session.json": json_text(validate("session", session))})


def status(root):
    from .exercise import require_ready
    session = load_session(root)
    issues = []
    validate("profile", read_json(contained(root, "learner/profile.json")))
    audited = set()
    def inspect_refs(refs):
        verify_refs(root, refs)
        for relative in refs:
            parts = Path(relative).parts
            if len(parts) == 3 and parts[0] == "evidence" and parts[2] == "summary.json":
                audit_report(root, parts[1], audited)
    for entry in read_evidence(root):
        try:
            inspect_refs(entry["evidence_refs"])
        except LabError as exc:
            issues.append(str(exc))
    for path in contained(root, "learner/reviews").glob("*.json"):
        try:
            review = validate("review", read_json(path))
            inspect_refs(review["evidence_refs"])
        except LabError as exc:
            issues.append(str(exc))
    for item in session["completed_exercises"]:
        try:
            audit_report(root, item["report_id"], audited)
        except LabError as exc:
            issues.append(str(exc))
    last = None
    if session["last_report_id"]:
        try:
            last = report_for(root, session["last_report_id"])
            audit_report(root, session["last_report_id"], audited)
        except LabError as exc:
            issues.append(str(exc))
    if session["current_exercise_id"] and session["phase"] in {"practicing", "reviewing"}:
        try:
            require_ready(root, session["current_exercise_id"], session["exercise_revision"])
        except LabError as exc:
            issues.append(str(exc))
    return {"session": session, "last_report": last, "integrity_issues": issues}
