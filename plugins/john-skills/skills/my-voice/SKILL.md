---
name: my-voice
description: Writes or rewrites content in the user's own voice by applying an existing `voice-profile.yaml` (weights, variability, register) to the requested piece. Use when the user asks for something written or edited to sound like them — "write this in my voice", "rewrite this the way I'd say it", "make this sound like me", "use my voice profile", "draft this in my style" — including emails, posts, essays, proposals, and other prose. This skill READS the profile and never modifies it; use the build-my-voice skill to create or update the profile itself.
---

# my-voice

## Purpose

Write or rewrite content in the user's voice using the existing `voice-profile.yaml`.

This skill does **not** analyze the user's historical writing.

It does **not** modify the voice profile.

`voice-profile.yaml` is read-only.

## Required Input

Load:

`voice-profile.yaml`

If the profile does not exist, do not attempt to reconstruct the user's voice from memory or from unrelated context.

Ask the user to provide the file directly or via URL.

The file comes in two shapes. Current profiles are a mapping with a `profile:` header and a `features:` list. Older ones are a bare list of features with no header. Read either. When there is no header, treat the corpus as undescribed rather than assuming it was broad.

## Voice Model

Each feature in the profile contains:

- `weight` — how important the feature is to the user's recognizable voice
- `variability` — how much the feature naturally changes between writing contexts

Treat these as tendencies, not binary rules.

A feature may also carry `author_confirmed: true`. That feature was not inferred from writing samples — the author stated it directly. Treat it as the most reliable thing in the file.

## Author Rulings

The `profile:` header may carry an `author_rulings` list. Each entry records a characteristic the author was asked about and rejected: something an earlier analysis inferred from their samples and the author said was wrong.

A rejected ruling is a constraint on you, not a suggestion. If a ruling says the author does use semicolons, do not avoid semicolons — and do not quietly reintroduce the rejected behavior because the profile's other features seem to lean that way.

Rulings usually exist because a corpus made an absence look deliberate when it was an accident of length, format, or subject. They are the corrections the samples could never have produced.

The header may also carry `open_questions` — inferences nobody has confirmed yet. Treat any feature they bear on as soft, and do not raise it above its written weight.

## Context

Before writing, infer the appropriate register from the requested artifact.

Consider:

- audience
- purpose
- medium
- subject
- desired formality
- expected length

Do not confuse register with voice.

Check the requested register against `profile.corpus`. When the request falls in `not_represented` — a long technical explanation from a profile built entirely on short public posts — the profile's high-weight, low-variability features still apply, but its contextual features have no evidence behind them for this kind of writing. Extrapolate from the stable core, hold the contextual features loosely, and invent nothing to fill the gap. It is worth telling the user, outside the artifact, that the register was not in the corpus.

The same person may write differently in:

- an executive proposal
- an email
- a technical explanation
- an essay
- a social post
- an informal message

while retaining the underlying characteristics of their voice.

## Feature Strength

Use each feature's weight as its baseline influence.

Adjust that influence according to its variability and the current context.

Conceptually:

```text
effective strength =
    weight
    × contextual adjustment
    × bounded variation
```

Do not calculate this mechanically unless useful.

It is a reasoning model for applying the profile.

### Stable Features

High-weight, low-variability features should remain strongly represented across most writing.

These constitute the core voice.

### Contextual Features

High-variability features should move substantially according to the task.

For example, humor may be prominent in an essay and almost absent from a contract proposal without either piece ceasing to sound like the same writer.

## Variation

Introduce modest variation when applying variable features.

Do not produce the exact same stylistic configuration every time.

Variation should primarily affect features with higher `variability`.

Features with low variability should receive little or no random modulation.

Never allow randomness to overpower a high-weight, stable feature.

Features carrying `author_confirmed: true` are not candidates for suppression. Vary how they surface; do not vary whether they do.

The purpose of variation is to avoid making the user's voice feel formulaic.

## Writing Procedure

1. Understand the requested artifact.
2. Determine its appropriate register.
3. Load the complete voice profile, header included.
4. Note the author rulings, and whether `corpus` covers this register.
5. Identify the highest-weight stable characteristics and the author-confirmed ones.
6. Determine which variable characteristics fit this context.
7. Apply modest variation to those characteristics.
8. Write the content.
9. Review the draft against the voice profile and its rulings.
10. Correct conspicuous deviations.
11. Return the finished content.

Do not expose this process unless requested.

## Priority

When stylistic characteristics compete, prioritize:

1. explicit instructions in the current request
2. semantic accuracy
3. author rulings and `author_confirmed` features
4. high-weight, low-variability voice features
5. contextual appropriateness
6. high-weight, high-variability features
7. lower-weight features
8. stochastic variation

An explicit instruction such as "make this unusually formal" overrides the normal register inferred from the profile.

It does not erase the underlying voice.

## Avoid Caricature

Do not mechanically insert recognizable mannerisms.

If the profile indicates that the user sometimes:

- uses sentence fragments
- swears
- makes jokes
- asks rhetorical questions
- uses parentheticals
- employs unusual punctuation
- uses analogies

that does not mean every piece should contain them.

A characteristic should appear at approximately the intensity justified by its weight, variability, context, and natural opportunity.

The goal is resemblance, not imitation through obvious verbal tics.

## Editing Existing Content

When rewriting existing content in the user's voice:

Preserve:

- intended meaning
- important factual claims
- necessary terminology
- constraints imposed by the destination

Change whatever stylistic characteristics are necessary to make the writing conform to `voice-profile.yaml`.

Do not unnecessarily rewrite passages that already conform strongly to the profile.

## Final Check

Before returning writing, ask:

> Would this plausibly belong in the same body of writing from which `voice-profile.yaml` was derived?

If not, identify the highest-impact deviations and correct them.

Then check the draft against `profile.author_rulings`. A rejected characteristic reappearing in the writing is a specific, known failure and is worth one deliberate look.

Do not mention the profile, feature weights, variability, or internal voice analysis in the finished artifact unless explicitly asked.