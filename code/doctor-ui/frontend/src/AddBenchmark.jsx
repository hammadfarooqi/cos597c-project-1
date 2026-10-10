import React, { useState } from "react";
import { api } from "./api.js";

export default function AddBenchmark({ onClose, onAdded }) {
  const [mode, setMode] = useState("git");
  const [url, setUrl] = useState("");
  const [ref, setRef] = useState("");
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [found, setFound] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = mode === "git" ? { git_url: url.trim(), ref: ref.trim() || null } : { path: path.trim() };
      setFound(await api.addBenchmark(body));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Add a benchmark</h2>
        {!found ? (
          <form onSubmit={submit}>
            <div className="seg">
              <button type="button" className={mode === "git" ? "on" : ""} onClick={() => setMode("git")}>
                Git URL
              </button>
              <button type="button" className={mode === "path" ? "on" : ""} onClick={() => setMode("path")}>
                Local folder
              </button>
            </div>
            {mode === "git" ? (
              <>
                <label className="field">
                  Repository URL
                  <input autoFocus value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://github.com/sierra-research/tau2-bench" />
                </label>
                <label className="field">
                  Branch or tag (optional)
                  <input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="main" />
                </label>
              </>
            ) : (
              <label className="field">
                Folder on the machine that runs the backend
                <input autoFocus value={path} onChange={(e) => setPath(e.target.value)} placeholder="/home/me/my-benchmark" />
              </label>
            )}
            <div className="explain">
              <strong>What works automatically:</strong> a tau2-bench checkout (one benchmark per
              domain), or any repo with a <code>noop-doctor.json</code> that names its adapter.
              Anything else is added as "needs adapter". The doctor runs the benchmark's own
              code on this machine, so only add repos you trust.
            </div>
            {error && <div className="banner error">{error}</div>}
            <div className="dirty">
              <button type="button" onClick={onClose}>
                Cancel
              </button>
              <button className="primary" disabled={busy || (mode === "git" ? !url : !path)}>
                {busy ? (mode === "git" ? "Cloning…" : "Reading…") : "Add"}
              </button>
            </div>
          </form>
        ) : (
          <div>
            <p>Found {found.length} benchmark(s):</p>
            <ul className="found">
              {found.map((b) => (
                <li key={b.id}>
                  <strong>{b.label}</strong> <span className={"pill " + b.status}>{b.status.replace("_", " ")}</span>
                  <div className="muted small">{b.detected}</div>
                  {b.status === "needs_setup" && (
                    <div className="muted small">
                      Its Python environment is not installed yet. Open it and press "Set up environment".
                    </div>
                  )}
                </li>
              ))}
            </ul>
            <div className="dirty">
              <button className="primary" onClick={() => onAdded(found)}>
                Open
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
