---
title: WebArena-Verified Already Uses a Read Gate
type: research
status: current
updated: 2026-10-26
review_by: 2026-12-01
summary: >-
  WebArena-Verified (ServiceNow), the audited release of WebArena, addresses the same problem we
  address in tau2: unachievable tasks that gave credit for a bare "N/A". On 8 of its 40
  failure-status tasks it uses the same idea as our read gate, a required visit to the page that
  holds the deciding data. The other 32 check the status only.
---

# WebArena-Verified Already Uses a Read Gate

**Last updated:** 2026-10-26 · **By:** Hammad + Claude

## 1. Summary

- **The same problem.** In the original WebArena, an unachievable task passed when the agent
  answered "N/A". So an agent got credit for giving up, the same hole as a no-action pass in
  τ²-bench. The WebArena-Verified maintainers name this problem: "premature 'N/A' answers are no
  longer auto-credited", and "the protocol favors agents that explore sufficiently before
  concluding failure".
- **The same idea, on 8 of its 40 unachievable tasks.** These 8 also require a network event
  that shows the agent opened the page with the deciding data. For example, tasks 794–798
  ("Change the delivery address for my most recent non canceled order …") expect
  `ACTION_NOT_ALLOWED_ERROR` **and** a visit to the order history page. As in our read gate, a
  "cannot do it" verdict counts only if the agent looked where the deciding facts are. It checks
  a page visit, not that the agent read the deciding fact on that page.
- **It was added in Verified.** In the original WebArena, all 8 tasks were graded by an
  `N/A` string match only.
- **It is partial.** The other 32 failure-status tasks check the status code only. Our read gate
  would apply to them too.

The maintainers built this check independently of us. We take it as outside support for the
read gate.

## 2. Evidence

`code/webarena-verified/failure_task_checks.py` reads the two datasets that ship in the
`webarena-verified` package (version 1.2.3): `webarena-verified.json` and the original
`test.raw.json`. It needs no sites, no model calls and no key.

```bash
uvx --python 3.12 --with webarena-verified==1.2.3 python code/webarena-verified/failure_task_checks.py
```

Output, 2026-10-26:

- 812 tasks. 40 expect a failure status: 28 `NOT_FOUND_ERROR`, 11 `ACTION_NOT_ALLOWED_ERROR`,
  1 `PERMISSION_DENIED_ERROR`.
- 8 of the 40 also have a `NetworkEventEvaluator`:

  | Tasks | Expected status | Required page visit | Start page |
  |---|---|---|---|
  | 301, 302 ("open the order details page for the most recent processing order", …) | `NOT_FOUND_ERROR` | `/sales/order/history/` | shop home |
  | 794–798 ("change the delivery address for my … order") | `ACTION_NOT_ALLOWED_ERROR` | `/sales/order/history/` | shop home |
  | 791 (commit the 5 most recent posts of the cars forum to a repository) | `NOT_FOUND_ERROR` | `/forums` | GitLab and Reddit home |

- In every case the required page is not the start page, so an agent that only loads the start
  page fails the check.
- In the original `test.raw.json`, all 8 tasks have `eval_types: ["string_match"]` with
  `fuzzy_match: "N/A"`, and no page check.
- The other 32 failure-status tasks need the status only: 8, 22, 24, 101, 115, 166, 168, 183,
  191, 201, 218, 219, 225, 234, 235, 247, 253, 313, 319, 368, 376, 382, 491, 723, 726, 783,
  789, 790, 792, 793, 805, 807.

## 3. What this does and does not show

- **It shows** that the maintainers of a widely used benchmark saw the "credit for giving up"
  problem, and that on some tasks they fixed it the way we do: with a required read.
- **It does not show** why they chose these 8 tasks. Their documentation explains the typed
  status codes, but not the choice of tasks for the page check.
- **Task 791 is a weak case.** The required page is the forum list, not the cars forum itself.
- **Our earlier count was wrong.** A first check on 2026-10-20 counted 9 gated tasks. The
  dataset has 8. This note uses 8.
- **A do-nothing check (2026-10-20, a spike whose script we did not keep).** An agent that only
  loads the start page and always answers `NOT_FOUND_ERROR` passed 24 of 812 tasks. The empty
  answer passed 0. We did not repeat this measurement for this note.

## Sources (accessed 2026-10-26)

- WebArena-Verified repository: https://github.com/ServiceNow/webarena-verified
- Package: `webarena-verified==1.2.3` on PyPI, files `webarena_verified/assets/dataset/webarena-verified.json`
  and `webarena_verified/assets/dataset/test.raw.json`.
- "Handling of Unachievable Tasks", WebArena-Verified documentation (source of both quotes):
  https://servicenow.github.io/webarena-verified/latest/evaluation/handling_of_unachievable_tasks/
- WebArena-Verified paper, "WebArena Verified: Reliable Evaluation for Web Agents":
  https://openreview.net/forum?id=94tlGxmqkN (not read: the page needs a browser check).
- WebArena (Zhou et al., ICLR 2024): https://arxiv.org/abs/2307.13854
