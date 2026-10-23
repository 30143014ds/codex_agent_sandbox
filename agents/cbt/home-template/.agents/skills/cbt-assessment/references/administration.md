# Instrument administration and interpretation

## Burns depression: `burns-depression-25-en-v1`

Source: English 25-item checklist reproduced by SSM Health and cross-checked with the supplied book, chapter 2, tables 2.1–2.2. The form specifies the past week including today. English anchors are 0 not at all, 1 somewhat, 2 moderately, 3 a lot, 4 extremely. They measure degree. Preserve that meaning when translating, rather than inheriting frequency-like labels from the Russian edition. English source URLs are stored in the canonical JSON.

Book bands: 0–5 no-depression range; 6–10 normal-but-unhappy range; 11–25 mild; 26–50 moderate; 51–75 severe; 76–100 extreme. These are historical book screening bands, not a diagnosis or an automatic treatment decision. Offer at least weekly during active self-help. Items 23–25 concern suicidal thoughts, wishes and plans; see the global safety instructions for direct follow-up independent of the sum.

Ask about duration, functioning, supports and treatment when they affect interpretation. Avoid reproducing categorical assurances from the book that a low score means the user is safe or that self-help alone will suffice.

## Novaco: `novaco-25-en-v1`

Source: English NAI-25/clinical reproductions cross-checked with chapter 7. Rate the general imagined reaction to each of 25 potentially provoking situations: 0 little/no irritation, 1 a little anger, 2 moderate, 3 quite angry, 4 very angry. The total is 0–100. This is the book-compatible short situational version, not a full contemporary Novaco Anger Scale/Provocation Inventory or a symptom-frequency checklist. A clinical mirror duplicates anchor 3 and adds a past-week instruction; do not copy those errors. Use the confirmed 0–4 general-reaction key. Source normalization notes are explicit in the JSON.

Book ranges: 0–45 very low, 46–55 below the book's reference average, 56–75 the book's reference average, 76–85 above that reference, 86–100 very high. Describe neutrally; omit teasing labels, claims about honesty, health consequences or precise population membership. A fortnightly repeat is a configurable workflow choice, not a frequency established in this source. For individual anger episodes use separate 0–100 intensity, frequency/context and behavior observations.

Some situations are dated. Explain them if needed while retaining the canonical scenario. Substituting a new scenario creates an adaptation that must be distinguished in records.

## Belief profile: `das-burns-35-en-v1`

Source: English 35-item Burns form hosted by Bruce Whealton, with a second English form and the supplied book (chapter 10) used for cross-checking. This is Burns' selected/adapted belief questionnaire, not the full original Weissman DAS. Ask how the user generally thinks. Strong agreement = -2, slight agreement = -1, neutral = 0, slight disagreement = +1, strong disagreement = +2. Sum consecutive groups of five into approval, love, achievement, perfectionism, entitlement, omnipotence and autonomy; each domain ranges -10 to +10. There is no overall severity total or diagnostic cutoff. Corrected typographic defects in the English mirror are listed in the JSON.

Use it to choose optional topics after initial stabilization; it is not mandatory and has no automatic repeat interval. Treat the domains as discussion prompts, not fixed traits. Historical wording about personal control and mood can oversimplify biological and social influences; a domain score does not establish that someone causes or controls all their symptoms.

## Input and revision

The workspace tool accepts an `instrument_id`, `status`, `answers` and optional ISO `recorded_at`, `attempt_id`, `supersedes`, `context`, `window_start`, `window_end`, `presentation_language` and `presented_wording`. Inspect the schema for fields. For depression the default window covers the local recorded date and preceding six calendar days. Novaco/DAS use their general-response window, not fabricated start/end dates. When a partial form is resumed later, retain its original reference window or start a new attempt explicitly.

The scorer checks lengths, integer response values, completion and instrument version. It flags answered positive safety items without making a risk category. A saved revision must name the latest event ID in `supersedes` and match its instrument. Repeating a questionnaire today is a new attempt; correcting/resuming an existing one is a revision.
