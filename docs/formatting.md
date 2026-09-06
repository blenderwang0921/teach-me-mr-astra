# Local formatting

English | [繁體中文](zh-TW/formatting.md)

`uv sync --frozen` installs the locked Ruff development dependency. `./lab format`
formats framework Python; `./lab format --check` checks it without edits. Explicit
files can be supplied, including C++: `./lab format exercises/ID/src/exercise.cpp`.
C++ uses installed clang-format and `.clang-format`; no lint fixes or model calls.

VS Code workspace settings enable format-on-save for Python (Ruff extension) and
C++ (Microsoft C/C++ extension). Install the recommended extensions once if missing.
The repository's `.codex/hooks.json` configures a synchronous PostToolUse command
for `apply_patch`. It formats only patch targets, is silent on success, and reports
errors. This machine's Codex CLI 0.153.4 reports hooks enabled. A fresh Codex session
must load the configuration; the handler is testable without calling a model.

The hook does not cover arbitrary shell writes, MCP editors, or manual edits in
other editors. After shell generation, run the explicit format command before
prepare/check. Do not use an asynchronous formatter: it can invalidate a test
snapshot after tests begin. Successful local formatting uses no model inference;
hook metadata or error messages can still contribute context, so total session
usage cannot be promised to be literally zero.

The helper rejects evidence, reports, learner records, symlinks and published
instructor/provided files. Existing learner implementations are formatted only
when explicitly named or edited by a patch. The hook grants no permission to solve
an exercise. Editor format-on-save applies to the document being saved; evidence
is configured read-only. Do not edit published provided files casually.

Sources: [Codex hooks](https://learn.chatgpt.com/docs/hooks),
[Ruff editor setup](https://docs.astral.sh/ruff/editors/setup/),
[VS Code C++ formatting](https://code.visualstudio.com/docs/cpp/cpp-ide).
