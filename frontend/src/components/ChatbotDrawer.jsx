import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, X, User } from 'lucide-react';
import { sendChatMessage } from '../api';

const NO_DATASET_SUGGESTIONS = [
  'How does attrition analysis work?',
  'What are top causes of employee turnover?',
  'How should I format my CSV file?',
  'Tell me a witty joke about work',
];

const ACTIVE_DATASET_SUGGESTIONS = [
  'Tell me about employee #101',
  'Who is likely to leave?',
  'Why do employees leave?',
  'Which department has highest attrition?',
  'Overtime impact',
  'What recommendations do you have?',
];

export default function ChatbotDrawer({ datasetInfo = {} }) {
  const hasDataset = Boolean(datasetInfo && datasetInfo.has_dataset);
  const [isOpen, setIsOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [suggestions, setSuggestions] = useState(
    hasDataset ? ACTIVE_DATASET_SUGGESTIONS : NO_DATASET_SUGGESTIONS
  );

  const initialBotText = hasDataset
    ? `👋 **Welcome to AttritionAI!**\n\nI'm currently analyzing **\`${datasetInfo.dataset_name || 'Active Dataset'}\`** (${(datasetInfo.total_employees || 0).toLocaleString()} records, ${datasetInfo.attrition_rate}% attrition).\n\nAsk me about any specific employee (e.g. *\"Tell me about employee #101\"*), department turnover, flight risks, or retention recommendations!`
    : "👋 **Welcome to AttritionAI!**\n\nI'm your workforce intelligence copilot powered by **Google Gemini**.\n\nNo CSV dataset is loaded yet. Upload your employee CSV file on the dashboard to generate instant metrics, or chat freely about general HR and workforce strategy!";

  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'bot',
      source: 'Gemini AI',
      time: 'Just now',
      text: initialBotText,
    },
  ]);

  const prevDatasetRef = useRef(datasetInfo.dataset_name);

  // Update suggestions and messages when dataset changes
  useEffect(() => {
    if (datasetInfo.has_dataset && datasetInfo.dataset_name && prevDatasetRef.current !== datasetInfo.dataset_name) {
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setSuggestions(ACTIVE_DATASET_SUGGESTIONS);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          sender: 'bot',
          source: 'Dataset Loaded',
          time,
          text: `📁 **Dataset Loaded!**\n\nNow analyzing **\`${datasetInfo.dataset_name}\`** (${(datasetInfo.total_employees || 0).toLocaleString()} records, ${datasetInfo.attrition_rate}% flight risk).\n\nAsk me anything about this cohort!`,
        },
      ]);
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
  }, [datasetInfo.has_dataset, datasetInfo.dataset_name, datasetInfo.total_employees, datasetInfo.attrition_rate]);

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
      // 2. Call backend
      const res = await sendChatMessage(text);
      const botTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const source = res.source === 'gemini_ai' ? 'Gemini AI' : 'HR Analytics';

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

      // 4. Update suggestions if provided
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

  // Safe markdown converter for bold, italics, bullets, newlines
  const renderFormattedText = (rawText) => {
    if (!rawText) return null;

    // Split paragraphs
    const paragraphs = rawText.split('\n\n');

    return paragraphs.map((para, pIdx) => {
      const lines = para.split('\n');
      const isBulletList = lines.every((line) => line.trim().startsWith('*') || line.trim().startsWith('•') || line.trim().startsWith('-'));

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
      .replace(/\*(.*?)\*/g, '<em>$1</em>');
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
                  <span>Online • Gemini 2.5 Flash</span>
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

          {/* Suggestions Chips */}
          <div className="chat-chips">
            {suggestions.map((s) => (
              <button
                key={s}
                className="chip-btn"
                onClick={() => handleSend(s)}
                disabled={isSending}
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
              placeholder="Ask anything or chat freely..."
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
