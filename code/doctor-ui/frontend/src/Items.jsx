// Review cards: read enforcements, twins, policy flips, and the shared review footer.

import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { callText, compact, pretty, wordDiff } from "./util.js";

// --- shared ------------------------------------------------------------------------------

export function StatusPill({ item, short }) {
  const v = item.validation;
  const bad = v && !v.ok;
  return (
    <span
      className={"pill status-" + item.status + (bad ? " invalid" : "")}
      title={`${item.id}: ${item.status}${bad ? ", fails validation" : ""}`}
    >
      {short ? item.id.split("_twin_").pop() : item.status}
      {bad && " ⚠"}
    </span>
  );
}

function needName(reviewer) {
  if (reviewer.trim()) return false;
  window.alert("Enter your name in the Reviewer box (top right) first.");
  return true;
}

function useSave(ctx, item) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const save = async (body) => {
    if (needName(ctx.reviewer)) return null;
    setBusy(true);
    setError("");
    try {
      const it = await api.updateItem(ctx.bench.id, item.id, { reviewer: ctx.reviewer, ...body });
      ctx.setItem(it);
      return it;
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setBusy(false);
    }
  };
  return { save, busy, error };
}

function ReviewFooter({ item, ctx, dirty }) {
  const { save, busy, error } = useSave(ctx, item);
  const [note, setNote] = useState(item.note || "");
  useEffect(() => setNote(item.note || ""), [item.note]);
  const del = async () => {
    if (!window.confirm(`Delete ${item.id}?`)) return;
    await api.deleteItem(ctx.bench.id, item.id);
    ctx.removeLocal(item.id);
  };
  return (
    <div className="footer">
      <div className="footer-row">
        <StatusPill item={item} />
        <span className="muted small">
          {item.source}
          {item.edited && item.proposal && " · edited"}
        </span>
        <span className="grow" />
        {item.edited && item.proposal && (
          <button className="small" disabled={busy} onClick={() => save({ revert: true })}>
            Revert to proposal
          </button>
        )}
        {!item.proposal && (
          <button className="small danger-text" onClick={del}>
            Delete
          </button>
        )}
        <button
          className="small"
          disabled={busy}
          onClick={() => save({ status: "pending", note })}
          hidden={item.status === "pending"}
        >
          Reset
        </button>
        <button
          className="reject"
          disabled={busy || item.status === "rejected"}
          onClick={() => save({ status: "rejected", note })}
        >
          Reject
        </button>
        <button
          className="approve"
          disabled={busy || dirty || item.status === "approved"}
          title={dirty ? "Save your edits first" : ""}
          onClick={() => {
            if (item.validation && !item.validation.ok &&
                !window.confirm("This item fails validation. Approve it anyway?")) return;
            save({ status: "approved", note });
          }}
        >
          Approve
        </button>
      </div>
      <div className="note-row">
        <input
          className="note"
          placeholder="Note (why you approve, reject or changed it). Saved with Approve or Reject."
          value={note}
          onChange={(e) => setNote(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && save({ note })}
        />
        {note !== (item.note || "") && (
          <button className="small" disabled={busy} onClick={() => save({ note })}>
            Save note
          </button>
        )}
      </div>
      {error && <div className="banner error">{error}</div>}
      <details className="history">
        <summary>History ({item.history.length})</summary>
        <ul>
          {item.history.map((h, i) => (
            <li key={i}>
              <span className="muted">{h.at.replace("T", " ").slice(0, 16)}</span> {h.who || "?"}{" "}
              <strong>{h.action}</strong> {h.note && `— ${h.note}`}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}

function Checks({ v, rows }) {
  if (!v) return <div className="muted small">Not validated yet.</div>;
  return (
    <div className="checks">
      {rows && v.null_orig !== undefined && (
        <div className="check-grid">
          {rows.map(([label, got, want, explain]) => (
            <div key={label} className={"check " + (got === want ? "pass" : "fail")} title={explain}>
              <span className="check-label">{label}</span>
              <span className="check-val">
                {String(got ?? "?")}
                <span className="muted"> / want {String(want)}</span>
              </span>
            </div>
          ))}
        </div>
      )}
      {v.failures?.map((f) => (
        <div key={f} className="banner error small">
          {f.length > 240 ? (
            <details>
              <summary>{f.slice(0, 240)}…</summary>
              <pre>{f}</pre>
            </details>
          ) : (
            f
          )}
        </div>
      ))}
      {v.warnings?.map((f) => (
        <div key={f} className="banner warn small">
          {f}
        </div>
      ))}
      {v.ok && !v.failures?.length && <div className="ok small">✓ Validation passed</div>}
    </div>
  );
}

function JsonInput({ value, onChange, rows = 1, placeholder }) {
  const [text, setText] = useState(() => (rows > 1 ? pretty(value) : JSON.stringify(value)));
  const [bad, setBad] = useState(false);
  return (
    <textarea
      className={"json" + (bad ? " bad" : "")}
      rows={rows}
      value={text}
      placeholder={placeholder}
      spellCheck={false}
      onChange={(e) => {
        setText(e.target.value);
        try {
          onChange(JSON.parse(e.target.value || "{}"));
          setBad(false);
        } catch {
          setBad(true);
          onChange(undefined);
        }
      }}
    />
  );
}

// --- read enforcement --------------------------------------------------------------------

function readKey(r) {
  return JSON.stringify([r.tool, r.match]);
}

export function ReadsCard({ item, gold, ...ctx }) {
  const [draft, setDraft] = useState(item.current);
  const [ver, setVer] = useState(0); // remount inputs after a revert or a save
  useEffect(() => {
    setDraft(item.current);
    setVer((v) => v + 1);
  }, [item.current]);
  const { save, busy, error } = useSave(ctx, item);
  const reads = draft.required_reads || [];
  const dirty = JSON.stringify(draft) !== JSON.stringify(item.current);
  const invalid = reads.some((r) => r.match === undefined);
  const readTools = ctx.tools.filter((t) => t.kind === "read").map((t) => t.name);
  const setReads = (rs) => setDraft({ ...draft, required_reads: rs });
  const have = new Set(reads.map(readKey));
  const goldReads = (gold || []).filter(
    (c) => c.kind === "read" && Object.keys(c.arguments || {}).length
  );
  const ref = item.reference?.required_reads;

  return (
    <div className={"item reads status-" + item.status}>
      <p className="explain">
        The do-nothing (or refusing) pass counts only if the agent made <strong>every</strong> read
        below. A read matches any successful call with one of the tool names whose arguments
        include the <code>match</code> values.
      </p>
      <table className="reads-table" key={ver}>
        <thead>
          <tr>
            <th>Tool</th>
            <th>Match (JSON)</th>
            <th>Why</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {reads.map((r, i) => (
            <tr key={i}>
              <td>
                <input
                  list="read-tools"
                  value={Array.isArray(r.tool) ? r.tool.join(" | ") : r.tool}
                  onChange={(e) => {
                    const parts = e.target.value.split("|").map((s) => s.trim()).filter(Boolean);
                    const rs = [...reads];
                    rs[i] = { ...r, tool: parts.length > 1 ? parts : e.target.value };
                    setReads(rs);
                  }}
                />
              </td>
              <td>
                <JsonInput
                  value={r.match}
                  onChange={(m) => {
                    const rs = [...reads];
                    rs[i] = { ...r, match: m };
                    setReads(rs);
                  }}
                />
              </td>
              <td>
                <input
                  value={r.why || ""}
                  onChange={(e) => {
                    const rs = [...reads];
                    rs[i] = { ...r, why: e.target.value };
                    setReads(rs);
                  }}
                />
              </td>
              <td>
                <button className="small danger-text" title="Drop this read" onClick={() => setReads(reads.filter((_, j) => j !== i))}>
                  ✕
                </button>
              </td>
            </tr>
          ))}
          {!reads.length && (
            <tr>
              <td colSpan={4} className="muted">
                No required reads. Without one, the read gate does not check this task: a do-nothing pass keeps its credit.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <datalist id="read-tools">
        {readTools.map((t) => (
          <option key={t} value={t} />
        ))}
      </datalist>
      <div className="add-row">
        <button className="small" onClick={() => setReads([...reads, { tool: readTools[0] || "", match: {}, why: "" }])}>
          + Read
        </button>
        {goldReads
          .filter((c) => !have.has(readKey({ tool: c.name, match: c.arguments })))
          .map((c, i) => (
            <button
              key={i}
              className="small ghost"
              title="Add this gold read"
              onClick={() => setReads([...reads, { tool: c.name, match: c.arguments, why: "from gold" }])}
            >
              + {callText(c)}
            </button>
          ))}
        {ref && JSON.stringify(ref) !== JSON.stringify(reads) && (
          <button
            className="small ghost"
            onClick={() => {
              setDraft({ ...draft, required_reads: ref });
              setVer((x) => x + 1);
            }}
          >
            Use the existing spec ({ref.length} reads)
          </button>
        )}
      </div>
      {ref && (
        <details className="ref">
          <summary>Existing spec for this task ({ref.length} reads)</summary>
          <ul>
            {ref.map((r, i) => (
              <li key={i}>
                <code>{callText({ name: [].concat(r.tool).join(" | "), arguments: r.match })}</code>{" "}
                <span className="muted">{r.why}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      {dirty && (
        <div className="dirty">
          <span>Unsaved edits.</span>
          <button
            className="small"
            onClick={() => {
              setDraft(item.current);
              setVer((x) => x + 1);
            }}
          >
            Discard
          </button>
          <button className="small primary" disabled={busy || invalid} onClick={() => save({ current: draft })}>
            Save & validate
          </button>
        </div>
      )}
      {error && <div className="banner error">{error}</div>}
      <Checks v={item.validation} />
      <ReviewFooter item={item} ctx={ctx} dirty={dirty} />
    </div>
  );
}

export function NewReads({ taskId, gold, ...ctx }) {
  const [error, setError] = useState("");
  const create = async () => {
    if (needName(ctx.reviewer)) return;
    const reads = (gold || [])
      .filter((c) => c.kind === "read" && Object.keys(c.arguments || {}).length)
      .map((c) => ({ tool: c.name, match: c.arguments, why: "from gold" }));
    try {
      const it = await api.addItem(ctx.bench.id, {
        reviewer: ctx.reviewer,
        kind: "reads",
        task_id: taskId,
        current: { required_reads: reads.length ? reads : [{ tool: "", match: {}, why: "" }] },
      });
      ctx.addLocal(it);
    } catch (e) {
      setError(e.message);
    }
  };
  return (
    <div className="empty">
      No read enforcement proposed for this task.{" "}
      <button className="small" onClick={create}>
        Write one
      </button>
      {error && <div className="banner error">{error}</div>}
    </div>
  );
}

// --- twins -------------------------------------------------------------------------------

export function TwinCard({ item, ...ctx }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.current);
  const [ver, setVer] = useState(0); // remount the JSON inputs after a discard or a save
  useEffect(() => {
    setDraft(item.current);
    setVer((x) => x + 1);
  }, [item.current]);
  const { save, busy, error } = useSave(ctx, item);
  const [validating, setValidating] = useState(false);
  const cur = item.current;
  const v = item.validation;
  const dirty = JSON.stringify(draft) !== JSON.stringify(cur);
  const invalid = draft.patch === undefined || draft.write.arguments === undefined;
  const isPolicy = cur.policy_flip || !cur.patch || !Object.keys(cur.patch).length;

  const revalidate = async () => {
    setValidating(true);
    try {
      ctx.setItem(await api.validateItem(ctx.bench.id, item.id));
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className={"item twin status-" + item.status}>
      <div className="item-head">
        <h3>
          {cur.name} <span className="pill kind">{isPolicy ? "policy twin" : "DB twin"}</span>
        </h3>
        <span className="grow" />
        <button className="small" onClick={() => setEditing(!editing)}>
          {editing ? "Close editor" : "Edit"}
        </button>
      </div>
      {cur.why && <p className="why">{cur.why}</p>}
      <div className="twin-body">
        <div>
          <h4>The flip</h4>
          {cur.policy_flip && (
            <div>
              Policy flip <code>{cur.policy_flip}</code> (see below or the Policy flips tab)
            </div>
          )}
          {v?.diff?.length ? (
            <table className="diff">
              <thead>
                <tr>
                  <th>State field</th>
                  <th>Before</th>
                  <th>After</th>
                </tr>
              </thead>
              <tbody>
                {v.diff.map((d) => (
                  <tr key={d.path.join(".")}>
                    <td>
                      <code>{d.path.join(".")}</code>
                    </td>
                    <td className="before">{compact(d.before)}</td>
                    <td className="after">{compact(d.after)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : cur.patch && Object.keys(cur.patch).length ? (
            <pre className="small-pre">{pretty(cur.patch)}</pre>
          ) : (
            !cur.policy_flip && <div className="muted">No state change.</div>
          )}
          <h4>Now correct</h4>
          <code className="call">{callText(cur.write)}</code>
        </div>
        <div>
          <h4>
            Checked with the benchmark's grader{" "}
            <button className="small ghost" disabled={validating} onClick={revalidate}>
              {validating ? "Validating…" : "Re-validate"}
            </button>
          </h4>
          <Checks
            v={v}
            rows={
              v && [
                ["do nothing, original", v.null_orig, 1, "The original task still passes with no action"],
                ["do nothing, twin", v.null_twin, 0, "Doing nothing must fail the twin"],
                ["comply, original", v.comply_orig, 0, "Doing the write must fail the original"],
                ["comply, twin", v.comply_twin, 1, "Gold reads + the write must pass the twin"],
                ["patch changes state", v.effective, true, ""],
                ["patch is local", v.local, true, "Only the records the patch names change"],
              ]
            }
          />
        </div>
      </div>
      {editing && (
        <div className="editor" key={ver}>
          <label className="field">
            Why (one sentence: what changed and why the write is now correct)
            <textarea rows={2} value={draft.why || ""} onChange={(e) => setDraft({ ...draft, why: e.target.value })} />
          </label>
          <div className="two">
            <label className="field">
              Write tool
              <input
                list="write-tools"
                value={draft.write.name}
                onChange={(e) => setDraft({ ...draft, write: { ...draft.write, name: e.target.value } })}
              />
            </label>
            <label className="field">
              Write arguments (JSON)
              <JsonInput
                value={draft.write.arguments}
                onChange={(a) => setDraft({ ...draft, write: { ...draft.write, arguments: a } })}
              />
            </label>
          </div>
          <label className="field">
            Patch of the start state (JSON, deep-merged)
            <JsonInput rows={6} value={draft.patch || {}} onChange={(p) => setDraft({ ...draft, patch: p })} />
          </label>
          <label className="field">
            Policy flip id (empty for a DB twin)
            <input
              value={draft.policy_flip || ""}
              onChange={(e) => setDraft({ ...draft, policy_flip: e.target.value || null })}
            />
          </label>
          <datalist id="write-tools">
            {ctx.tools
              .filter((t) => t.kind === "write")
              .map((t) => (
                <option key={t.name} value={t.name} />
              ))}
          </datalist>
          <div className="dirty">
            <button
              className="small"
              disabled={!dirty}
              onClick={() => {
                setDraft(cur);
                setVer((x) => x + 1);
              }}
            >
              Discard
            </button>
            <button
              className="small primary"
              disabled={!dirty || invalid || busy}
              onClick={async () => (await save({ current: draft })) && setEditing(false)}
            >
              {busy ? "Validating…" : "Save & validate"}
            </button>
          </div>
        </div>
      )}
      {error && <div className="banner error">{error}</div>}
      <ReviewFooter item={item} ctx={ctx} dirty={dirty && editing} />
    </div>
  );
}

export function NewTwin({ taskId, gold, ...ctx }) {
  const [open, setOpen] = useState(false);
  const goldWrite = (gold || []).find((c) => c.kind === "write");
  const blank = {
    task: taskId,
    name: "",
    patch: {},
    write: goldWrite ? { name: goldWrite.name, arguments: goldWrite.arguments } : { name: "", arguments: {} },
    why: "",
    policy_flip: null,
  };
  const [draft, setDraft] = useState(blank);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!open)
    return (
      <button className="small add-twin" onClick={() => setOpen(true)}>
        + Add a twin
      </button>
    );
  const create = async () => {
    if (needName(ctx.reviewer)) return;
    setBusy(true);
    try {
      const it = await api.addItem(ctx.bench.id, { reviewer: ctx.reviewer, kind: "twin", task_id: taskId, current: draft });
      ctx.addLocal(it);
      setOpen(false);
      setDraft(blank);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="item editor new">
      <h3>New twin for task {taskId}</h3>
      <div className="two">
        <label className="field">
          Name (short, lowercase)
          <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value.replace(/[^a-z0-9_]/g, "_") })} />
        </label>
        <label className="field">
          Policy flip id (empty for a DB twin)
          <input value={draft.policy_flip || ""} onChange={(e) => setDraft({ ...draft, policy_flip: e.target.value || null })} />
        </label>
      </div>
      <div className="two">
        <label className="field">
          Write tool
          <input list="write-tools-new" value={draft.write.name} onChange={(e) => setDraft({ ...draft, write: { ...draft.write, name: e.target.value } })} />
        </label>
        <label className="field">
          Write arguments (JSON)
          <JsonInput value={draft.write.arguments} onChange={(a) => setDraft({ ...draft, write: { ...draft.write, arguments: a } })} />
        </label>
      </div>
      <datalist id="write-tools-new">
        {ctx.tools.filter((t) => t.kind === "write").map((t) => (
          <option key={t.name} value={t.name} />
        ))}
      </datalist>
      <label className="field">
        Patch of the start state (JSON)
        <JsonInput rows={4} value={draft.patch} onChange={(p) => setDraft({ ...draft, patch: p })} placeholder='{"reservations": {"ABC123": {"cabin": "business"}}}' />
      </label>
      <label className="field">
        Why
        <textarea rows={2} value={draft.why} onChange={(e) => setDraft({ ...draft, why: e.target.value })} />
      </label>
      <div className="dirty">
        <button className="small" onClick={() => setOpen(false)}>
          Cancel
        </button>
        <button className="small primary" disabled={busy || !draft.name || !draft.write.name || draft.patch === undefined || draft.write.arguments === undefined} onClick={create}>
          {busy ? "Validating…" : "Add & validate"}
        </button>
      </div>
      {error && <div className="banner error">{error}</div>}
    </div>
  );
}

// --- policy flips ------------------------------------------------------------------------

export function FlipCard({ item, ...ctx }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.current);
  useEffect(() => setDraft(item.current), [item.current]);
  const { save, busy, error } = useSave(ctx, item);
  const cur = item.current;
  const v = item.validation;
  const dirty = JSON.stringify(draft) !== JSON.stringify(cur);
  const diff = wordDiff(cur.original.trim(), cur.replacement.trim());
  return (
    <div className={"item flip status-" + item.status}>
      <div className="item-head">
        <h3>
          {item.id.slice(5)} <span className="pill kind">policy flip</span>
        </h3>
        {cur.extra?.rule && (
          <span className="muted small">
            rule <code>{cur.extra.rule}</code> → {String(cur.extra.value)}
          </span>
        )}
        <span className="grow" />
        <button className="small" onClick={() => setEditing(!editing)}>
          {editing ? "Close editor" : "Edit"}
        </button>
      </div>
      <div className="policy-diff">
        {v?.context_before && <span className="ctx">…{v.context_before.slice(-160)}</span>}
        {diff.map((d, i) => (
          <span key={i} className={d.op}>
            {d.text}
          </span>
        ))}
        {v?.context_after && <span className="ctx">{v.context_after.slice(0, 160)}…</span>}
      </div>
      <div className="muted small">
        Found {v?.count ?? "?"} time(s) in the policy.
        {v?.twins?.length > 0 && ` Used by: ${v.twins.map((t) => t.slice(5)).join(", ")}.`}
      </div>
      <Checks v={v} />
      {editing && (
        <div className="editor">
          <label className="field">
            Original sentence (must occur exactly once in the policy)
            <textarea rows={4} value={draft.original} onChange={(e) => setDraft({ ...draft, original: e.target.value })} />
          </label>
          <label className="field">
            Replacement
            <textarea rows={4} value={draft.replacement} onChange={(e) => setDraft({ ...draft, replacement: e.target.value })} />
          </label>
          <div className="dirty">
            <button className="small" disabled={!dirty} onClick={() => setDraft(cur)}>
              Discard
            </button>
            <button className="small primary" disabled={!dirty || busy} onClick={async () => (await save({ current: draft })) && setEditing(false)}>
              Save & check
            </button>
          </div>
        </div>
      )}
      {error && <div className="banner error">{error}</div>}
      <ReviewFooter item={item} ctx={ctx} dirty={dirty && editing} />
    </div>
  );
}

export function NewFlip(ctx) {
  const [open, setOpen] = useState(false);
  const [id, setId] = useState("");
  const [draft, setDraft] = useState({ original: "", replacement: "", extra: {} });
  const [error, setError] = useState("");
  if (!open)
    return (
      <button className="small" onClick={() => setOpen(true)}>
        + Add a policy flip
      </button>
    );
  return (
    <div className="item editor new">
      <h3>New policy flip</h3>
      <label className="field">
        Id (lowercase, digits, _)
        <input value={id} onChange={(e) => setId(e.target.value.replace(/[^a-z0-9_]/g, "_"))} />
      </label>
      <label className="field">
        Original sentence (copy it exactly from the policy)
        <textarea rows={3} value={draft.original} onChange={(e) => setDraft({ ...draft, original: e.target.value })} />
      </label>
      <label className="field">
        Replacement
        <textarea rows={3} value={draft.replacement} onChange={(e) => setDraft({ ...draft, replacement: e.target.value })} />
      </label>
      <div className="dirty">
        <button className="small" onClick={() => setOpen(false)}>
          Cancel
        </button>
        <button
          className="small primary"
          disabled={!id || !draft.original}
          onClick={async () => {
            if (needName(ctx.reviewer)) return;
            try {
              ctx.addLocal(await api.addItem(ctx.bench.id, { reviewer: ctx.reviewer, kind: "flip", id, current: draft }));
              setOpen(false);
            } catch (e) {
              setError(e.message);
            }
          }}
        >
          Add & check
        </button>
      </div>
      {error && <div className="banner error">{error}</div>}
    </div>
  );
}
