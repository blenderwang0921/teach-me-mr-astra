# Learning-lab entry rules

This repository is a local C++ learning environment. Treat `start`, `continue`, `開始`, and `繼續` as entry points to the teaching loop.

## Start or resume

1. Use `.venv/bin/python tools/lab.py status --compact --json`; if state is absent, run `init`. Run `doctor` on first use or an environment failure. See `docs/environment.md` for this host's compiler selection.
2. Read `learner/profile.json` and `learner/session.json`. Follow `next_action`; load only relevant evidence and the active spec. Do not restart an interview when resumable progress exists.
3. Route by phase: onboarding → `teaching/interview.md`; planning/preparing → `teaching/generate.md`; practicing → `teaching/coach.md`; reviewing → `teaching/review.md`. Paused/blocked sessions require their recorded reason and resume position.

## Editing boundaries

- In teaching mode, do not edit an exercise's `editable_paths` unless the learner explicitly requests that help. Failing tests are not permission to solve the exercise.
- Generation and validation may write reference/skeleton/mutant assets before assignment. Never overwrite existing learner work when preparing or revising a task.
- Repair environment/provided-file defects transparently. Record the defect and revalidate a new revision if the contract changes; do not disguise solving the learning objective as a repair.
- During coaching, read specs, student diffs, and reports first. Do not open reference solutions unless the teaching need requires it. Do not reveal answers unprompted.
- Do not poll or change code while waiting for learner work. Run checks when requested or as part of an agreed review.

## Records and language

- Formal files, generated exercises, comments, identifiers, and reusable summaries are English. Conversation follows `preferred_interaction_language` (initially `zh-TW`). Preserve raw learner answers in their original language.
- Apply structured learner changes through `state apply` with an expected version; see `docs/state.md`. Save raw explanations in `learner/artifacts/` first.
- Separate self-report from demonstrated evidence; record hint level and uncertainty. A test pass cannot establish understanding. Never fabricate token usage; use null when unavailable.
- New exercises require successful `prepare` and semantic review before practicing. If generation fails, allow at most two automatic repair attempts before recording blocked and discussing a smaller valid task.
- No preset curriculum, external messages, API billing, model switching, or autonomous upstream imports. This is a private repository; preserve learner records and answers.


## Efficient sessions

- Prefer compact status and targeted report fields. Never dump full aggregate JSON or repetitive build logs into context; inspect a failing child log only when needed.
- Give the exact editable workspace link first. Evidence snapshots are generated history, never a learner workspace. If reported work differs from disk, check save/path before reasoning about concurrency.
- Use `.venv/bin/python tools/lab.py check` for the active exercise; confirm command syntax using `--help` before publishing instructions.
- Preserve known host setup. A dependency/network error calls for inspecting the dependency cache, not repeatedly running compiler probes or the whole validation matrix. Retry network access once only if the pinned object is absent.
- Wait 20–30 seconds between build output checks; report only meaningful progress. Do not spawn agents for routine teaching.
- If the learner stops for time/token limits, save a paused resume position and defer questions. Preserve successful test evidence without declaring understanding or completion.
- Run snapshots stay local and ignored by default, per learner preference. Never delete records to reduce Git noise. Explicit archival can force-add the referenced report closure when requested.
