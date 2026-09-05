# Review and complete

Use a fresh successful default check and the matching learner source. Accept a
previously supplied explanation of a choice, invariant, counterexample, or tradeoff.
Ask one focused question only if that evidence is missing. Tests alone never suffice.

Save the verbatim answer in `learner/artifacts/`. Write one completion bundle:
`schema_version`, `expected_version`, `review`, and `evidence` (nonempty array).
Review/evidence use existing schemas; see `docs/state.md` only when authoring a new
bundle shape. Summaries are English; raw answers retain their language. Record
actual assistance and uncertainty. Do not credit teacher-supplied corrections as
independently demonstrated knowledge.

Run `./lab finish FILE`. It validates the report, source/contract freshness, ready
publication, references and version, then commits review/evidence/completion in one
transaction. It works from practicing or reviewing; no ceremonial transition or
post-success status call is needed. Failed validation writes no partial completion.

Set one concrete evidence-based next action: isolate a concept gap, reduce API
friction, transfer assisted work with fewer hints, or add one adjacent constraint.
Completion means this exercise is complete, not that a skill is mastered. Corrections
append observations with `supersedes`; never rewrite history. Do not automatically
start another exercise when the learner is stopping.
