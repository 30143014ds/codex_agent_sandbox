# Engineering Agent Instructions

## Goal

This project is small enough (solo, phased build) that a multi-tier agent
hierarchy isn't worth the overhead. Keep it to two things:

- `scout` — used only to keep large, mostly read-only work out of the main
  agent's own context. The trigger is size/cost, not task type.
- Everything else — implementation, debugging, refactors, tests, and yes,
  architectural/design decisions — happens in the main agent thread.

There is no `architect` subagent. When a decision is genuinely hard,
ambiguous, or expensive to undo, the main agent does not call a stronger
model to decide it — it stops and asks the user. Architectural taste and
tradeoffs on this project are the user's call, not something to automate
away.

---

## `scout` — triggered by context cost, not task type

Delegate to `scout` when doing the work inline would burn a lot of the main
agent's context for little reasoning value — regardless of whether that
work is "investigation," "implementation," or anything else. Concretely:

- reading/searching a large number of files or a large codebase area
- reading long logs or long error output
- tracing something across many files/services
- summarizing an unfamiliar or large chunk of code before touching it
- any pull of bulk data/output that is only needed in summarized form

Do NOT delegate to `scout` just because a task is "investigation-flavored."
A quick, targeted look at one or two files the main agent doesn't already
have loaded is cheaper to just do directly than to hand off. The question
is always: "would doing this inline meaningfully bloat my context for
information I only need in summary?" If yes, use `scout`. If no, just do
it.

`scout` reports back a summary, not raw dumps — the point is to protect the
main agent's context, so pulling everything back verbatim defeats the
purpose.

---

## Everything else: the main agent

By default, the main agent does the actual engineering work itself, once
`scout` (if it was needed at all) has supplied a summary:

- feature implementation
- bug fixes, including moderately tricky ones
- multi-file changes
- refactors
- tests
- Docker/deployment config
- normal code review of its own diff

This is the default path. Most tasks on this project should never leave
the main agent thread.

---

## When to stop and ask the user instead of deciding alone

There is no automated escalation to a "smarter" agent for hard problems.
Instead, the main agent pauses and asks the user when it hits something
like:

- an architecture or schema decision (e.g. how the DB, CalDAV, and Garmin
  sync pieces should relate)
- a genuinely ambiguous requirement where more than one reasonable
  interpretation exists
- a choice that would be expensive or awkward to reverse later
- repeated failed attempts at the same bug, where the next step is a
  judgment call about approach rather than more debugging
- anything security-sensitive where the "right" tradeoff depends on how
  the user plans to run/expose this

Ask a specific, concrete question with the main options and their
tradeoffs laid out — don't just say "this is hard, what do you want to
do?" Give the user something to react to.

If the user isn't available and the decision truly can't wait, the main
agent may do a one-off deep-reasoning pass itself (not a standing
subagent, just thinking harder) and clearly flag the assumption it made so
the user can correct it later.

---

## Proactive delegation

### Feature implementation

1. If understanding the relevant code would burn significant context,
   `scout` summarizes it first.
2. Main agent implements the feature directly.
3. Main agent verifies integration and completeness itself.

### Bug fix

1. If reproducing/tracing the bug means digging through a lot of code or
   logs, `scout` gathers and summarizes the evidence.
2. Main agent attempts the fix directly.
3. If it's not converging, or the right fix is genuinely a design
   question, stop and ask the user rather than escalating to another
   model.

### Large investigation

Run multiple independent `scout` agents in parallel when their areas don't
overlap, then the main agent synthesizes before doing anything else.

### Multi-part change (e.g. adding a new sync/service layer)

Parallel `scout` agents can map independent existing components first. The
main agent then implements sequentially — there's no separate
implementation subagent to parallelize across, and for this project's
size that's fine.

---

## Parallelism

Parallel `scout` agents are fine when investigation areas are genuinely
independent (e.g. "how does the CalDAV service talk to the DB" and "how
does the Garmin client currently authenticate" — unrelated enough to
split).

Avoid parallel `scout` agents when:

- one investigation depends on another's result
- the areas overlap significantly
- coordination cost exceeds the benefit

Never parallelize the actual implementation across multiple agents on this
project — one main agent, one thread, sequential.

---

## Main-agent responsibility

The main agent owns the whole task:

- understanding what the user actually asked for
- deciding whether any part of it is expensive enough context-wise to
  hand to `scout`
- doing the implementation itself
- recognizing when it's hit a decision that isn't its call to make, and
  asking the user instead of guessing or escalating to another model
- reviewing its own diff critically before calling something done
- verification
- integration

Because the same agent writes and reviews the code, be deliberately
skeptical of your own diff — there's no separate implementer to catch what
you missed.

---

## Verification

Implementation isn't done until it's been reasonably verified. Depending
on what changed:

- unit / integration / end-to-end tests
- type checking
- linting
- build (including Docker build, given this project's services)
- runtime smoke test
- checking logs

Lean on automated verification over self-assessment wherever possible,
since self-review is the main agent's only check on itself here.

If verification fails, investigate it yourself before deciding whether
it's actually a "stop and ask the user" situation.

Do not hide failed verification.

---

## Cost discipline

- Don't send a quick, targeted look at one or two files to `scout` — just
  read them directly.
- Don't ask the user about something that has one obviously correct
  answer — that's not what "stop and ask" is for.
- Don't do a "one-off deep-reasoning pass" as a substitute for asking the
  user when the user is actually available; it's a fallback, not a
  shortcut to avoid a question.
- Don't repeatedly retry the same failing approach hoping it works —
  either change approach or ask.

---

## Completion

Before reporting something done:

1. Confirm the actual request was satisfied.
2. Review any `scout` summaries you relied on for accuracy.
3. Check your own diff.
4. Run appropriate verification.
5. Say what verification wasn't possible.
6. Flag any assumption you made (especially any made via the one-off
   deep-reasoning fallback instead of asking) so the user can correct it.