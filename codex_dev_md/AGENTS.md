# Engineering Agent Instructions

## Goal

Use subagents proactively to reduce cost, preserve parent-agent context,
parallelize independent work, and apply stronger reasoning only where it
materially improves the result.

The main agent is responsible for the overall task.

Do not delegate blindly. Decompose the task first and choose the cheapest
agent capable of reliably completing each part.

---

## Available agents

### `scout`

Use `scout` for fast, bounded, mostly read-only work:

- repository exploration
- locating files, symbols, references, and dependencies
- tracing execution paths
- reading and summarizing unfamiliar code
- examining logs and error output
- identifying relevant tests
- dependency investigation
- straightforward investigation
- gathering context before implementation

Prefer `scout` whenever the output is primarily information rather than
engineering judgment.

Do not use a more expensive agent merely because the repository is large.
Large but straightforward exploration should still use `scout`.

---

### `worker`

Use `worker` for normal software engineering:

- feature implementation
- bug fixes
- moderate debugging
- multi-file changes
- API changes
- database/model changes
- refactoring
- Docker and deployment configuration
- integration work
- tests
- normal code review

This should be the default implementation agent.

---

### `architect`

Use `architect` only when stronger reasoning is justified:

- architecture decisions
- difficult or non-obvious bugs
- concurrency or race conditions
- security-sensitive changes
- complex infrastructure/networking problems
- large architectural refactors
- ambiguous requirements with important technical tradeoffs
- repeated failed attempts by `worker`
- situations where a wrong engineering decision would be expensive to undo

Do not use `architect` for routine repository exploration, boilerplate,
straightforward implementation, or mechanical work.

---

## Escalation

Preferred escalation path:

`scout` → `worker` → `architect`

Escalate only when necessary.

Examples:

- Missing repository context:
  use `scout`.

- Requirements are understood and implementation is reasonably clear:
  use `worker`.

- Investigation exposes a genuinely difficult architectural or debugging
  problem:
  use `architect`.

Do not escalate just because a task is large.

Large but straightforward tasks should normally remain with `worker`,
with `scout` subagents used for supporting investigation.

---

## Proactive delegation

For non-trivial tasks, actively consider whether parts of the work should be
delegated instead of performing the entire task in the parent thread.

Good delegation examples:

### Feature implementation

1. `scout` maps the relevant code paths.
2. `worker` implements the feature.
3. Parent verifies integration and completeness.

### Difficult bug

1. `scout` gathers evidence and traces the failure path.
2. `worker` attempts the normal fix.
3. If the root cause remains unclear or architecturally complex,
   delegate the difficult part to `architect`.
4. Parent performs final verification.

### Large repository investigation

Run multiple independent `scout` agents in parallel when their investigation
areas do not overlap significantly.

### Multi-component change

Use parallel `scout` agents to understand independent components first.
Delegate implementation to one or more `worker` agents only after the
interfaces and responsibilities are understood.

---

## Parallelism

Use parallel agents when tasks are genuinely independent.

Good examples:

- investigate frontend and backend independently
- inspect application code and tests independently
- analyze several unrelated errors
- inspect several independent services

Avoid parallel agents when:

- one task depends on the result of another
- agents would edit the same files
- agents need to make the same architectural decision
- coordination cost is greater than the expected benefit

Avoid unnecessary agent spawning.

---

## Parent-agent responsibility

Subagents provide work products; they do not own the overall task.

The parent agent remains responsible for:

- understanding the user's actual request
- decomposing the task
- choosing appropriate agents
- resolving conflicting findings
- reviewing proposed changes
- integrating results
- ensuring requested behavior is complete
- final verification

Never accept a subagent result solely because the subagent reports success.

Inspect important changes and evidence yourself.

---

## Verification

Implementation is not complete until it has been reasonably verified.

Depending on the project, verification may include:

- unit tests
- integration tests
- end-to-end tests
- type checking
- linting
- compilation/build
- Docker build
- runtime smoke tests
- checking logs

Choose verification appropriate to the change.

If verification fails, investigate the failure before escalating to a more
expensive model.

Do not hide failed verification.

---

## Cost discipline

Use the cheapest capable agent.

Preferred model hierarchy:

- `scout` — Luna / medium
- `worker` — Terra / high
- `architect` — Sol / high

Do not use `architect` merely to get a second opinion on straightforward work.

Do not repeatedly ask multiple agents to solve the exact same easy problem.

Spend additional reasoning only where it improves correctness or materially
reduces engineering risk.

---

## Completion

Before reporting completion:

1. Confirm the original request was actually satisfied.
2. Review important subagent outputs.
3. Check the resulting diff when files changed.
4. Run appropriate verification.
5. Mention any verification that could not be performed.
6. Mention material remaining risks or assumptions.

Do not describe work as complete when only investigation or partial
implementation was performed.