"""Human-readable and JSON command interfaces with stable exit codes."""
import argparse
import json
from pathlib import Path
import sys

from . import exercise, runner, state
from .core import FRAMEWORK, LabError, read_json, validate, writer


def parser():
    result = argparse.ArgumentParser(description="Local C++ learning lab; no model API calls")
    result.add_argument("--root", type=Path, default=FRAMEWORK, help="Workspace root (default: this repository)")
    result.add_argument("--json", action="store_true", help="Emit one JSON object on stdout")
    commands = result.add_subparsers(dest="command", required=True)
    for name, help_text in [("doctor", "Check tools and real compiler/sanitizer capabilities"),
                            ("init", "Initialize empty state without overwriting progress"),
                            ("status", "Show state, last result, and evidence integrity")]:
        child = commands.add_parser(name, help=help_text)
        child.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
        if name == "status":
            child.add_argument("--compact", action="store_true", help="Omit full report logs from JSON output")
    for name in ["prepare", "check"]:
        child = commands.add_parser(name, help="Validate publication" if name == "prepare" else "Test an isolated student snapshot")
        child.add_argument("id", **({"nargs": "?", "help": "Exercise id (default: active exercise)"} if name == "check" else {}))
        child.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
        if name == "check":
            child.add_argument("--preset", choices=["debug", "release", "asan", "tsan"], help="Diagnostic-only profile; omit for a completion-eligible check")
    state_parser = commands.add_parser("state", help="Apply a validated teaching-state transaction")
    sub = state_parser.add_subparsers(dest="state_command", required=True)
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("file", type=Path)
    apply_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    ci_parser = commands.add_parser("ci", help="Validate ready references and declared-complete student versions")
    ci_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    return result


def ci(root):
    results = []
    for marker in sorted((root / ".instructor").glob("*/ready.json")):
        exercise_id = marker.parent.name
        exercise.require_ready(root, exercise_id)
        report = exercise.prepare(root, exercise_id)
        results.append({"exercise_id": exercise_id, "kind": "reference", "report_id": report["id"], "exit_status": report["exit_status"]})
    for item in state.load_session(root)["completed_exercises"]:
        report = exercise.check_completed(root, item)
        results.append({"exercise_id": item["id"], "revision": item["revision"], "kind": "completed_student", **report})
    return {"results": results, "exit_status": max([r["exit_status"] for r in results], default=0)}


def dispatch(args):
    root = args.root.resolve()
    if args.command == "doctor":
        validate("catalog", {"schema_version": 1, "materials": []})
        data = runner.doctor(root)
        return data, 2 if data["issues"] else 0
    with writer(root):
        recovered = state.recover(root)
        if args.command == "init":
            data = state.init(root)
            code = 0
        elif args.command == "status":
            data = state.status(root)
            code = 2 if data["integrity_issues"] else 0
            if args.compact and data["last_report"]:
                report = data["last_report"]
                data["last_report"] = {key: report[key] for key in ("id", "outcome", "exit_status", "exercise_revision", "source_snapshot")}
        elif args.command == "state":
            data, code = state.apply(root, read_json(args.file)), 0
        elif args.command == "prepare":
            state.load_session(root)
            data = exercise.prepare(root, args.id)
            code = data["exit_status"]
        elif args.command == "check":
            session = state.load_session(root)
            exercise_id = args.id or session["current_exercise_id"]
            if not exercise_id:
                raise LabError("No active exercise; use check <id> or start a learning session")
            data = exercise.check(root, exercise_id, args.preset)
            code = data["exit_status"]
        else:
            data = ci(root)
            code = data["exit_status"]
        return {**data, "recovered_transaction": recovered}, code


def summarize(command, data, code):
    if "error" in data:
        return f"Error: {data['error']}"
    lines = [f"{command}: {'ok' if code == 0 else 'failed'} (exit {code})"]
    if "session" in data:
        session = data["session"]
        lines += [f"Phase: {session['phase']} | state version: {session['version']}",
                  f"Exercise: {session['current_exercise_id'] or 'none'} | revision: {session['exercise_revision']}",
                  f"Next: {session['next_action']}"]
        if session["current_exercise_id"]:
            lines.append(f"Workspace: exercises/{session['current_exercise_id']}/ (edit here, never evidence/)")
        lines += [f"Pending: {q}" for q in session["pending_questions"]]
        if session["reason"]:
            lines.append(f"Reason: {session['reason']}")
    if "outcome" in data:
        lines += [f"Outcome: {data['outcome']}", f"Evidence: evidence/{data['id']}/summary.json"]
        if data["commands"]:
            lines.append(f"Logs: {Path(data['commands'][0]['log']).parent}")
        lines += data["test_summary"].get("failures", [])
        for run in data["test_summary"].get("runs", []):
            lines.append(f"{run['preset']}: {run['outcome']} | failed: {', '.join(run['summary'].get('failed', [])) or 'none'}")
            if "error" in run["summary"]:
                lines.append(run["summary"]["error"])
    if "tools" in data:
        lines += [f"{name}: {info['version'] if info else 'missing'}" for name, info in data["tools"].items()]
        lines += [f"{name} probe: {'supported' if info['supported'] else 'unavailable'}" for name, info in data["capabilities"].items()]
    lines += data.get("issues", []) + data.get("integrity_issues", [])
    if data.get("recovered_transaction"):
        lines.append("Recovered an interrupted state transaction.")
    return "\n".join(lines)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        data, code = dispatch(args)
    except (LabError, OSError) as exc:
        data, code = {"error": str(exc)}, 2
    if args.json:
        print(json.dumps({"command": args.command, "exit_code": code, "data": data}, ensure_ascii=False))
    else:
        print(summarize(args.command, data, code))
    return code
