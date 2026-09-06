# Local C++ learning lab

Conversation follows `preferred_interaction_language` (initially zh-TW). Formal
files and reusable summaries are English, except documentation translations;
preserve raw learner answers verbatim.
No preset curriculum, external messages, API billing, model switching, autonomous
upstream imports, or routine teaching agents. Preserve private learner records.

## Documentation languages

English documents in `docs/` are the primary maintenance version; translations
use matching filenames under `docs/<language>/` (currently `docs/zh-TW/`). When
adding, modifying, renaming, or deleting a document, update every supported
language and affected links in the same change. Keep sections, technical meaning,
commands, examples, and historical verification facts aligned. Each document
links to its other language versions; translated links prefer the same language
when available. This rule also applies to any languages added later.

## Entry and routing

For `start`, `continue`, `開始`, `繼續`, or each new teaching step, run
`./lab context --json` once before acting. A completion or review request after
learner work is a new step: refresh even if context was read when assigning or
coaching, because the learner may have run `./lab check` outside the chat. Here
"once" means once per routed step, not once per conversation; do not repeat it
without an intervening learner command, conflict, or other freshness need. Context
includes profile, session/version, active spec, editable source, recent evidence,
report location, integrity and check freshness. Do not separately reread these
files or dump aggregate reports. Read only the returned workflow file; do not
reread an unchanged workflow within the same conversation.

Missing state: `./lab init`. Run `doctor` only on initial environment setup or an
environment failure, not at every new chat. Preserve the known LLVM/cache setup
in `docs/environment.md`. Paused sessions retain their reason and resume position.
Use `./lab session resume --expected-version N --next-action '...'` to resume.

## Teaching boundaries

- Link the exact editable workspace first. Evidence snapshots are never workspaces.
- Do not edit learner implementation unless explicitly requested. Failed tests
  are not permission to solve it. Read student source/spec/reports before references;
  never open a reference just to speed up coaching or reveal answers unprompted.
- Author and validate new assets before assignment; never overwrite learner work.
  Repair provided-file/environment defects transparently; changed contracts need
  a recorded defect, a new revision, and validation.
- If work differs from disk, check save/path first. No polling, editing or tests
  while waiting for learner work. A completion request authorizes review checks,
  but first refresh context so externally run checks can be discovered.
- Decide from that refreshed context: if `check_reusable` is true, reuse the pass
  and do not run `./lab check`; otherwise run it when review is requested. Tests do
  not establish understanding. Accept an explanation already supplied; do not ask
  another question solely to satisfy a phase label.

## Records and efficiency

Use `./lab prepare ID --assign --expected-version N` after authoring and semantic
review. It validates and assigns only on success. At most two automatic generation
repairs; then record blocked and discuss a smaller task.

Save raw answers in `learner/artifacts/`. Use `./lab finish FILE` for an authored
completion bundle (see `docs/state.md`): evidence, review and completion commit
atomically, including from practicing. Other structured changes use `session` or
`state apply`, with the version returned by the last read/write. Do not issue
another status just to repeat that version; refresh after a conflict or intervening
learner command. Keep assistance, uncertainty and self-report distinct. Unknown
usage is null; never convert a usage-window percentage into token counts.

Use documented short commands; consult `--help` only for unfamiliar syntax or
errors. Batch independent reads. Wait 20–30 seconds between build checks and report
only useful progress. For dependency errors inspect the cache; retry network once
only when the pinned object is absent. Never rerun a full matrix to inspect a log.

For time/usage stops, save a paused resume position and defer questions. Run history
stays local and ignored; never delete it for Git noise. Archive only when requested.
Formatting is local (`./lab format`, editor save, patch hook); avoid model-generated
format-only rewrites. Format authored assets before prepare/check. See
`docs/formatting.md` for hook limits and protected paths.
