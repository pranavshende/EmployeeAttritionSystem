import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, X, RefreshCw } from 'lucide-react';
import { sendChatMessage, fetchChatbotSuggestions } from '../api';

const NO_DATASET_SUGGESTIONS = [
  'How does employee attrition analysis work?',
  'What CSV columns should my dataset include?',
  'How do I upload an employee dataset?',
  'What are top indicators of employee turnover?',
];

export default function ChatbotDrawer({ datasetInfo = {} }) {
  const hasDataset = Boolean(datasetInfo && datasetInfo.has_dataset);
  const [isOpen, setIsOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [suggestions, setSuggestions] = useState(
    datasetInfo.suggested_questions && datasetInfo.suggested_questions.length > 0
      ? datasetInfo.suggested_questions
      : NO_DATASET_SUGGESTIONS
  );

  // Unique session ID for persistent conversational context
  const sessionIdRef = useRef('session_' + Math.random().toString(36).substring(2, 9));

  const initialBotText = hasDataset
    ? `👋 **Welcome to AttritionAI!**\n\nI am dynamically analyzing **\`${datasetInfo.dataset_name || 'Active Dataset'}\`** (${(datasetInfo.total_employees || 0).toLocaleString()} records, ${datasetInfo.attrition_rate}% attrition).\n\nAsk about individual employees (e.g. *\"Tell me about employee #{id}\"*), department deep dives, comparisons, flight risks, or retention recommendations!`
    : "👋 **Welcome to AttritionAI!**\n\nI'm your workforce analytics intelligence assistant.\n\nNo CSV dataset is loaded yet. Upload your employee CSV file on the dashboard to generate instant metrics, or ask how attrition analysis works!";

  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'bot',
      source: 'Workforce Copilot',
      time: 'Just now',
      text: initialBotText,
    },
  ]);

  const prevDatasetRef = useRef(datasetInfo.dataset_name);

  // Load dynamic dataset-tailored questions when dataset changes
  useEffect(() => {
    const updateDynamicSuggestions = async () => {
      if (datasetInfo.has_dataset && datasetInfo.dataset_name) {
        if (datasetInfo.suggested_questions && datasetInfo.suggested_questions.length > 0) {
          setSuggestions(datasetInfo.suggested_questions);
        } else {
          try {
            const data = await fetchChatbotSuggestions();
            if (data.suggestions && data.suggestions.length > 0) {
              setSuggestions(data.suggestions);
            }
          } catch (e) {
            console.warn('Failed to load dynamic suggestions:', e);
          }
        }

        if (prevDatasetRef.current !== datasetInfo.dataset_name) {
          const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now(),
              sender: 'bot',
              source: 'Dataset Ingested',
              time,
              text: `📁 **Dataset Activated!**\n\nNow analyzing **\`${datasetInfo.dataset_name}\`** (${(datasetInfo.total_employees || 0).toLocaleString()} records, ${datasetInfo.attrition_rate}% attrition).\n\nDynamic questions for this specific cohort are ready below!`,
            },
          ]);
        }
      } else if (!datasetInfo.has_dataset && prevDatasetRef.current) {
        setSuggestions(NO_DATASET_SUGGESTIONS);
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            sender: 'bot',
            source: 'System',
            time,
            text: '🔄 **Dataset cleared.** Waiting for a new CSV upload to resume cohort analysis.',
          },
        ]);
      }
      prevDatasetRef.current = datasetInfo.dataset_name;
    };

    updateDynamicSuggestions();
  }, [datasetInfo.has_dataset, datasetInfo.dataset_name, datasetInfo.total_employees, datasetInfo.attrition_rate, datasetInfo.suggested_questions]);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, isSending]);

  const handleSend = async (messageToSend) => {
    const text = (messageToSend || inputMessage).trim();
    if (!text || isSending) return;

    const userTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // 1. Add user message
    const userMsg = {
      id: Date.now(),
      sender: 'user',
      time: userTime,
      text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsSending(true);

    try {
      // 2. Call backend with persistent session ID
      const res = await sendChatMessage(text, sessionIdRef.current);
      const botTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const source = res.source === 'gemini_ai' ? 'Gemini AI' : 'HR Analytics Engine';

      // 3. Add bot message
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'bot',
          source,
          time: botTime,
          text: res.response || "I've processed your query.",
        },
      ]);

      // 4. Update suggestions if provided by backend
      if (res.suggestions && res.suggestions.length > 0) {
        setSuggestions(res.suggestions);
      }
    } catch (err) {
      console.error('Chatbot error:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'bot',
          source: 'System',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: '⚠️ Unable to connect to the assistant right now. Please verify the backend server is running.',
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  // Safe markdown converter with table, bold, italics, bullets, newlines
  const renderFormattedText = (rawText) => {
    if (!rawText) return null;

    // Split paragraphs by double newline
    const paragraphs = rawText.split('\n\n');

    return paragraphs.map((para, pIdx) => {
      const lines = para.split('\n');

      // Check if this paragraph is a Markdown Table
      const isTable =
        lines.length >= 2 &&
        lines[0].trim().startsWith('|') &&
        lines[1].includes('---');

      if (isTable) {
        const headerCells = lines[0]
          .split('|')
          .map((c) => c.trim())
          .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

        const dataRows = lines
          .slice(2)
          .filter((l) => l.trim().startsWith('|'))
          .map((l) =>
            l
              .split('|')
              .map((c) => c.trim())
              .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
          );

        return (
          <div key={pIdx} className="chat-table-wrapper">
            <table className="chat-table">
              <thead>
                <tr>
                  {headerCells.map((h, hIdx) => (
                    <th key={hIdx} dangerouslySetInnerHTML={{ __html: formatInline(h) }} />
                  ))}
                </tr>
              </thead>
              <tbody>
                {dataRows.map((row, rIdx) => (
                  <tr key={rIdx}>
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} dangerouslySetInnerHTML={{ __html: formatInline(cell) }} />
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }

      // Check if bullet list
      const isBulletList = lines.every(
        (line) => line.trim().startsWith('*') || line.trim().startsWith('•') || line.trim().startsWith('-')
      );

      if (isBulletList) {
        return (
          <ul key={pIdx}>
            {lines.map((line, lIdx) => {
              const clean = line.replace(/^[\*\•\-]\s*/, '');
              return <li key={lIdx} dangerouslySetInnerHTML={{ __html: formatInline(clean) }} />;
            })}
          </ul>
        );
      }

      return (
        <p key={pIdx} style={{ marginBottom: pIdx < paragraphs.length - 1 ? '8px' : 0 }}>
          {lines.map((line, lIdx) => (
            <React.Fragment key={lIdx}>
              <span dangerouslySetInnerHTML={{ __html: formatInline(line) }} />
              {lIdx < lines.length - 1 && <br />}
            </React.Fragment>
          ))}
        </p>
      );
    });
  };

  const formatInline = (str) => {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code class="chat-code">$1</code>');
  };

  return (
    <>
      {/* Floating Action Button */}
      <button
        className="chatbot-fab"
        onClick={() => setIsOpen(!isOpen)}
        title={isOpen ? 'Close Chatbot' : 'Open AttritionAI Copilot'}
        aria-label="Open AI Chatbot"
      >
        <Bot size={28} />
      </button>

      {/* Slide-out Drawer */}
      {isOpen && (
        <aside className="chatbot-drawer" role="dialog" aria-label="AttritionAI Assistant">
          {/* Header */}
          <div className="drawer-header">
            <div className="drawer-header-left">
              <div className="chat-avatar-circle">
                <Bot size={20} />
              </div>
              <div>
                <div className="drawer-bot-title">AttritionAI</div>
                <div className="drawer-bot-status">
                  <span className="white-dot"></span>
                  <span>{hasDataset ? `Online • ${datasetInfo.dataset_name || 'Active Cohort'}` : 'Online • Ready for CSV'}</span>
                </div>
              </div>
            </div>
            <button
              className="btn-close-chat"
              onClick={() => setIsOpen(false)}
              title="Close chat"
              aria-label="Close"
            >
              <X size={16} />
            </button>
          </div>

          {/* Messages Body */}
          <div className="chat-body">
            {messages.map((m) => (
              <div key={m.id} className={`chat-msg ${m.sender}`}>
                <div className="bubble">
                  {renderFormattedText(m.text)}
                  <div className="bubble-meta">
                    {m.time}
                    {m.source && (
                      <span style={{ marginLeft: '6px', fontWeight: 600, color: 'var(--primary-600)' }}>
                        • {m.source}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {isSending && (
              <div className="chat-msg bot">
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Dynamic Suggestions Chips (Derived only from active dataset) */}
          <div className="chat-chips">
            {suggestions.map((s, idx) => (
              <button
                key={`${s}-${idx}`}
                className="chip-btn"
                onClick={() => handleSend(s)}
                disabled={isSending}
                title={s}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Input Footer */}
          <div className="chat-footer">
            <input
              type="text"
              className="chat-text-input"
              placeholder={hasDataset ? "Ask about employees, depts, risk factors..." : "Ask how attrition analysis works..."}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isSending}
            />
            <button
              className="btn-chat-send"
              onClick={() => handleSend()}
              disabled={isSending}
              title="Send"
              aria-label="Send message"
            >
              <Send size={16} />
            </button>
          </div>
        </aside>
      )}
    </>
  );
}
