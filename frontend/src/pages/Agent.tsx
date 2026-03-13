import { useState, useRef, useEffect, type KeyboardEvent, type ChangeEvent } from 'react';
import { useAgentChat, type ChatMessage, type ToolCall } from '../hooks/useAgentChat';

// ── Markdown-lite renderer ──────────────────────────────────────────

function renderContent(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const codeBlockRe = /```(\w*)\n?([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = codeBlockRe.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(...renderInline(text.slice(lastIndex, match.index), key));
      key += 100;
    }
    const lang = match[1];
    let code = match[2].trim();
    if (lang?.toLowerCase() === 'json') {
      try { code = JSON.stringify(JSON.parse(code), null, 2); } catch { /* keep as-is */ }
    }
    nodes.push(
      <div key={`cb-${key++}`} className="my-2 rounded border border-alien-green/30 bg-alien-black overflow-x-auto">
        {lang && (
          <div className="text-[10px] text-alien-text-dim px-3 py-1 border-b border-alien-border uppercase tracking-wider">
            {lang}
          </div>
        )}
        <pre className="p-3 text-xs text-alien-text font-mono whitespace-pre-wrap break-all">{code}</pre>
      </div>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    nodes.push(...renderInline(text.slice(lastIndex), key));
  }

  return nodes;
}

function renderInline(text: string, baseKey: number): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const inlineRe = /`([^`]+)`|\*\*(.+?)\*\*/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let k = baseKey;

  while ((match = inlineRe.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(<span key={k++}>{text.slice(last, match.index)}</span>);
    }
    if (match[1] !== undefined) {
      parts.push(
        <code key={k++} className="text-alien-cyan bg-alien-black/60 px-1.5 py-0.5 rounded text-xs font-mono">
          {match[1]}
        </code>
      );
    } else if (match[2] !== undefined) {
      parts.push(<strong key={k++} className="text-alien-text font-bold">{match[2]}</strong>);
    }
    last = match.index + match[0].length;
  }

  if (last < text.length) {
    parts.push(<span key={k++}>{text.slice(last)}</span>);
  }

  return parts;
}

// ── Tool Call Card ──────────────────────────────────────────────────

function ToolCallCard({ tool }: { tool: ToolCall }) {
  const [inputOpen, setInputOpen] = useState(false);
  const [resultOpen, setResultOpen] = useState(false);

  const statusIcon = tool.status === 'running'
    ? <span className="inline-block w-3 h-3 border-2 border-alien-cyan border-t-transparent rounded-full animate-spin" />
    : tool.status === 'error'
    ? <span className="text-alien-red">&#x2717;</span>
    : <span className="text-alien-green">&#x2713;</span>;

  const formatJson = (val: unknown): string => {
    try { return JSON.stringify(val, null, 2); } catch { return String(val); }
  };

  return (
    <div className="my-2 border border-alien-cyan/30 rounded-lg bg-alien-dark/80 overflow-hidden animate-slide-in">
      <div className="flex items-center gap-2 px-3 py-2 bg-alien-cyan/5 border-b border-alien-cyan/20">
        <span className="text-alien-cyan text-xs">&#x2699;</span>
        {statusIcon}
        <span className="text-alien-cyan text-xs font-mono font-bold flex-1 truncate">{tool.name}</span>
      </div>

      {Object.keys(tool.input).length > 0 && (
        <div className="border-b border-alien-border/50">
          <button
            onClick={() => setInputOpen(!inputOpen)}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-[10px] text-alien-text-dim hover:text-alien-cyan transition-colors"
          >
            <span className={`transition-transform ${inputOpen ? 'rotate-90' : ''}`}>&#x25B6;</span>
            <span className="uppercase tracking-wider">Input</span>
          </button>
          {inputOpen && (
            <pre className="px-3 pb-2 text-[11px] text-alien-text font-mono whitespace-pre-wrap break-all max-h-48 overflow-auto">
              {formatJson(tool.input)}
            </pre>
          )}
        </div>
      )}

      {tool.result !== undefined && (
        <div>
          <button
            onClick={() => setResultOpen(!resultOpen)}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-[10px] text-alien-text-dim hover:text-alien-cyan transition-colors"
          >
            <span className={`transition-transform ${resultOpen ? 'rotate-90' : ''}`}>&#x25B6;</span>
            <span className="uppercase tracking-wider">Result</span>
          </button>
          {resultOpen && (
            <pre className="px-3 pb-2 text-[11px] text-alien-text font-mono whitespace-pre-wrap break-all max-h-64 overflow-auto">
              {formatJson(tool.result)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

// ── Message Bubble ──────────────────────────────────────────────────

function MessageBubble({ msg, isStreaming }: { msg: ChatMessage; isStreaming: boolean }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end mb-3 animate-slide-in">
        <div className="max-w-[85%] sm:max-w-[70%] bg-alien-dark border border-alien-green/30 rounded-lg px-3 py-2 sm:px-4 sm:py-3">
          <p className="text-alien-text text-sm whitespace-pre-wrap break-words">{msg.content}</p>
          <div className="text-[9px] text-alien-text-dim mt-1.5 text-right">
            {msg.timestamp.toLocaleTimeString()}
          </div>
        </div>
      </div>
    );
  }

  // Assistant message
  const showCursor = isStreaming && msg.content.length > 0;
  const showThinking = isStreaming && msg.content.length === 0 && (!msg.toolCalls || msg.toolCalls.length === 0);

  return (
    <div className="flex justify-start mb-3 animate-slide-in">
      <div className="max-w-[90%] sm:max-w-[75%] w-full">
        {showThinking && (
          <div className="flex items-center gap-2 text-alien-cyan text-xs mb-2">
            <span className="inline-block w-3 h-3 border-2 border-alien-cyan border-t-transparent rounded-full animate-spin" />
            <span className="animate-flicker">thinking...</span>
          </div>
        )}

        {msg.content && (
          <div className="bg-alien-panel border border-alien-border rounded-lg px-3 py-2 sm:px-4 sm:py-3 mb-1">
            <div className="text-alien-text text-sm leading-relaxed whitespace-pre-wrap break-words">
              {renderContent(msg.content)}
              {showCursor && <span className="inline-block w-1.5 h-4 bg-alien-green ml-0.5 animate-flicker align-text-bottom" />}
            </div>
          </div>
        )}

        {msg.toolCalls && msg.toolCalls.length > 0 && (
          <div className="space-y-1">
            {msg.toolCalls.map((tc) => (
              <ToolCallCard key={tc.id} tool={tc} />
            ))}
          </div>
        )}

        {msg.content && (
          <div className="text-[9px] text-alien-text-dim mt-1">
            {msg.timestamp.toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Empty State ─────────────────────────────────────────────────────

const SUGGESTIONS = [
  'Scan all traffic for vulnerabilities',
  'Analyze the most recent requests',
  'Show me requests to suspicious hosts',
  'Generate a security report',
];

function EmptyState({ onSend }: { onSend: (text: string) => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4">
      <div className="text-alien-green text-3xl sm:text-5xl font-bold glow-text mb-2">@</div>
      <h2 className="text-alien-text text-base sm:text-lg font-bold mb-1">Intercept37 Agent</h2>
      <p className="text-alien-text-dim text-xs sm:text-sm mb-6 text-center max-w-md">
        AI-powered security analysis. Ask me to scan, analyze, or investigate your intercepted traffic.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSend(s)}
            className="text-left px-3 py-2.5 rounded-lg border border-alien-border bg-alien-panel hover:border-alien-green/40 hover:bg-alien-green/5 text-alien-text-dim hover:text-alien-green text-xs transition-all duration-200"
          >
            <span className="text-alien-green mr-1.5">&gt;</span>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main Agent Page ─────────────────────────────────────────────────

export default function Agent() {
  const { messages, isStreaming, sendMessage, clearSession, sessionId } = useAgentChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Auto-resize textarea
  const handleInput = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const ta = e.target;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  };

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const shortSession = sessionId.slice(0, 8);

  return (
    <div className="flex flex-col h-full -m-2 sm:-m-4">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between px-3 py-2 border-b border-alien-border bg-alien-dark/50">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-alien-green font-bold text-sm">@</span>
          <span className="text-alien-text text-xs font-bold uppercase tracking-wider">Agent</span>
          <span className="text-alien-text-dim text-[10px] hidden sm:inline truncate">
            session:{shortSession}
          </span>
        </div>
        <button
          onClick={clearSession}
          className="text-[10px] text-alien-text-dim hover:text-alien-red border border-alien-border hover:border-alien-red/40 px-2 py-1 rounded transition-colors uppercase tracking-wider flex-shrink-0"
        >
          Clear
        </button>
      </div>

      {/* Messages area */}
      {messages.length === 0 ? (
        <EmptyState onSend={sendMessage} />
      ) : (
        <div className="flex-1 overflow-y-auto px-2 sm:px-4 py-3 space-y-1">
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              msg={msg}
              isStreaming={isStreaming && msg.id === messages[messages.length - 1]?.id}
            />
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input bar */}
      <div className="flex-shrink-0 border-t border-alien-border bg-alien-dark/80 px-2 sm:px-4 py-2 sm:py-3">
        <div className="flex items-end gap-2 max-w-4xl mx-auto">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            placeholder={isStreaming ? 'Waiting for response...' : 'Ask the agent...'}
            rows={1}
            className="flex-1 bg-alien-panel border border-alien-border focus:border-alien-green/50 rounded-lg px-3 py-2.5 text-sm text-alien-text placeholder-alien-text-dim resize-none outline-none transition-colors font-mono min-h-[40px] max-h-[120px] disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="flex-shrink-0 bg-alien-green/20 hover:bg-alien-green/30 disabled:bg-alien-border disabled:text-alien-text-dim text-alien-green border border-alien-green/40 disabled:border-alien-border rounded-lg px-4 py-2.5 text-sm font-bold uppercase tracking-wider transition-all duration-200 min-h-[40px]"
          >
            Send
          </button>
        </div>
        <div className="text-[9px] text-alien-text-dim text-center mt-1.5 sm:hidden">
          session:{shortSession}
        </div>
      </div>
    </div>
  );
}
