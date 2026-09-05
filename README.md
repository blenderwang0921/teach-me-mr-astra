# Teach Me, Mr. Astra

A local C++ learning repository for rebuilding implementation, debugging, and design judgment through hands-on work. Open this repository in Codex and say **開始**, **繼續**, **start**, or **continue**. The teacher interviews you briefly, prepares one verified exercise, and records enough evidence to resume in a new session.

The learner writes the solution. The teacher chooses exercises, asks useful questions, offers hints, and checks evidence. Passing tests never automatically means mastery.

## Setup

Requirements: macOS or Linux, Python 3.11+, CMake 3.25+, Git, and a working C++20 compiler. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available. Ninja and Python dependencies are installed into the project environment from `uv.lock`.

```sh
uv sync --frozen
source .venv/bin/activate
python tools/lab.py doctor
python tools/lab.py init
python tools/lab.py status
```

`doctor` compiles and runs capability probes; a compiler version string alone is insufficient. It does not install or upgrade system tools. Initial exercise preparation downloads the pinned Catch2 release into `.cache/dependencies/Catch2`; subsequent runs reuse that checkout. No model API key is required.

For this development machine, the default Apple compiler cannot find its C++ standard headers. An existing Homebrew LLVM installation works; select it explicitly:

```sh
export CXX=/opt/homebrew/opt/llvm/bin/clang++
python tools/lab.py doctor
```

See [environment notes](docs/environment.md) for supported profiles and verified versions.

## Learn

Open the repository in Codex and say `start` or `continue`. The teacher follows [AGENTS.md](AGENTS.md), reads your current session, and asks only questions needed for the next exercise. There are no preselected lessons. `tools/tests/fixtures` contains framework tests, not a curriculum.

After receiving a verified exercise, edit only its declared `editable_paths` and run:

```sh
python tools/lab.py check <exercise-id>
python tools/lab.py status
```

Ask for a hint when needed. After implementation, explain a key decision or predict a changed requirement. The teacher records assistance and evidence before choosing the next step. You can explicitly request a full solution, but that completion will be recorded as assisted.

Formal documents, generated exercises, source comments, and reports use English. Conversation defaults to Traditional Chinese through `learner/profile.json`; your own answers can remain in your preferred language.

## Commands

| Command | Behavior |
| --- | --- |
| `doctor` | Inspect tools, compiler, standard library, and sanitizer capability. |
| `init` | Create empty learner state and directories; preserve existing files. |
| `prepare <id>` | Validate existing exercise assets and publish a revision-bound ready marker. |
| `check <id>` | Run public and additional tests against a snapshot of the student version. |
| `check <id> --preset release` | Run a diagnostic profile without qualifying session completion. |
| `status` | Show phase, pending questions, last report, and broken evidence references. |
| `state apply <file>` | Apply a schema-validated, version-checked teaching transaction. |
| `ci` | Revalidate published exercises and check declared-complete student versions. |

All commands are prefixed with `python tools/lab.py`. Add `--json` for one machine-readable object on stdout. `--root <workspace>` before the command selects an isolated workspace; tools and schemas still come from this framework.

Exit codes: **0** success; **1** student compilation/test failure or test timeout; **2** environment, configuration, state integrity, or publication failure. Expected skeleton/mutant failures can produce a successful `prepare`; a failed reference cannot. Unsupported required sanitizers, failed test discovery, and zero tests never count as passing.

`prepare` is deterministic: it does not generate missing code, call a model, or overwrite student files. The teacher creates complete assets using the [generation guide](teaching/generate.md). Default `check` runs debug and all required sanitizers. A single `--preset` is diagnostic only and does not update the session's qualifying report.

## State, evidence, and recovery

This is a **private learning repository**. Track `learner/`, `exercises/`, `.instructor/`, and `evidence/` in your private Git history. `.instructor/` reduces accidental answer exposure; it is not a security boundary. Export a clean framework copy before publishing publicly. The tools never commit, push, create an external repository, or send messages.

Full logs live in ignored `reports/`; immutable run snapshots and compact summaries live in tracked `evidence/<report-id>/`. Raw learner explanations belong in `learner/artifacts/`. Evidence references must point to durable files, not mutable exercise files or disposable logs. Do not delete referenced evidence. The append-only observation log can be corrected by adding a new entry with `supersedes`.

Run `status` after restarting. Lab commands recover any interrupted state transaction while holding an OS file lock. A stale lock file is harmless; a live writer causes a conflict error. Do not remove locks to bypass another running process. If a journal is corrupt, preserve it and restore the affected learner files from your private backup rather than inventing progress.

If a published exercise is wrong, the teacher records the defect, returns the session to preparing, increments its revision, and revalidates. Student failure never silently relaxes tests. See [state transactions](docs/state.md) for the concrete update interface.

## Verification

```sh
python -m unittest discover -s tools/tests -v
LAB_CPP_TESTS=1 python -m unittest discover -s tools/tests -v
python tools/lab.py ci
```

The first command checks state and tool behavior without downloading C++ dependencies. The second adds a real CMake/Catch2 loop in a temporary workspace: reference and sanitizer validation, expected student failure, recorded hint, simulated student fix, review, log removal, and recovery in a new process. It never edits your learning exercises.

Linux CI uses Clang 18 and GCC 14. Current unfinished exercises are not required to pass. Configured CI is not evidence that a remote run has occurred.

See [local verification results](docs/verification.md) for the tested environment, checks, and remaining platform limits.

## Design and contribution

[English design](docs/design.md) describes the implemented first version; [original design](design.md) preserves the Traditional Chinese handoff. Upstream material contracts exist, but adapters, a material library, Windows support, API workers, scheduling, and automatic mastery scoring are deferred.

Keep teaching rules concise and deterministic checks in Python. Add behavioral tests for state, publication, and evidence changes. Do not convert fixtures into assigned lessons or add a prefilled curriculum. Preserve upstream license notices when introducing material; no public distribution license is implied for learner work or external assets.
