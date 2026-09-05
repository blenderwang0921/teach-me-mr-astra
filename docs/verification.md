# Local verification — 2026-09-05

Verified on macOS 14.5 / arm64 with Python 3.14.3, CMake 4.3.1, Ninja 1.13.0, and Homebrew Clang 22.1.2 / libc++ 220102. Commands explicitly selected `CXX=/opt/homebrew/opt/llvm/bin/clang++`.

## Results

- 27 tool/state behavior tests passed. The default suite discovers 30 tests and intentionally skips the three opt-in C++ integration tests.
- All three C++ integration tests passed in separate verification runs: complete learning loop and process restart; intentional compiler-error debugging; isolated rechecking of a historical completed snapshot under debug and ASan+UBSan.
- The complete-loop test verifies reference/debug/ASan validation, mutant detection, skeleton failure, non-overwriting student checks, recorded assistance, a simulated learner fix, explanation/review, deletion of disposable logs, and recovery in a new Python process.
- Doctor's baseline, ASan+UBSan, and TSan probes passed with the selected LLVM. This is not a concurrency-exercise correctness claim.
- Empty-root CMake configuration succeeded after selecting the local compiler and making the virtual environment's Ninja available on PATH.
- Repeated initialization created no files and preserved session version 0. Status reports onboarding, no selected exercise, and no integrity issues.
- The local `ci` command succeeds with no published or completed exercises. Linux Clang/GCC GitHub Actions are configured but have not been run remotely.

The default Apple Clang installation cannot locate `iostream`; it is not the validated toolchain. No system compiler was replaced. No formal exercise or learner proficiency observation was created during implementation; C++ verification used temporary fixture workspaces. Local Git metadata is initialized, with no commit or remote publication.

## Reproduce

```sh
uv sync --frozen
source .venv/bin/activate
export CXX=/opt/homebrew/opt/llvm/bin/clang++
python tools/lab.py doctor
python -m unittest discover -s tools/tests -v
LAB_CPP_TESTS=1 python -m unittest discover -s tools/tests -v
python tools/lab.py status
```

Use a compiler path appropriate for another machine. Real integration tests need initial access to the pinned Catch2 source. Tool tests do not need a model API or network.

