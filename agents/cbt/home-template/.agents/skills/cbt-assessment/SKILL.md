---
name: cbt-assessment
description: Administer and score the supplied book's Burns depression checklist, 25-situation Novaco irritability scale, and optional 35-item belief profile. Use for baseline or periodic measurements, scoring answers, and explaining comparable results.
---

# Versioned assessment

Read [administration.md](references/administration.md) for the chosen instrument. The canonical wording, anchors, item order and source pages live in the workspace's `resources/instruments/`. Use `tools/cbt_workspace.py` from that workspace; do not score by mental arithmetic or invent another instrument with the same name.

```bash
python tools/cbt_workspace.py --workspace . list-instruments
python tools/cbt_workspace.py --workspace . instrument burns-depression-25-en-v1
python tools/cbt_workspace.py --workspace . score --input /path/to/assessment.json
```

## Administration

Explain what is being measured, its reference window, and the response options. Offer manageable batches or one item at a time, following the user's preference. Use the single English canonical JSON and translate for the conversation without changing meaning, the response key or the reference window. Discuss confusing examples without substituting another scenario; allow a skip. Never fill an answer from conversational impressions. Store answers in a full-length array using `null` for unanswered items.

Any positive response to depression items 23–25 warrants a direct present-safety conversation, including on a partial form. Do not wait until the remaining questions are complete. Use `$cbt-crisis-support` as indicated. If those items are unanswered, safety is unknown. A zero answer cannot overrule concerning statements elsewhere.

Set `status` to `completed` only when every item has a valid explicit answer. `partial` and `declined` attempts have no total/band and do not reset the schedule. A resumed attempt can update the same attempt ID with an explicit `supersedes` link; do not edit historical answers as if the change never occurred. The tool stores append-only assessment events and uses the latest event per attempt.

## Results

Inspect the scorer output, explain the relevant book band neutrally, and discuss functioning, duration, context and the user's reaction. Never equate a score with a clinical diagnosis or use it to predict suicide. A high, persistent or worsening score increases the importance of professional assessment, but professional help is not conditional on crossing a numeric threshold. Use `$cbt-review` for trends.

Save using the same input through `save-assessment` when storage is enabled. Preserve instrument identity, time window, item answers and completion status. Interpret repeated Novaco scores as within-person observations, not precise evidence of a population percentile or a validated treatment response threshold.

Record `presentation_language` and the actual translated `presented_wording` (item IDs and response anchors). Reuse suitable wording from the previous administration in that language to limit drift. Keep one canonical English definition: conversational translation does not create another instrument file. Do not claim a conversational translation has been independently validated. A substantive change to item content/scoring requires a distinct version; `trend` separates presentation languages and does not pool them into one score change.
