---
title: No-op Doctor Review UI
type: index
status: current
updated: 2026-10-10
summary: >-
  A web app around the no-op doctor. Plug in a benchmark (built in, git URL or local folder),
  run the checkup, and review the proposed read enforcements, DB twins and policy flips for
  each no-op task. Approved items export as the doctor's own spec files.
note: >-
  First version. Proposals come from gold trajectories and existing spec files; the doctor has
  no LLM proposer yet. A benchmark other than tau2 needs an adapter.
---

# No-op Doctor Review UI

The doctor (`code/doctor/`) proposes treatments for tasks that an agent passes by doing
nothing. A person must check each one before it is used. This app is where they do that.

The backend does all the work: it clones the benchmark, runs the doctor, validates every
proposal and every edit with the benchmark's own grader, and writes the spec files. The
frontend is only for review.

## Run it

Set up once (installs FastAPI and uvicorn into `code/doctor-ui/.venv`, and the React build
tools into `frontend/node_modules`):

```bash
cd code/doctor-ui
uv sync --extra dev
(cd frontend && npm install && npm run build)
```

The built-in tau2 benchmarks also need tau2's own environment:
`(cd ../tau2-bench && uv sync --extra dev)`.

Start it:

```bash
uv run uvicorn backend.app:app --port 8000
```

Open <http://localhost:8000>. Put your name in the Reviewer box: every review records who did it.

To work on the frontend, run `npm run dev` in `frontend/` as well and open
<http://localhost:5173>. Vite sends `/api` to the backend on port 8000.

Tests (mini_web only: no tau2, no API key, about 1 second):

```bash
uv run --extra dev pytest tests
```

## How to use it

1. **Pick or add a benchmark.** The sidebar lists this repository's tau2 domains and the
   mini_web toy. **+ Add** takes a git URL (cloned into the workspace) or a local folder.
2. **Run checkup.** The doctor scores the do-nothing trajectory on every task. Then the backend
   drafts proposals and validates them all. Airline takes about 4 minutes, most of it twin
   validation.
3. **Review each no-op task.** The task page shows what the user wants and the gold
   trajectory on the left. On the right:
   - **Read enforcement.** The reads drafted from the gold. Edit a tool or its `match`, drop a
     read, add one (gold reads are one click), or take the existing spec. A refusal counts as
     justified only if the agent made every read.
   - **Counterfactual twins.** The patch is shown as a before/after diff of the start state,
     with the write that is now correct. Six checks come from the benchmark's grader: doing
     nothing passes the original and fails the twin, doing the write fails the original and
     passes the twin, and the patch changes only the records it names. **Edit** re-validates
     on save. **+ Add a twin** writes a new one.
   - **Policy flips** used by those twins. All flips are also on the **Policy flips** tab, as
     a word diff inside the policy. The sentence must occur exactly once.
   Each item has **Approve**, **Reject**, a note, **Revert to proposal** and a history.
4. **Export.** The **Export** tab writes the approved items:

   | File | Content | Used by |
   |---|---|---|
   | `read-spec.json` | read enforcements | `doctor.py check-reads --spec`; tau2 `justification.json` |
   | `twins.yaml` | twin specs | `doctor.py twins build --spec` |
   | `twin-tasks.json` | built twin tasks (validated twins only) | the benchmark's task loader |
   | `flips.yaml`, `policy_flips/<id>.md` | flips and flipped policies | `doctor.py flips`; tau2 `policy_flips/` |
   | `review-log.json` | every item: status, note, history | the record of who approved what |

   The default folder is `workspace/exports/<benchmark>/<time>/`. The app never writes into the
   benchmark repository unless you name a folder there.

## What works automatically, and what does not

| Benchmark | Checkup | Read drafts | Twins | Flips |
|---|---|---|---|---|
| This repo's tau2 (`code/tau2-bench`) | yes | yes, from gold | reviews `tasks_twins.json` (airline); add others by hand | airline: `code/twins/policy_flips.yaml` |
| Another tau2-bench checkout (git URL) | after **Set up environment** (`uv sync` in the clone; it asks first) | yes | by hand, or from its `tasks_twins.json` | by hand |
| mini_web toy | yes | yes | yes (`examples/mini_web_twins.yaml`) | no policy |
| A repo with `noop-doctor.json` | yes, through its adapter | if the adapter gives gold calls | if the adapter patches state | if the adapter gives a policy |
| Any other repo | **no**: added as "needs adapter" | | | |

Plugging in an arbitrary repo needs an **adapter**: a class with the methods in
`code/doctor/noop_doctor/adapters/base.py` (`mini_web.py` is a worked example). Either add a
manifest to the repo:

```json
{
  "benchmarks": [
    {
      "id": "main",
      "label": "My benchmark",
      "adapter": "py:my_bench.doctor_adapter:MyAdapter:data/tasks.json",
      "setup": ["uv", "sync"],
      "sources": {"twin_yaml": ["doctor/twins.yaml"], "flips_yaml": ["doctor/flips.yaml"],
                  "skip_tools": ["lookup_user"]}
    }
  ]
}
```

or fill in the adapter and Python command on the benchmark's page. Writing the adapter is
still a person's job.

**Not built yet:**

- An **LLM proposer**. Read proposals come from gold trajectories. Twins and flips come from
  existing spec files or from the reviewer. When the doctor gets a proposer, it becomes
  another source in `backend/service.py` `refresh_proposals`.
- **Running agents** on approved twins. The app exports the specs; running them is the
  benchmark's job (for tau2, registry entries per domain; see `code/doctor/README.md`).
- **Several reviewers at once.** Reviews are one JSON file per benchmark on the machine that
  runs the backend. Two people on one backend work; two backends do not share state.

## Files

| File | What it does |
|---|---|
| `backend/app.py` | The HTTP API (FastAPI). Also serves `frontend/dist/`. |
| `backend/benchmarks.py` | Benchmark configs: presets, git clone, detection (manifest, tau2, unknown). |
| `backend/worker.py` | Runs inside the benchmark's own Python. Loads the adapter and answers JSON requests on stdin/stdout. Imports only the standard library and the doctor. |
| `backend/workers.py` | Starts a worker per benchmark and talks to it. |
| `backend/service.py` | Per benchmark: checkup job, proposals, validation of edits, export. |
| `backend/store.py` | Review state: proposal, current version, status, note, history. |
| `frontend/src/` | React app: `Benchmark.jsx` (summary, task list, flips, export), `TaskReview.jsx` (one task), `Items.jsx` (the review cards), `AddBenchmark.jsx`. |
| `tests/test_backend.py` | Checkup, edits, a refresh that keeps reviews, export round trip through `doctor.py`, detection, git clone. |
| `workspace/` | Clones, reviews and exports. Git-ignored. Set `DOCTOR_UI_HOME` to move it. |

**Why a worker process.** The doctor's adapters import the benchmark (tau2 and its
dependencies). The backend never imports a benchmark. It runs `worker.py` with the benchmark's
own Python (`uv run --project <checkout> python`), so two benchmarks with different
dependencies can be open at once. The doctor's core has no benchmark imports, so the backend
uses it directly for read specs and flips.

**The app does not change `code/doctor/`.** It calls the doctor as a library.
