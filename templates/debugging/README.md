# Debugging template

Copy `exercise/` into a new exercise workspace and `instructor/` into its matching instructor directory. Replace identifiers, APIs, placeholders, tests, and validation expectations using `teaching/generate.md`.

Provide a reproducible defect and a useful diagnostic task. Keep the learner's repair localized. Prefer a functional bug; for an intentional compilation defect, declare compile_failure and its expected diagnostic in validation.json and explain it in the student README.

Every variant must contain exactly the editable file set. These placeholders deliberately fail semantic approval and cannot be published unchanged. The tool does not infer a task from this template.
