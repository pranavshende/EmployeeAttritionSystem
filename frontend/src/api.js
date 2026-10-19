/**
 * API client for communicating with Flask backend
 */

export async function fetchKPIs() {
  const res = await fetch('/api/kpis');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchChart(name) {
  const res = await fetch(`/api/charts/${name}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchHighRisk(page = 1, limit = 15) {
  const res = await fetch(`/api/high-risk?page=${page}&limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchFilterOptions() {
  const res = await fetch('/api/filters');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchFiltered(params = {}) {
  const query = new URLSearchParams(params).toString();
  const url = query ? `/api/filtered?${query}` : '/api/filtered';
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function sendChatMessage(message) {
  const res = await fetch('/api/chatbot/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchDatasetInfo() {
  const res = await fetch('/api/dataset/info');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function uploadDataset(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/api/dataset/upload', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function resetDataset() {
  const res = await fetch('/api/dataset/clear', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function clearDataset() {
  const res = await fetch('/api/dataset/clear', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function loadSampleDataset() {
  const res = await fetch('/api/dataset/load-sample', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP ${res.status}`);
  }
  return await res.json();
}


