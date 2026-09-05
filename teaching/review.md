# Review evidence and choose the next action

Read the latest qualifying student report and source version. Ask the learner to explain a key choice, an invariant, a counterexample, or a changed constraint. For system design, discuss capacity assumptions, alternatives, failure conditions, and experiment limits; a unit-test pass is not proof of architectural quality.

Save the raw answer in `learner/artifacts/`, retaining its language. Prepare an English review with the learner explanation, evidence references, assistance level (in accompanying observations), and a concrete next action. Use `state apply` for the review, evidence entries, session transition, and completed exercise record together.

Completion requires a current successful default `check`, a ready contract, and a review containing the learner's explanation. It means the exercise is complete, not that a skill is mastered. Do not invent calibrated probabilities; confidence is a provisional low/medium/high teaching judgment. Append corrections using `supersedes` rather than rewriting old observations.

Choose the next step from evidence:

- Concept gaps: isolate one counterexample and reduce unrelated complexity.
- API friction: offer a short reference while keeping the conceptual challenge.
- Assisted completion: schedule a different context with reduced hints.
- Independent implementation and explanation: add one constraint or adjacent concept.
- Exercise defect: document and revalidate the task; do not score the defect against the learner.

Persist reviewing → planning with a concise `next_action`. Clear current exercise/revision when moving to an unselected task. Keep a prior report only as historical context; set it to null when choosing a new revision. On a new session, read this state rather than reconstructing the whole conversation.

