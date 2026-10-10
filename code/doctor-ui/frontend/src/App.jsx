import React, { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { go, useLocal, useRoute } from "./util.js";
import AddBenchmark from "./AddBenchmark.jsx";
import Benchmark from "./Benchmark.jsx";

export const STATUS_LABEL = {
  ready: "ready",
  needs_setup: "needs setup",
  needs_adapter: "needs adapter",
};

export default function App() {
  const route = useRoute();
  const [benches, setBenches] = useState([]);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [reviewer, setReviewer] = useLocal("doctor-ui.reviewer", "");

  const refresh = useCallback(() => {
    api
      .benchmarks()
      .then((b) => {
        setBenches(b);
        setError("");
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(refresh, [refresh]);

  const current = benches.find((b) => b.id === route.bench);

  return (
    <div className="app">
      <header className="top">
        <a className="brand" href="#/">
          <span className="logo">⚕</span> No-op doctor <span className="muted">review</span>
        </a>
        <label className="reviewer">
          Reviewer
          <input
            value={reviewer}
            placeholder="your name"
            onChange={(e) => setReviewer(e.target.value)}
          />
        </label>
      </header>
      <div className="body">
        <nav className="side">
          <div className="side-head">
            <span>Benchmarks</span>
            <button className="small" onClick={() => setAdding(true)}>
              + Add
            </button>
          </div>
          {benches.map((b) => (
            <a
              key={b.id}
              className={"bench-link" + (b.id === route.bench ? " active" : "")}
              href={`#/b/${encodeURIComponent(b.id)}`}
            >
              <span className="bench-name">{b.label}</span>
              <span className="bench-meta">
                {b.status !== "ready" ? (
                  <span className={"pill " + b.status}>{STATUS_LABEL[b.status]}</span>
                ) : b.checkup ? (
                  <>
                    {b.checkup.null_passes}/{b.checkup.tasks} no-op
                    {b.counts.pending > 0 && <span className="dot" title="pending reviews" />}
                  </>
                ) : (
                  <span className="muted">no checkup yet</span>
                )}
              </span>
            </a>
          ))}
        </nav>
        <main className="main">
          {error && <div className="banner error">Backend: {error}</div>}
          {adding && (
            <AddBenchmark
              onClose={() => setAdding(false)}
              onAdded={(found) => {
                setAdding(false);
                refresh();
                if (found[0]) go("b", found[0].id);
              }}
            />
          )}
          {current ? (
            <Benchmark
              key={current.id}
              bench={current}
              route={route}
              reviewer={reviewer}
              onChanged={refresh}
            />
          ) : (
            <Welcome benches={benches} onAdd={() => setAdding(true)} />
          )}
        </main>
      </div>
    </div>
  );
}

function Welcome({ benches, onAdd }) {
  return (
    <div className="welcome">
      <h1>Review what the doctor proposes</h1>
      <p>
        A benchmark gives credit to an agent that does nothing when the correct outcome of a
        task is "no change". The doctor finds those tasks and proposes three treatments. You
        review each one here before it is used.
      </p>
      <div className="three">
        <div className="card">
          <h3>Read enforcements</h3>
          <p>The facts the agent must look up before a refusal counts. Drafted from the gold trajectory.</p>
        </div>
        <div className="card">
          <h3>DB twins</h3>
          <p>One field of the start state flips, so the action becomes correct. Checked with the benchmark's own grader.</p>
        </div>
        <div className="card">
          <h3>Policy flips</h3>
          <p>One policy sentence changes, so the action becomes allowed. The sentence must occur exactly once.</p>
        </div>
      </div>
      <p>
        Pick a benchmark on the left, or{" "}
        <button className="link" onClick={onAdd}>
          add one from a git URL
        </button>
        . {benches.length} benchmarks are available.
      </p>
    </div>
  );
}
