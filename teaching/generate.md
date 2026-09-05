# Choose, generate, and publish one exercise

Read goals, recent relevant observations, and session next_action. Select one principal learning objective. Prefer a self-contained problem for v1. `references/catalog.json` starts empty; no upstream adapter is implemented.

## Author assets

1. Select `templates/implementation` or `templates/debugging`. Copy its `exercise/` files into a new `exercises/<id>/` directory and its `instructor/` files into `.instructor/<id>/`. Replace every placeholder. Never copy over an existing learner workspace.
2. Define a scenario whose constraints affect the solution, explicit requirements/non-goals, and named acceptance checks. Every check references an exact requirement string and an exact public Catch2 test name. Review non-executable requirements explicitly.
3. Define a C++20 API (C++23 only when needed), platform, exact editable/provided file paths, fixed seeds, bounded test/command timeouts, and required sanitizers. ASan implies ASan+UBSan; declare TSan for applicable concurrency objectives after platform checks.
4. Write public tests, a reference implementation, and one or more objective-specific mutants. Additional acceptance tests go in `.instructor/<id>/tests/`; they run against reference, mutants, and student snapshots. Use independent expected values/oracles where possible, boundary cases, reproducible failure inputs, and deterministic synchronization rather than sleep-based races.
5. Create the learner skeleton by removing only the objective's implementation. Each `reference/`, `skeleton/`, and `mutants/<id>/` tree must contain exactly the editable file paths, including any editable design/experiment files. They overlay an isolated copy of the provided files.
6. Complete `validation.json`: explicitly approve semantic review, list all reviewed requirements and limitations, confirm English formal assets, identify expected skeleton failures, and map each mutant to the checks that must catch it. For compile-error debugging, declare `compile_failure` and an expected compiler diagnostic substring. Mutant compile failures never prove functional test quality.

The templates are deliberately unpublishable until completed. No script calls a model to fill missing content. Requirements and test names are not placeholders once a task is assigned. Report costs only when directly available; do not estimate hidden model usage from visible text.

## Validate and assign

Save the spec before setting the session to preparing with its id and revision. Run `prepare <id>`. Review the compact validation report, mapping, failure diagnoses, and stated limitations. The tool publishes ready only after reference/debug/sanitizer passes, exact expected skeleton behavior, and expected mutant detections. Failed preparation enters blocked when it is the active preparing task.

Allow at most two automatic generation repairs. If still blocked, preserve diagnostics and explain the blocker or propose a smaller self-contained task. Do not hand over an unvalidated exercise.

When ready, apply preparing → practicing and point the learner to the README and editable files. Explain how to run `check`. Wait for the learner's implementation.

## Revisions and defects

Do not relax acceptance because the learner failed. When the exercise is wrong, save a durable defect explanation and review, return practicing/reviewing → preparing, increment `spec.revision`, update affected assets, and revalidate. Clear an obsolete `last_report_id` when changing revisions. Preserve student work and explicitly discuss API changes that require their edits.

Implementation changes only affect a run's source hash. Provided files, tests, reference/skeleton/mutants, schemas, and execution-tool changes invalidate the contract. A previously published contract cannot be republished under the same revision after such a change.

