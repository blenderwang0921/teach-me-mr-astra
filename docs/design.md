# Local C++ teaching lab — implemented v1 design

English | [繁體中文](zh-TW/design.md)

The original Traditional Chinese handoff is [design.md](../design.md). This English document is the primary implementation design for the first three delivery stages. Design intentions and verified behavior are distinguished from future learning outcomes.

## Purpose and boundaries

The learner practices C++ implementation, debugging, algorithms, concurrency, and system-design judgment locally. The teacher uses brief interviews, short calibration tasks, and implementation evidence to choose one appropriate next challenge. The goal is transfer to new contexts with less assistance, not test scores or rankings.

There is no web interface, preset course, cloud executor, extra API key, automatic model routing, or mastery classifier. Generated exercises appear only after an interview. Implementation and debugging templates are authoring scaffolds; the small counter fixture is a framework test, never an assigned lesson.

The repository is private by default and tracks learner history, generated tasks, instructor assets, and durable evidence. Public release should export the framework without private records and answers. Instructor directories are an accidental-disclosure barrier, not access control.

## Responsibilities

| Component | Owns |
| --- | --- |
| Teacher | Interview, objective selection, semantic review, diagnosis, hints, interpretation, next action. |
| Teaching documents | Stage-specific policies, language, assistance levels, and editing boundaries. |
| Learner state | Goals, preferences, separate self-reports/observations, current phase, durable references. |
| Exercise contract | Scenario, API, requirements, test mapping, editable/provided paths, revisions, limits. |
| Fixed tools | Validation, process control, reproducible builds/tests, reports, state transactions. |

Teacher decisions are not replaced with heuristics in the CLI. Scripts never generate missing exercises through a model. A correct reference is necessary but insufficient: the teacher reviews semantics and the tool verifies objective-specific faults and learner skeleton behavior.

All formal documents, generated artifacts, code comments, and reusable summaries are English, except documentation translations. English documents in `docs/` are the primary maintenance version; translations use matching filenames under `docs/<language>/` (currently `zh-TW`). Additions, edits, renames, and deletions must update all supported languages and affected links in the same change, including future languages. Interaction language is independent and initially `zh-TW`. Original learner answers and upstream notices retain their language.

## Build and execution

The CLI uses Python and JSON Schema. CMake/Ninja create one exercise test target from `src/**/*.cpp`, `tests/**/*.cpp`, and `include/`. Exercises do not supply arbitrary alternative build adapters in v1. C++20 is default and C++23 is selected per target. Catch2 is fixed to an immutable v3.8.1 commit and cached outside tracked source.

Debug, release, ASan+UBSan, and separate TSan profiles are available. Each requested profile must compile and run a real capability probe. Unsupported required checks are failures, not successful skips. Exact compiler and standard-library details are retained per run. Platform-specific tasks declare Linux/macOS explicitly; Windows is deferred.

CTest discovers named public checks, rejects zero/missing tests, applies bounded timeouts, and emits JUnit evidence. Every declared seed is executed. Build parallelism and process timeouts are bounded; process-group termination avoids abandoned descendants. Tests are not an isolation sandbox, and memory quotas are not enforced in v1.

## Contracts and evidence

Schemas cover profile, session, exercise, validation, evidence, review, material, catalog, ready marker, state update, and run report. Structured data uses schema version 1. Unknown public fields are rejected; raw learner text and preferences remain flexible where appropriate.

Profile stores goals, time, platform, language, preferences, and self-reported experience. Evidence observations are append-only, carry skill/revision/hint level, and refer to durable code snapshots, reports, or learner explanations. Teacher confidence is provisional, not statistically calibrated. Corrections append a new observation referencing its predecessor.

Reports separate the executed source hash from the original student-tree hash. This preserves provenance when extra instructor tests are overlaid. Full logs and builds are disposable; compact outcomes, bounded failure diagnostics, exact seeds, and executed source snapshots remain tracked. Missing support is reported as an integrity issue. Usage fields remain null when trustworthy measurements are unavailable.

State changes require one OS-held writer lock and an expected session version. After validation, a redo journal records complete replacement contents, then files are atomically replaced. On restart, the journal is replayed under the same lock. Evidence history is appended logically even though its file is replaced atomically. Conflicts fail rather than silently overwrite another session.

## Publication and revision rules

Author the scenario and observable requirements first, then reference implementation, tests, mutants, and skeleton. Reference/skeleton/mutant directories contain exactly the editable paths and overlay isolated copies of provided files. Templates are deliberately unpublishable until their placeholders and semantic-review flags are replaced.

Preparation validates the schema and path ownership, runs reference debug and required sanitizer profiles, checks the skeleton's declared functional failures (or explicit debugging compile failure), and requires each mutant to fail its designated tests. Compilation failure alone never proves a functional mutant was detected. Public acceptance tests and additional instructor tests run against the student too.

Successful publication saves a ready marker bound to exercise id/revision, contract hash, and durable validation report. The contract hashes provided files, specification, instructor assets, schemas, and execution/build tooling; normal editable-file changes do not invalidate it. A changed published contract requires an incremented revision and explicit revalidation. Repeated preparation cannot overwrite learner work.

Student checks use immutable snapshots and record code/contract changes during execution as integrity failures. Single-profile checks are diagnostic. Only a default check covering all required profiles updates the session's qualifying report.

## Teaching lifecycle

The normal sequence is onboarding → planning → preparing → practicing → reviewing → planning. Paused sessions retain their resume phase and reason. Failed preparation blocks assignment; a learner test failure remains practicing. Documented exercise defects can return the task to preparing for a new revision without blaming the learner.

The teacher begins by reading state and only the relevant stage guide, active contract, recent observations, and reports. It does not reload an entire conversation or continue polling while the learner works. Hints range from a prediction question through counterexamples, concepts, pseudocode, and an explicitly requested full solution. Assistance is recorded honestly.

After passing tests, the learner explains a decision or predicts a changed requirement. Completion requires that explanation, a review, current successful required-profile evidence, and unchanged student files. It does not establish mastery. A later task should test transfer under a different context and lower assistance.

System-design exercises add a design note and reproducible load/failure experiments around one executable component. Capacity estimates and tradeoffs require teacher review. Unit tests cannot certify an overall architecture.

## Verification and deferred work

Behavioral tests focus on recovery, version conflicts, append-only evidence, path ownership, contract invalidation, failure classification, and publication gates. A real C++ integration fixture covers initialization through a hint, simulated learner fix, explanation/review, deletion of full logs, and restoration in a new process. These checks verify tooling, not a human learning outcome.

GitHub Actions configures Linux Clang/GCC validation and checks declared-complete student work; unfinished student tasks do not fail framework CI. Remote results must be reported separately from local checks.

Material manifests/catalogs support later candidate curation, but upstream execution and reset adapters are deferred. A future material must pin its source/commit, preserve licensing, record an exact environment, and demonstrate baseline reproducibility before becoming ready. The first version does not claim any validated upstream project.

Token accounting, a ten-session cost review, optional workers, a large material library, scheduling, and Windows support remain later work. No subscription quota or model name is embedded in the teaching rules. Learning success still requires actual independent implementation and explanation across new scenarios.
