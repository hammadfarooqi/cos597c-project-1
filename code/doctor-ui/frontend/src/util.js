// Small helpers: word diff, JSON text, task ordering, hash routing.

import { useEffect, useState } from "react";

// Word-level diff (LCS). Returns [{op: "same"|"del"|"add", text}].
export function wordDiff(a, b) {
  const x = a.split(/(\s+)/);
  const y = b.split(/(\s+)/);
  const n = x.length;
  const m = y.length;
  const L = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      L[i][j] = x[i] === y[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out = [];
  const push = (op, text) => {
    const last = out[out.length - 1];
    if (last && last.op === op) last.text += text;
    else out.push({ op, text });
  };
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (x[i] === y[j]) {
      push("same", x[i]);
      i++;
      j++;
    } else if (L[i + 1][j] >= L[i][j + 1]) push("del", x[i++]);
    else push("add", y[j++]);
  }
  while (i < n) push("del", x[i++]);
  while (j < m) push("add", y[j++]);
  return out;
}

export const pretty = (v) => JSON.stringify(v, null, 2);

export function compact(v) {
  if (v === undefined) return "";
  if (v === null) return "null";
  if (v && typeof v === "object" && v._clipped) return v._clipped;
  return typeof v === "string" ? JSON.stringify(v) : JSON.stringify(v);
}

export function callText(c) {
  const args = Object.entries(c.arguments || {})
    .map(([k, v]) => `${k}=${compact(v)}`)
    .join(", ");
  return `${c.name}(${args})`;
}

export function natural(a, b) {
  const na = /^\d+$/.test(a);
  const nb = /^\d+$/.test(b);
  if (na && nb) return Number(a) - Number(b);
  if (na !== nb) return na ? -1 : 1;
  return a.localeCompare(b);
}

// Hash routes: #/b/<bench>[/task/<id> | /flips | /export | /settings]
export function useRoute() {
  const parse = () => {
    const parts = window.location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
    if (parts[0] !== "b" || !parts[1]) return { bench: null };
    return { bench: parts[1], view: parts[2] || "tasks", arg: parts[3] };
  };
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    const on = () => setRoute(parse());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function go(...parts) {
  window.location.hash = "/" + parts.map(encodeURIComponent).join("/");
}

export function useLocal(key, initial) {
  const [v, setV] = useState(() => {
    try {
      const s = localStorage.getItem(key);
      return s === null ? initial : JSON.parse(s);
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(v));
    } catch {
      /* private window: keep it in memory only */
    }
  }, [key, v]);
  return [v, setV];
}
