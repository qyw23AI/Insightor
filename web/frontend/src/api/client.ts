/* API client — all backend calls */

const BASE = '/api';

function headers(token?: string): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
}

async function handle(res: Response) {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || res.statusText);
  }
  return res.json();
}

// Auth
export async function register(username: string, password: string) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ username, password }),
  });
  return handle(res);
}

export async function login(username: string, password: string) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ username, password }),
  });
  return handle(res);
}

export async function getMe(token: string) {
  const res = await fetch(`${BASE}/auth/me`, { headers: headers(token) });
  return handle(res);
}

// Admin
export async function listUsers(token: string) {
  const res = await fetch(`${BASE}/admin/users`, { headers: headers(token) });
  return handle(res);
}

export async function deleteUser(token: string, userId: string) {
  const res = await fetch(`${BASE}/admin/users/${userId}`, { method: 'DELETE', headers: headers(token) });
  return handle(res);
}

// Config
export async function getConfig(token: string) {
  const res = await fetch(`${BASE}/config`, { headers: headers(token) });
  return handle(res);
}

export async function getConfigMasked(token: string) {
  const res = await fetch(`${BASE}/config/masked`, { headers: headers(token) });
  return handle(res);
}

export async function saveConfig(token: string, configs: Record<string, string>) {
  const res = await fetch(`${BASE}/config`, {
    method: 'PUT', headers: headers(token), body: JSON.stringify({ configs }),
  });
  return handle(res);
}

// PR
export async function getPREntries(token: string) {
  const res = await fetch(`${BASE}/pr/entries`, { headers: headers(token) });
  return handle(res);
}

export async function addPREntries(token: string, pr_urls: string[]) {
  const res = await fetch(`${BASE}/pr/entries`, {
    method: 'POST', headers: headers(token), body: JSON.stringify({ pr_urls }),
  });
  return handle(res);
}

export async function deletePREntry(token: string, entryId: string) {
  const res = await fetch(`${BASE}/pr/entries/${entryId}`, { method: 'DELETE', headers: headers(token) });
  return handle(res);
}

// Analyze
export async function startAnalysis(token: string, pr_urls: string[], tool: string, depth: string, model?: string) {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST', headers: headers(token),
    body: JSON.stringify({ pr_urls, tool, depth, model }),
  });
  return handle(res);
}

export function getStreamUrl(jobId: string) {
  return `${BASE}/analyze/${jobId}/stream`;
}

export async function getJobResult(jobId: string) {
  const res = await fetch(`${BASE}/analyze/${jobId}/result`);
  return handle(res);
}

export async function getJobInfo(jobId: string) {
  const res = await fetch(`${BASE}/analyze/${jobId}/info`);
  return handle(res);
}

export async function batchJobInfo(jobIds: string[]) {
  const res = await fetch(`${BASE}/analyze/jobs/info`, {
    method: 'POST', headers: headers(), body: JSON.stringify(jobIds),
  });
  return handle(res);
}

// Reviews
export async function getReviews(token: string, status?: string) {
  const query = status ? `?status=${status}` : '';
  const res = await fetch(`${BASE}/reviews${query}`, { headers: headers(token) });
  return handle(res);
}

export async function getReview(token: string, reviewId: string) {
  const res = await fetch(`${BASE}/reviews/${reviewId}`, { headers: headers(token) });
  return handle(res);
}

export async function getReviewDiff(token: string, reviewId: string) {
  const res = await fetch(`${BASE}/reviews/${reviewId}/diff`, { headers: headers(token) });
  return handle(res);
}

export async function publishReview(token: string, reviewId: string, feedbacks: Array<{finding_id: string; status: string; note: string | null; reviewer: string | null}>) {
  const res = await fetch(`${BASE}/reviews/${reviewId}/publish`, {
    method: 'POST', headers: headers(token), body: JSON.stringify({ feedbacks }),
  });
  return handle(res);
}

export async function deleteReview(token: string, reviewId: string) {
  const res = await fetch(`${BASE}/reviews/${reviewId}`, { method: 'DELETE', headers: headers(token) });
  return handle(res);
}
