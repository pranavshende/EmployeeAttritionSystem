/**
 * API client for communicating with Flask backend.
 * Uses VITE_API_BASE_URL if set in environment (e.g. Render production URL),
 * falling back to relative paths for local dev proxy.
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  ''
).replace(/\/$/, '');

export async function fetchKPIs() {
  const res = await fetch(`${API_BASE_URL}/api/kpis`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchChart(name) {
  const res = await fetch(`${API_BASE_URL}/api/charts/${name}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchHighRisk(page = 1, limit = 15) {
  const res = await fetch(`${API_BASE_URL}/api/high-risk?page=${page}&limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchFilterOptions() {
  const res = await fetch(`${API_BASE_URL}/api/filters`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchFiltered(params = {}) {
  const query = new URLSearchParams(params).toString();
  const url = query ? `${API_BASE_URL}/api/filtered?${query}` : `${API_BASE_URL}/api/filtered`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function sendChatMessage(message, sessionId = 'default') {
  const res = await fetch(`${API_BASE_URL}/api/chatbot/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchChatbotSuggestions() {
  const res = await fetch(`${API_BASE_URL}/api/chatbot/suggestions`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchDatasetInfo() {
  const res = await fetch(`${API_BASE_URL}/api/dataset/info`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function uploadDataset(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/api/dataset/upload`, {
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
  const res = await fetch(`${API_BASE_URL}/api/dataset/clear`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function clearDataset() {
  const res = await fetch(`${API_BASE_URL}/api/dataset/clear`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function loadSampleDataset() {
  const res = await fetch(`${API_BASE_URL}/api/dataset/load-sample`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchDatasetProfile() {
  const res = await fetch(`${API_BASE_URL}/api/dataset/profile`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE_URL}/api/documents`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function uploadDocument(file, title = '', category = 'Policy') {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  if (category) formData.append('category', category);

  const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function deleteDocument(docId) {
  const res = await fetch(`${API_BASE_URL}/api/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}


