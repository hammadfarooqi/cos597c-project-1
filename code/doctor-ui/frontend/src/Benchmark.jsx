import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";
import { STATUS_LABEL } from "./App.jsx";
import { go, natural } from "./util.js";
import TaskReview from "./TaskReview.jsx";
import { FlipCard, NewFlip, StatusPill } from "./Items.jsx";

const STEPS = [
  ["checkup", "Checkup"],
  ["draft-reads", "Read drafts"],
  ["twins", "DB twins"],
  ["flips", "Policy flips"],
];

export default function Benchmark({ bench, route, reviewer, onChanged }) {
  const [review, setReview] = useState(null);
  const [job, setJob] = useState(bench.job);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.review(bench.id).then(setReview).catch((e) => setError(e.message));
  }, [bench.id]);
  useEffect(load, [load]);

  // Poll the running job; reload the review when it ends.
  useEffect(() => {
    if (!job || job.state !== "running") return;
    const t = setInterval(async () => {
      const j = await api.job(bench.id).catch(() => null);
      if (!j) return;
      setJob(j);
      if (j.state !== "running") {
        load();
        onChanged();
      }
    }, 800);
    return () => clearInterval(t);
  }, [job, bench.id, load, onChanged]);

  const start = async (fn, confirmText) => {
    if (confirmText && !window.confirm(confirmText)) return;
    setError("");
    try {
      setJob(await fn(bench.id));
    } catch (e) {
      setError(e.message);
    }
  };

  const items = review?.items || [];
  // Keep the item list here and the counts in the header and sidebar up to date.
  const setItem = (it) => {
    setReview((r) => ({ ...r, items: r.items.map((x) => (x.id === it.id ? it : x)) }));
    onChanged();
  };
  const addLocal = (it) => {
    setReview((r) => ({ ...r, items: [...r.items, it] }));
    onChanged();
  };
  const removeLocal = (id) => {
    setReview((r) => ({ ...r, items: r.items.filter((x) => x.id !== id) }));
    onChanged();
  };
  const ctx = { bench, reviewer, items, setItem, addLocal, removeLocal, tools: review?.tools || [] };
  const running = job && job.state === "running";
  const missing = bench.adapter_info?.missing || {};
  const view = route.view;

  return (
    <div className="bench">
      <section className="bench-head">
        <div>
          <h1>{bench.label}</h1>
          <div className="meta">
            <span className={"pill " + bench.status}>{STATUS_LABEL[bench.status]}</span>
            <code>{bench.adapter || "no adapter"}</code>
            <span className="muted">{sourceText(bench.source)}</span>
          </div>
          <div className="muted small">{bench.detected}</div>
          {bench.adapter_info && (
            <div className="steps">
              {STEPS.map(([k, label]) => (
                <span
                  key={k}
                  className={"step " + ((missing[k] || []).length ? "off" : "on")}
                  title={(missing[k] || []).length ? `adapter has no ${missing[k].join(", ")}` : "available"}
                >
                  {(missing[k] || []).length ? "✕" : "✓"} {label}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="actions">
          {bench.status === "needs_setup" && (
            <button
              disabled={running}
              onClick={() =>
                start(
                  api.setup,
                  `This runs "${(bench.setup || []).join(" ")}" in ${bench.cwd}. It installs the benchmark's Python packages into its own environment. Continue?`
                )
              }
            >
              Set up environment
            </button>
          )}
          {bench.source?.kind !== "preset" && (
            <button
              className="danger-text"
              disabled={running}
              onClick={async () => {
                if (!window.confirm(`Remove ${bench.label}? Its reviews stay in the workspace.`)) return;
                await api.deleteBenchmark(bench.id).catch((e) => setError(e.message));
                window.location.hash = "/";
                onChanged();
              }}
            >
              Remove
            </button>
          )}
          {bench.status === "ready" && (
            <>
              <button className="primary" disabled={running} onClick={() => start(api.checkup)}>
                {bench.checkup ? "Re-run checkup" : "Run checkup"}
              </button>
              <button disabled={running || !items.length} onClick={() => start(api.validateAll)}>
                Validate all
              </button>
            </>
          )}
        </div>
      </section>

      {job && (job.state !== "done" || job.kind !== "checkup" || !bench.checkup) && (
        <JobBar job={job} />
      )}
      {error && <div className="banner error">{error}</div>}

      {bench.status === "needs_adapter" && <NeedsAdapter bench={bench} onChanged={onChanged} />}

      {bench.checkup && view !== "task" && <Summary s={bench.checkup} counts={bench.counts} />}

      {review && bench.checkup && (
        <>
          <div className="tabs">
            {[
              ["tasks", "No-op tasks"],
              ["flips", "Policy flips"],
              ["export", "Export"],
            ].map(([k, label]) => (
              <a
                key={k}
                className={view === k || (k === "tasks" && view === "task") ? "active" : ""}
                href={`#/b/${encodeURIComponent(bench.id)}/${k}`}
              >
                {label}
                {k === "flips" && ` (${items.filter((i) => i.kind === "flip").length})`}
              </a>
            ))}
          </div>
          {view === "task" && route.arg ? (
            <TaskReview key={route.arg} taskId={route.arg} review={review} {...ctx} />
          ) : view === "flips" ? (
            <FlipsView {...ctx} />
          ) : view === "export" ? (
            <ExportView bench={bench} items={items} />
          ) : (
            <TaskList bench={bench} review={review} />
          )}
        </>
      )}
    </div>
  );
}

function sourceText(s) {
  if (!s) return "";
  if (s.kind === "git") return `git ${s.url}${s.ref ? "@" + s.ref : ""}`;
  if (s.kind === "local") return `local ${s.path}`;
  return "built in";
}

function JobBar({ job }) {
  const [done, total] = job.progress || [0, 0];
  const pct = total ? Math.round((100 * done) / total) : job.state === "running" ? 5 : 100;
  return (
    <div className={"job " + job.state}>
      <div className="job-line">
        <strong>{job.kind}</strong>
        <span>{job.state === "error" ? job.error : job.message || job.state}</span>
      </div>
      {job.state === "running" && (
        <div className="bar">
          <div style={{ width: pct + "%" }} />
        </div>
      )}
      {job.state === "error" && job.log?.length > 0 && (
        <details>
          <summary>Details</summary>
          <pre>{job.log.join("\n")}</pre>
        </details>
      )}
    </div>
  );
}

function Summary({ s, counts }) {
  const errors = Object.keys(s.errors || {}).length;
  return (
    <section className="summary">
      <Stat big={`${s.null_passes}/${s.tasks}`} label="tasks pass with a do-nothing agent" />
      {errors ? (
        <Stat big={`${errors}/${s.tasks}`} label="tasks could not be scored: the result is incomplete" bad />
      ) : (
        <Stat big={`${(100 * s.pass_rate).toFixed(1)}%`} label={s.verdict} />
      )}
      <Stat big={s.passed_without_gold_reads.length} label="no-op tasks with no gold reads (need a person)" />
      <Stat big={`${counts.approved}/${counts.approved + counts.pending + counts.rejected}`} label="proposals approved" />
      {s.passed_but_gold_writes.length > 0 && (
        <div className="banner warn">
          These tasks pass with no action although their gold has a write (a grader bug, or a
          write that changes nothing, such as answering "N/A"):{" "}
          {s.passed_but_gold_writes.join(", ")}
        </div>
      )}
      {errors > 0 && (
        <div className="banner warn">
          {errors} tasks could not be scored, for example task {Object.keys(s.errors)[0]}:{" "}
          {Object.values(s.errors)[0]}
        </div>
      )}
    </section>
  );
}

function Stat({ big, label, bad }) {
  return (
    <div className={"stat" + (bad ? " bad" : "")}>
      <div className="big">{big}</div>
      <div className="label">{label}</div>
    </div>
  );
}

function TaskList({ bench, review }) {
  const [filter, setFilter] = useState("all");
  const rows = useMemo(() => {
    const byTask = {};
    const passed = new Set(review.checkup.summary.passed);
    for (const t of review.checkup.tasks) if (t.passed) byTask[t.task_id] = { ...t, items: [] };
    for (const it of review.items) {
      if (!it.task_id) continue;
      if (!byTask[it.task_id]) {
        const t = review.checkup.tasks.find((x) => x.task_id === it.task_id) || { task_id: it.task_id };
        byTask[it.task_id] = { ...t, items: [] };
      }
      byTask[it.task_id].items.push(it);
    }
    return Object.values(byTask)
      .map((r) => ({ ...r, noop: passed.has(r.task_id) }))
      .sort((a, b) => natural(a.task_id, b.task_id));
  }, [review]);

  const shown = rows.filter((r) =>
    filter === "pending" ? r.items.some((i) => i.status === "pending") : true
  );
  if (!rows.length)
    return Object.keys(review.checkup.summary.errors || {}).length ? (
      <div className="empty">No task passed, but some tasks could not be scored (see above). Fix that and re-run the checkup.</div>
    ) : (
      <div className="empty">No task passes with a do-nothing agent. No treatment needed.</div>
    );

  return (
    <section>
      <div className="filters">
        <label>
          <input type="radio" checked={filter === "all"} onChange={() => setFilter("all")} /> All
          ({rows.length})
        </label>
        <label>
          <input type="radio" checked={filter === "pending"} onChange={() => setFilter("pending")} />{" "}
          Needs review ({rows.filter((r) => r.items.some((i) => i.status === "pending")).length})
        </label>
      </div>
      <table className="tasks">
        <thead>
          <tr>
            <th>Task</th>
            <th>Do-nothing reward</th>
            <th>Gold reads / writes</th>
            <th>Read enforcement</th>
            <th>Twins</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {shown.map((r) => {
            const reads = r.items.find((i) => i.kind === "reads");
            const twins = r.items.filter((i) => i.kind === "twin");
            return (
              <tr key={r.task_id} onClick={() => go("b", bench.id, "task", r.task_id)}>
                <td>
                  <strong>{r.task_id}</strong>
                  {!r.noop && <span className="pill muted-pill">not a no-op pass</span>}
                </td>
                <td>{r.null_reward ?? "?"}</td>
                <td>
                  {r.gold_reads ?? "?"} / {r.gold_writes ?? "?"}
                </td>
                <td>
                  {reads ? (
                    <>
                      <StatusPill item={reads} /> {reads.current.required_reads.length} reads
                    </>
                  ) : (
                    <span className="muted">none</span>
                  )}
                </td>
                <td>
                  {twins.length ? (
                    <span className="twin-pills">
                      {twins.map((t) => (
                        <StatusPill key={t.id} item={t} short />
                      ))}
                    </span>
                  ) : (
                    <span className="muted">none yet</span>
                  )}
                </td>
                <td className="go">Review →</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function FlipsView(ctx) {
  const flips = ctx.items.filter((i) => i.kind === "flip");
  return (
    <section className="stack">
      <p className="muted">
        A policy flip changes one sentence of the policy so that the action the user asks for
        becomes allowed. Twins that use a flip name it in their <code>policy_flip</code> field.
      </p>
      {flips.map((it) => (
        <FlipCard key={it.id} item={it} {...ctx} />
      ))}
      {!flips.length && <div className="empty">No policy flips proposed for this benchmark.</div>}
      <NewFlip {...ctx} />
    </section>
  );
}

function ExportView({ bench, items }) {
  const [dest, setDest] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const approved = items.filter((i) => i.status === "approved");
  const by = (k) => approved.filter((i) => i.kind === k).length;
  const notOk = approved.filter((i) => i.kind === "twin" && !i.validation?.ok);
  const pending = items.filter((i) => i.status === "pending").length;
  return (
    <section className="stack">
      <div className="card">
        <h3>Export approved items as doctor spec files</h3>
        <ul>
          <li>
            <code>read-spec.json</code>: {by("reads")} read enforcements (the format of{" "}
            <code>justification.json</code>)
          </li>
          <li>
            <code>twins.yaml</code> and <code>twin-tasks.json</code>: {by("twin")} twins
            {notOk.length > 0 && ` (${notOk.length} not validated OK: left out of twin-tasks.json)`}
          </li>
          <li>
            <code>flips.yaml</code> and <code>policy_flips/*.md</code>: {by("flip")} policy flips
          </li>
          <li>
            <code>review-log.json</code>: every item with its status, notes and history
          </li>
        </ul>
        {pending > 0 && <div className="banner warn">{pending} items are still pending and are not exported.</div>}
        <label className="field">
          Folder (empty: the workspace export folder)
          <input value={dest} onChange={(e) => setDest(e.target.value)} placeholder="/path/to/folder" />
        </label>
        <button
          className="primary"
          onClick={() =>
            api
              .exportSpecs(bench.id, dest)
              .then((r) => {
                setResult(r);
                setError("");
              })
              .catch((e) => setError(e.message))
          }
        >
          Export
        </button>
        {error && <div className="banner error">{error}</div>}
        {result && (
          <div className="result">
            <div>
              Wrote to <code>{result.folder}</code>:
            </div>
            <ul>
              {result.files.map((f) => (
                <li key={f}>
                  <code>{f.replace(result.folder + "/", "")}</code>
                </li>
              ))}
            </ul>
            {result.skipped.length > 0 && (
              <div className="banner warn">
                Left out:
                <ul>
                  {result.skipped.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

function NeedsAdapter({ bench, onChanged }) {
  const [adapter, setAdapter] = useState("py:");
  const [python, setPython] = useState((bench.python || []).join(" "));
  const [error, setError] = useState("");
  return (
    <section className="card needs">
      <h3>This repo needs an adapter</h3>
      <p>
        The doctor only knows a benchmark through an adapter: a small class that lists the tasks,
        labels tools as READ or WRITE, scores a do-nothing run, and (for twins) patches the start
        state. The doctor ships adapters for tau2-bench and the mini_web example. For any other
        benchmark, write one (see <code>code/doctor/noop_doctor/adapters/mini_web.py</code>) and
        either add a <code>noop-doctor.json</code> to the repo or fill in the form.
      </p>
      <label className="field">
        <span>
          Adapter (<code>py:&lt;module&gt;:&lt;Class&gt;:&lt;argument&gt;</code>, importable from the repo root)
        </span>
        <input value={adapter} onChange={(e) => setAdapter(e.target.value)} />
      </label>
      <label className="field">
        Python command (runs the worker in the benchmark's environment)
        <input value={python} onChange={(e) => setPython(e.target.value)} />
      </label>
      <button
        className="primary"
        onClick={() =>
          api
            .updateBenchmark(bench.id, { adapter, python: python.split(/\s+/).filter(Boolean) })
            .then(onChanged)
            .catch((e) => setError(e.message))
        }
      >
        Save adapter
      </button>
      {error && <div className="banner error">{error}</div>}
      <details>
        <summary>
          <code>noop-doctor.json</code> example
        </summary>
        <pre>{`{
  "benchmarks": [
    {
      "id": "main",
      "label": "My benchmark",
      "adapter": "py:my_bench.doctor_adapter:MyAdapter:data/tasks.json",
      "setup": ["uv", "sync"],
      "sources": {
        "twin_yaml": ["doctor/twins.yaml"],
        "flips_yaml": ["doctor/flips.yaml"],
        "skip_tools": ["lookup_user"]
      }
    }
  ]
}`}</pre>
      </details>
    </section>
  );
}
