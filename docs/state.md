# State transactions

All structured records have `schema_version: 1`. Schemas live in `schemas/`; fields outside the declared interface are rejected. `session.version` is the optimistic concurrency counter, independent of exercise revision.

`state apply <file>` accepts `schema_version`, `expected_version`, and optional `profile`, `session`, `evidence`, and `reviews`. Profile/session are complete replacement objects; evidence/reviews are new records. When supplying a session, set its version to `expected_version + 1`. An evidence-only/profile-only transaction also increments the stored session version. Read `status --json` immediately before constructing the update.

Example first transition after `init`:

```json
{
  "schema_version": 1,
  "expected_version": 0,
  "session": {
    "schema_version": 1,
    "version": 1,
    "phase": "planning",
    "current_exercise_id": null,
    "exercise_revision": null,
    "last_report_id": null,
    "pending_questions": [],
    "next_action": "Choose one short calibration task based on the saved interview.",
    "resume_phase": null,
    "reason": null,
    "completed_exercises": []
  }
}
```

Save the update file and run `python tools/lab.py state apply <file>`. The tool validates the whole transaction before saving a redo journal, replacing state files, and removing the journal. Every lab state command holds a nonblocking OS lock; a crashed writer releases its lock automatically. Recovery replays a committed journal before accepting new work.

## Phases

The normal path is onboarding → planning → preparing → practicing → reviewing → planning. Staying in the same phase is allowed. Paused records retain their original `resume_phase` and a nonempty reason; resuming clears both. Preparation validation failures record blocked with a reason and preserve the preparing resume position. Blocked work can return to preparing or planning.

Preparing/practicing/reviewing require an exercise id and revision. Practicing/reviewing additionally require a current ready marker backed by durable validation evidence. A student test failure stays practicing. A documented exercise defect may return practicing/reviewing to preparing with an accompanying review; new contracts need a new revision.

`check` saves reports independently of teacher conclusions. A default check for the active revision updates `last_report_id` and increments the state version without changing phase. Diagnostic `--preset` runs do not update it.

## Completion and observations

To complete an exercise, finish its review (from practicing or reviewing) into planning and append `{ "id": "exercise-id", "revision": 1, "report_id": "run-…" }` to `completed_exercises`. The report id must equal the previous session's last qualifying report. Include a review for the same revision, with the learner explanation and durable references. Completion requires the previous session's successful default student check, unchanged student files, and a valid ready contract. Existing completion history cannot be removed. CI reruns the recorded source/test snapshot, so a later live revision does not erase or misrepresent the completed version.

Evidence entries include id, timestamp, exercise id/revision, skill, observation, references, hint level (0–5), teacher interpretation, low/medium/high confidence, and nullable `supersedes`. Self-report stays in profile. References must be existing files below `evidence/`, `learner/artifacts/`, or `learner/reviews/`; reports under `reports/` and live exercise source are not durable references.

Save raw explanations before submitting their referencing transaction. A run's `source_hash` covers its actual executed source snapshot, including additional tests. `student_source_hash` covers the student's original exercise tree so added acceptance tests do not distort source freshness checks. Reports are never evidence of understanding by themselves.

`status` checks reference existence and publication integrity. It reports missing support rather than silently treating an orphaned observation as supported. Preserve all referenced evidence on disk. Run snapshots are ignored by default to keep learner changes clear; a Git-only backup requires explicitly archiving referenced reports and their child snapshots with `git add -f`. Never delete evidence as routine cleanup.

## Short commands (preferred)

Use `./lab context --json` once at entry. It combines profile/session, active spec
and bounded editable source, two recent observations, compact report profiles and
source/contract freshness. `check_reusable` means a successful required-profile
student check matches the active source and contract with no integrity errors.
It does not assert understanding. No compiler is run by context.

Use the returned version; successful mutations return the new version. Read again
only after an intervening command, conflict, or a meaningful need for fresh context.

```sh
./lab prepare ID --assign --expected-version N
./lab session reviewing --expected-version N --next-action 'Await an explanation.'
./lab session paused --expected-version N --reason 'Time limit' --next-action 'Resume the saved review.'
./lab session resume --expected-version N --next-action 'Continue the saved review.'
./lab finish /tmp/completion.json
```

`prepare --assign` requires authored assets and approved semantic review. It enters
preparing from planning, runs the existing publication gates, and enters practicing
only on success. Failures preserve the preparing/blocked resume position.

The completion bundle is `{ "schema_version": 1, "expected_version": N,
"review": REVIEW, "evidence": [OBSERVATION] }` using `review.schema.json` and
`evidence.schema.json`. Save and reference the original answer in learner/artifacts
first. The review contains the English explanation summary and concrete next action.
`finish` builds the session replacement and commits all records atomically; it
requires a nonempty evidence array, matching revision, durable answer reference,
fresh default pass, valid ready marker and unchanged source/contract. It may finish
from practicing directly when the explanation is already available; the same
completion gates apply as when leaving reviewing. It increments the version once.
Legacy `state apply` remains available, including for profile changes and defects.

A framework change can make historical live ready markers stale. Preserve completed
records and their snapshots; do not republish an old revision to disguise the change.
The next new exercise is validated against the new framework. Full `ci` still
requires live ready contracts; it is not a routine teaching-resume command.
