/**
 * Chatbot UI and Messaging Controller
 * Supports rule-based attrition answers and Gemini generative chat
 */

const Chatbot = {
  isOpen: false,
  isSending: false,

  init() {
    this.setupEventListeners();
    this.setupSuggestions();
  },

  setupEventListeners() {
    const fab = document.getElementById('chatbotFab');
    const panel = document.getElementById('chatbotPanel');
    const closeBtn = document.getElementById('chatCloseBtn');
    const sendBtn = document.getElementById('chatSendBtn');
    const input = document.getElementById('chatInput');

    if (fab) {
      fab.addEventListener('click', () => this.toggleChat());
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.closeChat());
    }

    if (sendBtn) {
      sendBtn.addEventListener('click', () => this.handleSendMessage());
    }

    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.handleSendMessage();
        }
      });
    }
  },

  setupSuggestions() {
    const container = document.getElementById('chatSuggestions');
    if (!container) return;

    container.addEventListener('click', (e) => {
      const btn = e.target.closest('.suggestion-btn');
      if (btn) {
        const query = btn.getAttribute('data-query') || btn.textContent.trim();
        this.sendMessage(query);
      }
    });
  },

  updateSuggestions(suggestions) {
    const container = document.getElementById('chatSuggestions');
    if (!container || !suggestions || suggestions.length === 0) return;

    container.innerHTML = suggestions.map(s => `
      <button class="suggestion-btn" data-query="${s}">${s}</button>
    `).join('');
  },

  toggleChat() {
    if (this.isOpen) {
      this.closeChat();
    } else {
      this.openChat();
    }
  },

  openChat() {
    const panel = document.getElementById('chatbotPanel');
    const fab = document.getElementById('chatbotFab');
    const input = document.getElementById('chatInput');

    if (panel) panel.classList.add('open');
    if (fab) fab.classList.add('active');
    this.isOpen = true;

    if (input) setTimeout(() => input.focus(), 200);
    this.scrollToBottom();
  },

  closeChat() {
    const panel = document.getElementById('chatbotPanel');
    const fab = document.getElementById('chatbotFab');

    if (panel) panel.classList.remove('open');
    if (fab) fab.classList.remove('active');
    this.isOpen = false;
  },

  async handleSendMessage() {
    const input = document.getElementById('chatInput');
    if (!input || this.isSending) return;

    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    await this.sendMessage(message);
  },

  sessionId: 'vanilla_' + Math.random().toString(36).substring(2, 9),

  async sendMessage(message) {
    if (this.isSending) return;
    this.isSending = true;

    // Make sure panel is open
    if (!this.isOpen) this.openChat();

    // 1. Add user message bubble
    this.appendUserMessage(message);

    // 2. Add typing indicator
    const typingId = this.showTypingIndicator();

    try {
      // 3. Call backend endpoint with sessionId
      const result = await API.sendChatMessage(message, this.sessionId);

      // 4. Remove typing indicator
      this.removeTypingIndicator(typingId);

      // 5. Add bot response
      let source = 'HR Analytics';
      if (result.source === 'gemini_ai') source = 'Gemini AI';
      else if (result.source === 'hybrid_rag') source = 'Hybrid RAG + Gemini';
      else if (result.source === 'deterministic_rag') source = 'HR Policy Base';
      else if (result.source === 'deterministic_analytics') source = 'Full-Dataset Engine';

      this.appendBotMessage(result.response, source, result.citations);

      // 6. Update suggestions if available
      if (result.suggestions && result.suggestions.length > 0) {
        this.updateSuggestions(result.suggestions);
      }
    } catch (err) {
      console.error('Chat error:', err);
      this.removeTypingIndicator(typingId);
      this.appendBotMessage(
        "⚠️ Sorry, I encountered an error communicating with the server. Please try again.",
        "System"
      );
    } finally {
      this.isSending = false;
    }
  },

  appendUserMessage(text) {
    const messages = document.getElementById('chatMessages');
    if (!messages) return;

    const time = this.getCurrentTime();
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message user';
    msgDiv.innerHTML = `
      <div class="chat-message-avatar">
        <i data-lucide="user" style="width: 14px; height: 14px; color: var(--accent-purple);"></i>
      </div>
      <div>
        <div class="chat-bubble">${this.escapeHtml(text)}</div>
        <div class="chat-time">${time}</div>
      </div>
    `;

    messages.appendChild(msgDiv);
    if (window.lucide) lucide.createIcons();
    this.scrollToBottom();
  },

  appendBotMessage(markdownText, sourceLabel, citations = []) {
    const messages = document.getElementById('chatMessages');
    if (!messages) return;

    const time = this.getCurrentTime();
    const formattedHtml = this.formatMarkdown(markdownText);
    const sourceBadge = sourceLabel ? `<span style="font-size: 0.65rem; color: var(--accent-cyan); margin-left: 6px; font-weight: 600;">• ${sourceLabel}</span>` : '';

    let citationsHtml = '';
    if (citations && citations.length > 0) {
      const items = citations.map(c => `
        <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 4px 8px; margin-top: 4px; font-size: 0.7rem;">
          <div style="font-weight: 600; color: #fff;">📄 ${this.escapeHtml(c.title || '')} <span style="color: var(--accent-cyan); font-size: 0.65rem;">${this.escapeHtml(c.section || '')}</span></div>
          ${c.content ? `<div style="color: #94a3b8; font-size: 0.65rem; font-style: italic; margin-top: 2px;">"${this.escapeHtml(c.content.substring(0, 100))}..."</div>` : ''}
        </div>
      `).join('');

      citationsHtml = `
        <div style="margin-top: 8px; padding-top: 6px; border-top: 1px dashed rgba(255,255,255,0.15);">
          <div style="font-size: 0.65rem; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Document References (${citations.length})</div>
          ${items}
        </div>
      `;
    }

    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message bot';
    msgDiv.innerHTML = `
      <div class="chat-message-avatar">
        <i data-lucide="bot" style="width: 14px; height: 14px; color: #fff;"></i>
      </div>
      <div>
        <div class="chat-bubble">
          ${formattedHtml}
          ${citationsHtml}
        </div>
        <div class="chat-time">${time} ${sourceBadge}</div>
      </div>
    `;

    messages.appendChild(msgDiv);
    if (window.lucide) lucide.createIcons();
    this.scrollToBottom();
  },

  showTypingIndicator() {
    const messages = document.getElementById('chatMessages');
    if (!messages) return null;

    const id = 'typing-' + Date.now();
    const typingDiv = document.createElement('div');
    typingDiv.id = id;
    typingDiv.className = 'chat-message bot';
    typingDiv.innerHTML = `
      <div class="chat-message-avatar">
        <i data-lucide="bot" style="width: 14px; height: 14px; color: #fff;"></i>
      </div>
      <div class="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    `;

    messages.appendChild(typingDiv);
    if (window.lucide) lucide.createIcons();
    this.scrollToBottom();
    return id;
  },

  removeTypingIndicator(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
  },

  scrollToBottom() {
    const messages = document.getElementById('chatMessages');
    if (messages) {
      setTimeout(() => {
        messages.scrollTop = messages.scrollHeight;
      }, 50);
    }
  },

  getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  },

  escapeHtml(str) {
    const p = document.createElement('p');
    p.textContent = str;
    return p.innerHTML;
  },

  formatMarkdown(text) {
    if (!text) return '';

    let html = this.escapeHtml(text);

    // Bold: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic: *text* or _text_
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Bullet points
    html = html.replace(/^•\s+(.*)$/gm, '<li style="margin-left: 16px; margin-bottom: 4px;">$1</li>');
    html = html.replace(/(<li.*<\/li>)/s, '<ul style="padding-left: 4px; margin: 6px 0;">$1</ul>');

    // Line breaks
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');

    return html;
  }
};
