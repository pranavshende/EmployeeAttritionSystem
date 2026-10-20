/**
 * API Service for Employee Attrition Dashboard
 * Handles all REST endpoints communication
 */

const API = {
  baseUrl: '',

  async getKPIs() {
    const res = await fetch(`${this.baseUrl}/api/kpis`);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  },

  async getChart(name) {
    const res = await fetch(`${this.baseUrl}/api/charts/${name}`);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  },

  async getHighRisk(page = 1, limit = 15) {
    const res = await fetch(`${this.baseUrl}/api/high-risk?page=${page}&limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  },

  async getFilterOptions() {
    const res = await fetch(`${this.baseUrl}/api/filters`);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  },

  async getFiltered(params = {}) {
    const query = new URLSearchParams(params).toString();
    const url = query ? `${this.baseUrl}/api/filtered?${query}` : `${this.baseUrl}/api/filtered`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  },

  async sendChatMessage(message, sessionId = 'default') {
    const res = await fetch(`${this.baseUrl}/api/chatbot/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  },

  async getDocuments() {
    const res = await fetch(`${this.baseUrl}/api/documents`);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  },

  async uploadDocument(file, title = '', category = 'Policy') {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (category) formData.append('category', category);
    const res = await fetch(`${this.baseUrl}/api/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  },
};
