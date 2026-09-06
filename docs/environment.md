# Environment and reproducibility

English | [繁體中文](zh-TW/environment.md)

## Baseline

- Python 3.11+; dependencies and transitive dependencies are pinned in `uv.lock`. `uv sync --frozen` installs Ninja 1.13.0 and jsonschema 4.25.1 into `.venv`.
- CMake 3.25+ with presets schema 6; Ninja generator; CTest included with CMake.
- C++20 by default, C++23 per spec. Clang is primary; Linux CI also selects GCC explicitly.
- Catch2 v3.8.1 at commit `56809e5282f104c5c8b570e7c2996cdc352d94f1`. The fixed Git checkout retains upstream licensing and is cached, not vendored into the framework.
- No modules, package-wide benchmark library, containers, or model API credentials are required.

Each run records compiler path/version, standard-library identifier, Python, platform, preset, commands, seed, duration, outcome, and source/contract hashes. Host architecture and kernel differences still matter; recorded versions are not a claim of bit-for-bit reproducibility.

## Select tools

Activate `.venv`, then set `CXX` to a compiler executable if needed. It must be one executable path/name, not a shell command containing flags. The lab locates Ninja next to its Python interpreter even without activation.

```sh
export CXX=clang++
python tools/lab.py doctor --json
```

This machine has macOS 14.5 on Apple Silicon, Python 3.14.3, CMake 4.3.1, and Homebrew LLVM 22.1.2 with libc++ 220102. LLVM capability probes pass for debug, ASan+UBSan, and TSan. The default Apple Clang 16.0.0 cannot locate its standard headers; selecting a compiler by version alone would miss this problem. Use the existing LLVM explicitly:

```sh
export CXX=/opt/homebrew/opt/llvm/bin/clang++
```

Do not globally replace the system compiler to fix this project. For manual CMake work, put host-specific presets in ignored `CMakeUserPresets.json`. For lab CLI execution, select the compiler with `CXX`; its built-in profile names are fixed.

## Profiles and limits

`debug` and `release` differ in build type. `asan` enables address and undefined-behavior checks; `tsan` enables thread checks separately. Sanitizers instrument exercise source and tests. Catch2 itself uses its normal build configuration. Required profiles must compile and run a capability probe before testing; unavailable required profiles fail explicitly.

Spec limits bound build parallelism, each test, and each command. Commands run in a process group; timeout kills the entire group. This is execution hygiene, not a sandbox for untrusted C++ or upstream repositories. Do not run untrusted exercises merely because a timeout exists. Resource limits do not currently impose a hard memory quota.

Linux CI targets Ubuntu 24.04 with Clang 18/GCC 14 and Python 3.11/3.14. The integration fixture exercises ASan+UBSan. TSan capability is probed, but real concurrency correctness requires a concurrency-specific exercise and tests; no such exercise is preassigned.

## Troubleshooting

- Missing tool: install it using your platform's package manager; rerun `doctor`.
- Dependency network failure: keep the report and retry once connectivity is available. No unverified fallback dependency is used.
- Compiler succeeds but sanitizer cannot run: inspect the probe details and platform. Do not silently remove a required sanitizer from an assigned task.
- Changed contract: increment exercise revision, record the reason, and run `prepare`. Student edits alone do not require revision changes.
- Failed source/test discovery or zero tests: fix the exercise/framework, not the learner's proficiency record.


## Cached dependency behavior

The Catch2 pin identifies an annotated tag object. Resolve it with `^{commit}` before
comparing it with HEAD. Fetch only when the pinned object is missing; verify the
working tree on every use. A valid cache must work without GitHub access. The lab
automatically selects installed Homebrew LLVM on macOS unless CXX overrides it.
