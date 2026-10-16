---
title: Drafts Index
type: index
status: current
updated: 2026-10-15
summary: >-
  Written, not yet submitted or shown. Expect these to change. Move a file to docs/external/ when
  it is sent.
---

# Drafts

| File | What it is | Status |
|---|---|---|
| `docs/drafts/2026-10-10-presentation-no-op-validity.pptx` | Draft slides for the project presentation, 34 slides with speaker notes, in three sections: motivation (general, then τ²-bench with two example traces), methodology (the read mandate and counterfactual twins, and how each gate is built), and results (per gate, qualitative then quantitative, then a summary for gpt-6-luna, claude-haiku-4.5, gpt-5.4-nano and llama-4-maverick, then one limitations slide and a questions slide). An appendix follows: attempted writes, removal causes, more limits, the no-op doctor, the qualitative scorecard, and the old discussion section slide. | draft |

**Notes on the presentation draft.**

- **By:** Vatsal + Claude.
- Each slide is one picture, so the text cannot be edited in PowerPoint. The editable source is
  the Claude slide deck the file was exported from. Change the deck there and export it again.
- Numbers come from `docs/research/findings-log.md` §1, §14 and §20. All twin scores use the
  lenient rule: a twin counts as passed if the agent made the right write, even if the episode
  failed for another reason. Slide titles name the topic, not the conclusion.
- The qualitative results slides (16, 18, 20) and slide 28 use the finished 3-trial review,
  the review-3-trials note (findings log §23) on the draft PR #8 branch. That review
  is not on main yet. The labels come from LLM reviewers, with no blind second labeller.
- Slide 28 shows a hand projection for a "no write attempted" check (M1.27). The scoreboard does
  not compute it yet. The nano value there is inferred.
- Slide 18 still has a placeholder for a transcript excerpt.
