"""Bounded subprocess execution and CMake/CTest evidence collection."""
from __future__ import annotations

import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

from .core import FRAMEWORK, LabError, atomic_text, contained

CATCH_COMMIT = "56809e5282f104c5c8b570e7c2996cdc352d94f1"


def environment():
    env = dict(os.environ)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    # Fail on undefined behavior; do not let a recoverable UBSan warning pass CTest.
    env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    env["ASAN_OPTIONS"] = "halt_on_error=1"
    env["TSAN_OPTIONS"] = "halt_on_error=1"
    return env


def execute(argv, log, timeout=120, cwd=None):
    start = time.monotonic()
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    timed_out = False
    with log.open("wb") as stream:
        try:
            process = subprocess.Popen(list(map(str, argv)), cwd=cwd, env=environment(),
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                code = 124
        except OSError as exc:
            stream.write(str(exc).encode())
            code = 127
    return {"argv": list(map(str, argv)), "exit_status": code,
            "duration": time.monotonic() - start, "log": str(log), "timed_out": timed_out}


def compiler():
    selected = os.environ.get("CXX", "clang++")
    resolved = shutil.which(selected, path=environment()["PATH"])
    if not resolved:
        raise LabError(f"Missing compiler {selected}; install Clang or set CXX to a compiler executable")
    return resolved


def probe(root, standard=20, sanitizer="none"):
    cache = contained(root, ".cache/probes")
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="probe-", dir=cache) as temporary:
        path = Path(temporary)
        source = path / "probe.cpp"
        atomic_text(source, '''#include <iostream>
#include <span>
#include <thread>
#if __cplusplus < 202002L
#error C++20 is required
#endif
int main() {
  int values[] = {1, 2};
  std::span<int> view(values);
  std::thread worker([] {});
  worker.join();
#if defined(_LIBCPP_VERSION)
  std::cout << "libc++ " << _LIBCPP_VERSION;
#elif defined(__GLIBCXX__)
  std::cout << "libstdc++ " << __GLIBCXX__;
#else
  std::cout << "unknown standard library";
#endif
  return view.size() != 2;
}
''')
        argv = [compiler(), f"-std=c++{standard}", "-pthread", str(source), "-o", str(path / "probe")]
        flags = {"asan": "address,undefined", "tsan": "thread"}
        if sanitizer in flags:
            argv += [f"-fsanitize={flags[sanitizer]}", "-fno-omit-frame-pointer"]
        compilation = execute(argv, path / "compile.log")
        if compilation["exit_status"]:
            return {"supported": False, "detail": (path / "compile.log").read_text(errors="replace")[-3000:]}
        execution = execute([path / "probe"], path / "run.log", timeout=15)
        return {"supported": execution["exit_status"] == 0,
                "detail": (path / "run.log").read_text(errors="replace")[-3000:]}


def doctor(root):
    tools = {}
    issues = []
    with tempfile.TemporaryDirectory(prefix="lab-doctor-") as temporary:
        for name in ["cmake", "ctest", "ninja", "git"]:
            executable = shutil.which(name, path=environment()["PATH"])
            if not executable:
                issues.append(f"Missing {name}")
                tools[name] = None
                continue
            log = Path(temporary) / f"{name}.log"
            result = execute([executable, "--version"], log, timeout=10)
            tools[name] = {"path": executable, "version": log.read_text(errors="replace").splitlines()[0]}
            if result["exit_status"]:
                issues.append(f"Cannot execute {name}")
            if name == "cmake":
                match = re.search(r"(\d+)\.(\d+)", tools[name]["version"])
                if not match or tuple(map(int, match.groups())) < (3, 25):
                    issues.append("CMake 3.25 or newer is required")
        try:
            log = Path(temporary) / "compiler.log"
            execute([compiler(), "--version"], log, timeout=10)
            tools["compiler"] = {"path": compiler(), "version": log.read_text(errors="replace").strip()}
            capabilities = {kind: probe(root, sanitizer=kind) for kind in ["none", "asan", "tsan"]}
            if not capabilities["none"]["supported"]:
                issues.append("Compiler cannot build and run the C++20 capability probe")
        except LabError as exc:
            capabilities = {}
            issues.append(str(exc))
    if sys.platform not in {"darwin", "linux"}:
        issues.append(f"Unsupported platform: {sys.platform}")
    return {"python": sys.version, "platform": sys.platform, "tools": tools,
            "capabilities": capabilities, "issues": issues}


def ensure_catch(root, commands, log_dir, timeout):
    checkout = contained(root, ".cache/dependencies/Catch2")
    checkout.mkdir(parents=True, exist_ok=True)

    def command(argv, name):
        result = execute(argv, log_dir / name, timeout, cwd=checkout)
        commands.append(result)
        if result["exit_status"]:
            raise LabError(f"Catch2 preparation failed; see {result['log']}")

    if not (checkout / ".git").exists():
        command(["git", "init"], "catch-init.log")
    # The pinned object may be an annotated tag; compare peeled commits.
    pinned = execute(["git", "rev-parse", "--verify", f"{CATCH_COMMIT}^{{commit}}"],
                     log_dir / "catch-pin.log", timeout, cwd=checkout)
    commands.append(pinned)
    if pinned["exit_status"]:
        command(["git", "fetch", "--depth", "1", "https://github.com/catchorg/Catch2.git", CATCH_COMMIT], "catch-fetch.log")
        command(["git", "rev-parse", "--verify", f"{CATCH_COMMIT}^{{commit}}"], "catch-pin.log")
    expected = (log_dir / "catch-pin.log").read_text().strip()
    current = execute(["git", "rev-parse", "HEAD"], log_dir / "catch-head.log", timeout, cwd=checkout)
    commands.append(current)
    if current["exit_status"] or (log_dir / "catch-head.log").read_text().strip() != expected:
        command(["git", "checkout", "--detach", expected], "catch-checkout.log")
    command(["git", "diff", "--exit-code", "HEAD", "--"], "catch-integrity.log")
    return checkout


