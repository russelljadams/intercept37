import { useState, useRef, useEffect, type KeyboardEvent, type ChangeEvent } from "react";
import type { ChatMessage, ToolCall, ContentBlock } from "../hooks/useAgentChat";

// ── Props ───────────────────────────────────────────────────────────

export interface ChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  isStreaming: boolean;
  sendMessage: (text: string) => void;
  clearSession: () => void;
}

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
    if (lang?.toLowerCase() === "json") {
      try { code = JSON.stringify(JSON.parse(code), null, 2); } catch { /* keep */ }
    }
    nodes.push(
      <div key={`cb-${key++}`} className="my-2 rounded border border-alien-green/30 bg-alien-black overflow-x-auto">
        {lang && (
          <div className="text-[10px] text-alien-text-dim px-3 py-1 border-b border-alien-border uppercase tracking-wider">{lang}</div>
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
    if (match.index > last) parts.push(<span key={k++}>{text.slice(last, match.index)}</span>);
    if (match[1] !== undefined) {
      parts.push(<code key={k++} className="text-alien-cyan bg-alien-black/60 px-1.5 py-0.5 rounded text-xs font-mono">{match[1]}</code>);
    } else if (match[2] !== undefined) {
      parts.push(<strong key={k++} className="text-alien-text font-bold">{match[2]}</strong>);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(<span key={k++}>{text.slice(last)}</span>);
  return parts;
}

// ── Tool Call Card ──────────────────────────────────────────────────

function ToolCallCard({ tool }: { tool: ToolCall }) {
  const [inputOpen, setInputOpen] = useState(false);
  const [resultOpen, setResultOpen] = useState(false);

  const statusIcon = tool.status === "running"
    ? <span className="inline-block w-3 h-3 border-2 border-alien-cyan border-t-transparent rounded-full animate-spin" />
    : tool.status === "error"
    ? <span className="text-alien-red">&#x2717;</span>
    : <span className="text-alien-green">&#x2713;</span>;

  const formatJson = (val: unknown): string => {
    try { return JSON.stringify(val, null, 2); } catch { return String(val); }
  };

  return (
    <div className="my-1.5 border border-alien-cyan/30 rounded bg-alien-dark/80 overflow-hidden text-xs">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-alien-cyan/5">
        <span className="text-alien-cyan">&#x2699;</span>
        {statusIcon}
        <span className="text-alien-cyan font-mono font-bold flex-1 truncate">{tool.name}</span>
      </div>
      {Object.keys(tool.input).length > 0 && (
        <div className="border-t border-alien-border/30">
          <button onClick={() => setInputOpen(!inputOpen)} className="w-full flex items-center gap-2 px-3 py-1 text-[10px] text-alien-text-dim hover:text-alien-cyan">
            <span className={`transition-transform ${inputOpen ? "rotate-90" : ""}`}>&#x25B6;</span> Input
          </button>
          {inputOpen && <pre className="px-3 pb-2 text-[10px] text-alien-text font-mono whitespace-pre-wrap break-all max-h-32 overflow-auto">{formatJson(tool.input)}</pre>}
        </div>
      )}
      {tool.result !== undefined && (
        <div className="border-t border-alien-border/30">
          <button onClick={() => setResultOpen(!resultOpen)} className="w-full flex items-center gap-2 px-3 py-1 text-[10px] text-alien-text-dim hover:text-alien-cyan">
            <span className={`transition-transform ${resultOpen ? "rotate-90" : ""}`}>&#x25B6;</span> Result
          </button>
          {resultOpen && <pre className="px-3 pb-2 text-[10px] text-alien-text font-mono whitespace-pre-wrap break-all max-h-48 overflow-auto">{formatJson(tool.result)}</pre>}
        </div>
      )}
    </div>
  );
}

// ── Content Block Renderer ──────────────────────────────────────────

function BlockRenderer({ block, isLast, isStreaming }: { block: ContentBlock; isLast: boolean; isStreaming: boolean }) {
  if (block.type === "text" && block.text) {
    const showCursor = isLast && isStreaming;
    return (
      <div className="bg-alien-panel border border-alien-border rounded-lg px-3 py-2 my-1.5">
        <div className="text-alien-text text-sm leading-relaxed whitespace-pre-wrap break-words">
          {renderContent(block.text)}
          {showCursor && <span className="inline-block w-1.5 h-4 bg-alien-green ml-0.5 animate-flicker align-text-bottom" />}
        </div>
      </div>
    );
  }
  if (block.type === "tool" && block.tool) {
    return <ToolCallCard tool={block.tool} />;
  }
  return null;
}

// ── Message Bubble ──────────────────────────────────────────────────

function MessageBubble({ msg, isStreaming }: { msg: ChatMessage; isStreaming: boolean }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[85%] bg-alien-dark border border-alien-green/30 rounded-lg px-3 py-2">
          <p className="text-alien-text text-sm whitespace-pre-wrap break-words">{msg.content}</p>
          <div className="text-[9px] text-alien-text-dim mt-1.5 text-right">{msg.timestamp.toLocaleTimeString()}</div>
        </div>
      </div>
    );
  }

  const showThinking = isStreaming && msg.blocks.length === 0;

  return (
    <div className="flex justify-start mb-3">
      <div className="max-w-[90%] w-full">
        {showThinking && (
          <div className="flex items-center gap-2 text-alien-cyan text-xs mb-2">
            <span className="inline-block w-3 h-3 border-2 border-alien-cyan border-t-transparent rounded-full animate-spin" />
            <span className="animate-flicker">thinking...</span>
          </div>
        )}
        {msg.blocks.map((block, i) => (
          <BlockRenderer key={i} block={block} isLast={i === msg.blocks.length - 1} isStreaming={isStreaming} />
        ))}
        {msg.blocks.length > 0 && (
          <div className="text-[9px] text-alien-text-dim mt-1">{msg.timestamp.toLocaleTimeString()}</div>
        )}
      </div>
    </div>
  );
}

// ── Suggestions ─────────────────────────────────────────────────────

const SUGGESTIONS = [
  "Crawl https://example.com and analyze what you find",
  "Scan all captured traffic for vulnerabilities",
  "Show me a summary of everything intercepted so far",
  "Generate a security report",
];

function EmptyState({ onSend }: { onSend: (text: string) => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4">
      <div className="text-alien-green text-3xl font-bold glow-text mb-2">@</div>
      <h2 className="text-alien-text text-base font-bold mb-1">Intercept37 Agent</h2>
      <p className="text-alien-text-dim text-xs mb-6 text-center max-w-md">
        AI-powered pentesting. I can crawl targets, intercept traffic, scan for vulnerabilities, and generate reports.
      </p>
      <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
        {SUGGESTIONS.map((s) => (
          <button key={s} onClick={() => onSend(s)}
            className="text-left px-3 py-2.5 rounded-lg border border-alien-border bg-alien-panel hover:border-alien-green/40 hover:bg-alien-green/5 text-alien-text-dim hover:text-alien-green text-xs transition-all">
            <span className="text-alien-green mr-1.5">&gt;</span>{s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Chat Panel ──────────────────────────────────────────────────────

export default function ChatPanel({ isOpen, onClose, messages, isStreaming, sendMessage, clearSession }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  // Focus textarea when panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => textareaRef.current?.focus(), 300);
    }
  }, [isOpen]);

  const handleInput = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
  };

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 hidden sm:block"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`fixed top-0 right-0 z-50 h-full w-full sm:w-[420px] lg:w-[480px] bg-alien-dark border-l border-alien-border flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex-shrink-0 flex items-center justify-between px-3 py-2 border-b border-alien-border bg-alien-dark/90">
          <div className="flex items-center gap-2">
            <span className="text-alien-green font-bold text-sm">@</span>
            <span className="text-alien-text text-xs font-bold uppercase tracking-wider">Agent</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={clearSession}
              className="text-[10px] text-alien-text-dim hover:text-alien-red border border-alien-border hover:border-alien-red/40 px-2 py-1 rounded transition-colors uppercase tracking-wider">
              Clear
            </button>
            <button onClick={onClose}
              className="text-alien-text-dim hover:text-alien-green text-lg leading-none px-1 transition-colors">
              &#x2715;
            </button>
          </div>
        </div>

        {/* Messages */}
        {messages.length === 0 ? (
          <EmptyState onSend={sendMessage} />
        ) : (
          <div className="flex-1 overflow-y-auto px-2 py-3">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} isStreaming={isStreaming && msg.id === messages[messages.length - 1]?.id} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Input */}
        <div className="flex-shrink-0 border-t border-alien-border bg-alien-dark/80 px-2 py-2">
          <div className="flex items-end gap-2">
            <textarea ref={textareaRef} value={input} onChange={handleInput} onKeyDown={handleKeyDown}
              disabled={isStreaming} placeholder={isStreaming ? "Waiting for response..." : "Ask the agent..."}
              rows={1}
              className="flex-1 bg-alien-panel border border-alien-border focus:border-alien-green/50 rounded-lg px-3 py-2.5 text-sm text-alien-text placeholder-alien-text-dim resize-none outline-none transition-colors font-mono min-h-[40px] max-h-[120px] disabled:opacity-50" />
            <button onClick={handleSend} disabled={isStreaming || !input.trim()}
              className="flex-shrink-0 bg-alien-green/20 hover:bg-alien-green/30 disabled:bg-alien-border disabled:text-alien-text-dim text-alien-green border border-alien-green/40 disabled:border-alien-border rounded-lg px-4 py-2.5 text-sm font-bold uppercase tracking-wider transition-all min-h-[40px]">
              Send
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
