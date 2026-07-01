const BASE = "/api";

export async function fetchFreeModels() {
  const res = await fetch(`${BASE}/models/free`);
  if (!res.ok) throw new Error("failed to fetch free models");
  return res.json();
}

export async function fetchPlugins() {
  const res = await fetch(`${BASE}/plugins`);
  if (!res.ok) throw new Error("failed to fetch plugin catalog");
  return res.json();
}

export async function createJob({ referenceFile, sampleFile, goalText, topology }) {
  const form = new FormData();
  form.append("reference", referenceFile);
  form.append("sample", sampleFile);
  form.append("goal_text", goalText);
  form.append("topology", topology.join(","));

  const res = await fetch(`${BASE}/jobs`, { method: "POST", body: form });
  if (!res.ok) throw new Error("failed to create job");
  return res.json();
}

export async function fetchJob(jobId) {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error("failed to fetch job");
  return res.json();
}

export function manifestUrl(jobId) {
  return `${BASE}/jobs/${jobId}/manifest`;
}

export function containerManifestUrl(jobId) {
  return `${BASE}/jobs/${jobId}/container-manifest`;
}

export function audioUrl(jobId) {
  return `${BASE}/jobs/${jobId}/audio`;
}