def run_cpp(root, source, spec, report_id, preset):
    log_dir = contained(root, f"reports/{report_id}")
    log_dir.mkdir(parents=True, exist_ok=True)
    commands = []
    summary = {"total": 0, "failed": [], "passed": [], "cases": [], "stage": "environment"}
    toolchain = {"platform": sys.platform, "python": sys.version, "preset": preset}

    def result(outcome, code):
        return {"commands": commands, "test_summary": summary, "toolchain": toolchain,
                "outcome": outcome, "exit_status": code}

    timeout = spec["resource_limits"]["command_timeout_seconds"]
    try:
        if sys.platform not in spec["platform"]:
            raise LabError(f"Exercise requires platform {spec['platform']}; host is {sys.platform}")
        capability = probe(root, spec["cpp_standard"], preset)
        toolchain["standard_library"] = capability["detail"]
        toolchain["compiler"] = compiler()
        toolchain["architecture"] = os.uname().machine
        toolchain["kernel"] = os.uname().release
        version = execute([compiler(), "--version"], log_dir / "compiler.log", timeout)
        commands.append(version)
        toolchain["compiler_version"] = (log_dir / "compiler.log").read_text(errors="replace").strip()
        if not capability["supported"]:
            raise LabError(f"Required {preset} C++{spec['cpp_standard']} capability probe failed: {capability['detail']}")
        checkout = ensure_catch(root, commands, log_dir, timeout)
    except LabError as exc:
        summary["error"] = str(exc)
        return result("environment_error", 2)
    build = contained(root, f"build/{report_id}")
    configure = ["cmake", "--preset", preset, "-S", FRAMEWORK, "-B", build,
                 f"-DLAB_SOURCE_DIR={source}", f"-DCMAKE_CXX_COMPILER={compiler()}",
                 f"-DFETCHCONTENT_SOURCE_DIR_CATCH2={checkout}"]
    summary["stage"] = "configure"
    commands.append(execute(configure, log_dir / "configure.log", timeout, cwd=FRAMEWORK))
    if commands[-1]["exit_status"]:
        return result("configuration_error", 2)
    summary["stage"] = "build"
    commands.append(execute(["cmake", "--build", build, "--target", "lab_tests", "--parallel",
                             str(spec["resource_limits"]["build_jobs"])], log_dir / "build.log", timeout))
    if commands[-1]["exit_status"]:
        return result("build_timeout" if commands[-1]["timed_out"] else "compile_failure", 2 if commands[-1]["timed_out"] else 1)
    # Discover before running: a malformed test binary or missing acceptance case is not a student failure.
    summary["stage"] = "discovery"
    discovery = execute(["ctest", "--test-dir", build, "--show-only=json-v1"], log_dir / "discovery.json", timeout)
    commands.append(discovery)
    try:
        import json
        discovered = json.loads((log_dir / "discovery.json").read_text())["tests"]
        names = {test["name"] for test in discovered}
    except (ValueError, KeyError):
        names = set()
    expected = {check["test_name"] for check in spec["acceptance_checks"]}
    if discovery["exit_status"] or not names or not expected <= names:
        summary["error"] = f"Missing acceptance tests or failed discovery: {sorted(expected - names)}"
        return result("discovery_error", 2)
    summary["stage"] = "test"
    # CTest test names remain stable; override Catch2's seed through its environment-independent arguments.
    # The generated test registration reads LAB_TEST_SEED from the configure-time spec.
    for index, seed in enumerate(spec["seeds"]):
        if index:
            commands.append(execute(configure + [f"-DLAB_TEST_SEED={seed}"], log_dir / f"seed-{seed}-configure.log", timeout, cwd=FRAMEWORK))
            if commands[-1]["exit_status"]:
                return result("configuration_error", 2)
        junit = log_dir / f"seed-{seed}.xml"
        command = execute(["ctest", "--test-dir", build, "--output-on-failure", "--no-tests=error",
                           "--timeout", str(spec["resource_limits"]["test_timeout_seconds"]),
                           "--output-junit", junit], log_dir / f"seed-{seed}.log", timeout)
        commands.append(command)
        if command["timed_out"]:
            return result("test_timeout", 1)
        try:
            cases = ET.parse(junit).getroot().findall(".//testcase")
        except (ET.ParseError, OSError):
            return result("test_report_error", 2)
        if not cases:
            return result("zero_tests", 2)
        for case in cases:
            failed = case.find("failure") is not None or case.find("error") is not None or case.find("skipped") is not None
            name = case.attrib.get("name", "")
            detail = "".join(case.itertext())[-8000:] if failed else ""
            summary["cases"].append({"name": name, "seed": seed, "passed": not failed, "failure_detail": detail})
            summary["failed" if failed else "passed"].append(name)
        summary["total"] += len(cases)
        execution_log = (log_dir / f"seed-{seed}.log").read_text(errors="replace")
        if "***Timeout" in execution_log:
            return result("test_timeout", 1)
        if any(marker in execution_log for marker in ["***Exception", "Subprocess aborted", "***Not Run"]):
            return result("test_process_failure", 1)
        if command["exit_status"] and not summary["failed"]:
            return result("test_execution_error", 2)
    summary["stage"] = "complete"
    summary["failed"] = sorted(set(summary["failed"]))
    summary["passed"] = sorted(set(summary["passed"]))
    return result("test_failure" if summary["failed"] else "passed", 1 if summary["failed"] else 0)
