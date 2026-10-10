// Thin wrapper over the backend API (backend/app.py).

async function req(method, path, body) {
  const r = await fetch(`/api${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => null);
  if (!r.ok) throw new Error((data && data.detail) || `${r.status} ${r.statusText}`);
  return data;
}

const enc = encodeURIComponent;

export const api = {
  benchmarks: () => req("GET", "/benchmarks"),
  benchmark: (b) => req("GET", `/benchmarks/${enc(b)}`),
  addBenchmark: (body) => req("POST", "/benchmarks", body),
  updateBenchmark: (b, body) => req("PATCH", `/benchmarks/${enc(b)}`, body),
  deleteBenchmark: (b) => req("DELETE", `/benchmarks/${enc(b)}`),
  setup: (b) => req("POST", `/benchmarks/${enc(b)}/setup`),
  checkup: (b) => req("POST", `/benchmarks/${enc(b)}/checkup`),
  validateAll: (b) => req("POST", `/benchmarks/${enc(b)}/validate-all`),
  job: (b) => req("GET", `/benchmarks/${enc(b)}/job`),
  review: (b) => req("GET", `/benchmarks/${enc(b)}/review`),
  task: (b, t) => req("GET", `/benchmarks/${enc(b)}/tasks/${enc(t)}`),
  policy: (b) => req("GET", `/benchmarks/${enc(b)}/policy`),
  updateItem: (b, id, body) => req("PUT", `/benchmarks/${enc(b)}/items/${enc(id)}`, body),
  addItem: (b, body) => req("POST", `/benchmarks/${enc(b)}/items`, body),
  validateItem: (b, id) => req("POST", `/benchmarks/${enc(b)}/items/${enc(id)}/validate`),
  deleteItem: (b, id) => req("DELETE", `/benchmarks/${enc(b)}/items/${enc(id)}`),
  exportSpecs: (b, dest) => req("POST", `/benchmarks/${enc(b)}/export`, { dest: dest || null }),
};
