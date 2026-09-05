# Material candidates

The catalog starts empty. V1 supports self-contained exercises and stores material metadata for later work; it does not execute upstream adapters or claim that any project has been validated.

To record a candidate, create `materials/<material-id>/manifest.json` conforming to `schemas/material.schema.json` and add its id to `catalog.json`. Record source URL, license/commit when known, intended mode, learning targets, prerequisites, dependencies, resource requirements, and proposed adapter paths. Unknown candidate values remain null rather than guessed.

Modes are `reference`, `subsystem`, and `upstream`. Status is `candidate`, `ready`, or `blocked`. A future readiness workflow must bind a fixed commit to source/license review, exact environment, reproducible baseline, and durable validation report. Do not mark a candidate ready merely because its upstream project has tests.

Future adapters must preserve the upstream build system, reuse checked-out sources, and back up student modifications before any workspace reset. No reset command or autonomous material fetch workflow is implemented in this version.

