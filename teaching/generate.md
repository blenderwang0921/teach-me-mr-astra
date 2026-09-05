# Author, validate, assign

Use goals, recent observations and `next_action` from `context`. Choose one principal
objective within the learner's time budget; no fixed curriculum or upstream imports.

1. Copy a suitable `templates/{implementation,debugging}/exercise` into a NEW
   `exercises/ID` and its `instructor` into `.instructor/ID`. Never overwrite work.
2. Replace all placeholders. Define a consequential scenario, exact requirements,
   non-goals, C++20 API, editable/provided paths, platform, seeds and timeouts.
   Map each acceptance check to an exact requirement and public Catch2 test name.
3. Author public tests with independent expected values and deterministic concurrency
   scheduling. Put extra tests in instructor `tests/`. Supply reference, skeleton,
   and objective-specific mutants; each overlay contains exactly editable paths.
4. Complete `validation.json`: semantic approval, every reviewed requirement,
   English assets, limitations, exact skeleton failures, and expected mutant
   detections. Compile-error debugging needs a diagnostic substring; mutant compile
   errors never prove functional test quality. Declare ASan and applicable TSan.
5. Format new assets before publication. Run
   `./lab prepare ID --assign --expected-version N` from planning or the same active
   preparing task. It enters preparing, validates, and assigns only on success.
   Review the result; read targeted child summaries only if needed. Never publish
   an unvalidated task. At most two automatic repairs before discussing a blocker.
6. Link the exact editable file first, explain the task briefly, give `./lab check`,
   and wait. Do not run the learner's failing skeleton as another student check.

Provided-file/test/framework changes invalidate publication. Record defects and
increment the revision before revalidation; preserve learner edits. Finished historical
snapshots remain evidence even if a live ready marker becomes stale after maintenance.
Do not revalidate old completed tasks during routine teaching; revise only if reused.
