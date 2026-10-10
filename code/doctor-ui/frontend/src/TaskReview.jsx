import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { callText, go, natural } from "./util.js";
import { FlipCard, NewReads, NewTwin, ReadsCard, TwinCard } from "./Items.jsx";

export default function TaskReview({ taskId, review, ...ctx }) {
  const { bench, items } = ctx;
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.task(bench.id, taskId).then(setInfo).catch((e) => setError(e.message));
  }, [bench.id, taskId]);

  const row = review.checkup.tasks.find((t) => t.task_id === taskId);
  const reads = items.find((i) => i.kind === "reads" && i.task_id === taskId);
  const twins = items.filter((i) => i.kind === "twin" && i.task_id === taskId);
  const flipIds = new Set(twins.map((t) => t.current.policy_flip).filter(Boolean));
  const flips = items.filter((i) => i.kind === "flip" && flipIds.has(i.id.slice(5)));

  // Previous / next task with something to review.
  const ids = [
    ...new Set(items.filter((i) => i.task_id).map((i) => i.task_id).concat(review.checkup.summary.passed)),
  ].sort(natural);
  const at = ids.indexOf(taskId);

  return (
    <div className="task-review">
      <div className="task-nav">
        <button className="link" onClick={() => go("b", bench.id, "tasks")}>
          ← All tasks
        </button>
        <span className="muted">
          Task {at + 1} of {ids.length}
        </span>
        <span>
          <button className="small" disabled={at <= 0} onClick={() => go("b", bench.id, "task", ids[at - 1])}>
            ‹ Prev
          </button>{" "}
          <button
            className="small"
            disabled={at < 0 || at >= ids.length - 1}
            onClick={() => go("b", bench.id, "task", ids[at + 1])}
          >
            Next ›
          </button>
        </span>
      </div>
      <div className="split">
        <aside className="context">
          <h2>Task {taskId}</h2>
          {row && (
            <div className="facts">
              <span>
                Do-nothing reward <strong>{row.null_reward ?? "?"}</strong>
              </span>
              <span>
                Gold: {row.gold_reads} reads, {row.gold_writes} writes
              </span>
            </div>
          )}
          {error && <div className="banner error">{error}</div>}
          {!info && !error && <div className="muted">Loading the task…</div>}
          {info && (
            <>
              {info.summary && (
                <div className="scenario">
                  <h4>What the user wants</h4>
                  <div className="pre-wrap">{info.summary}</div>
                </div>
              )}
              <h4>Gold trajectory (agent calls)</h4>
              {info.gold.length ? (
                <ol className="gold">
                  {info.gold.map((c, i) => (
                    <li key={i}>
                      <span className={"kind " + c.kind}>{c.kind}</span>
                      <code>{callText(c)}</code>
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="muted">The benchmark has no gold calls for this task.</div>
              )}
              <details>
                <summary>Raw task</summary>
                <pre>{JSON.stringify(info.raw, null, 2)}</pre>
              </details>
            </>
          )}
        </aside>
        <div className="panels">
          <section className="panel">
            <h2>
              Read enforcement <span className="hint">Did the agent look before it refused?</span>
            </h2>
            {reads ? <ReadsCard item={reads} gold={info?.gold} {...ctx} /> : <NewReads taskId={taskId} gold={info?.gold} {...ctx} />}
          </section>
          <section className="panel">
            <h2>
              Counterfactual twins <span className="hint">Does the agent act when the action becomes correct?</span>
            </h2>
            {twins.map((t) => (
              <TwinCard key={t.id} item={t} {...ctx} />
            ))}
            {!twins.length && <div className="empty">No twin proposed for this task yet.</div>}
            <NewTwin taskId={taskId} gold={info?.gold} {...ctx} />
          </section>
          {flips.length > 0 && (
            <section className="panel">
              <h2>
                Policy flips used by these twins{" "}
                <span className="hint">Shared across tasks; also on the Policy flips tab.</span>
              </h2>
              {flips.map((f) => (
                <FlipCard key={f.id} item={f} {...ctx} />
              ))}
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
