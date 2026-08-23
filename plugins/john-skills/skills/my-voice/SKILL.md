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

## Voice Model

Each feature in the profile contains:

- `weight` — how important the feature is to the user's recognizable voice
- `variability` — how much the feature naturally changes between writing contexts

Treat these as tendencies, not binary rules.

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

The purpose of variation is to avoid making the user's voice feel formulaic.

## Writing Procedure

1. Understand the requested artifact.
2. Determine its appropriate register.
3. Load the complete voice profile.
4. Identify the highest-weight stable characteristics.
5. Determine which variable characteristics fit this context.
6. Apply modest variation to those characteristics.
7. Write the content.
8. Review the draft against the voice profile.
9. Correct conspicuous deviations.
10. Return the finished content.

Do not expose this process unless requested.

## Priority

When stylistic characteristics compete, prioritize:

1. explicit instructions in the current request
2. semantic accuracy
3. high-weight, low-variability voice features
4. contextual appropriateness
5. high-weight, high-variability features
6. lower-weight features
7. stochastic variation

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

Do not mention the profile, feature weights, variability, or internal voice analysis in the finished artifact unless explicitly asked.