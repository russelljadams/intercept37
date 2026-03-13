import { useState, useCallback, useRef } from 'react';

export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  result?: unknown;
  status: 'running' | 'done' | 'error';
}

// A content block is either text or a tool call, in sequence
export interface ContentBlock {
  type: 'text' | 'tool';
  text?: string;
  tool?: ToolCall;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string; // raw text for user messages
  blocks: ContentBlock[]; // interleaved blocks for assistant messages
  timestamp: Date;
}

export interface UseAgentChatReturn {
  messages: ChatMessage[];
  isStreaming: boolean;
  sendMessage: (text: string) => void;
  clearSession: () => void;
  sessionId: string;
}

function generateId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function useAgentChat(): UseAgentChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionIdRef = useRef(generateId());
  const abortRef = useRef<AbortController | null>(null);

  const clearSession = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setMessages([]);
    setIsStreaming(false);
    sessionIdRef.current = generateId();
    // Also clear on backend
    fetch(`/api/chat/${sessionIdRef.current}`, { method: 'DELETE' }).catch(() => {});
  }, []);

  const sendMessage = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;

    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: trimmed,
      blocks: [],
      timestamp: new Date(),
    };

    const assistantId = generateId();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      blocks: [],
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionIdRef.current, message: trimmed }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine.startsWith('data: ')) continue;

            let event: Record<string, unknown>;
            try {
              event = JSON.parse(trimmedLine.slice(6));
            } catch {
              continue;
            }

            if (event.type === 'text') {
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== assistantId) return m;
                  const blocks = [...m.blocks];
                  const last = blocks[blocks.length - 1];
                  // Append to existing text block or create new one
                  if (last && last.type === 'text') {
                    blocks[blocks.length - 1] = { ...last, text: (last.text ?? '') + (event.content as string ?? '') };
                  } else {
                    blocks.push({ type: 'text', text: event.content as string ?? '' });
                  }
                  return { ...m, blocks };
                })
              );
            } else if (event.type === 'tool_use') {
              const toolCall: ToolCall = {
                id: (event.id as string) ?? generateId(),
                name: (event.name as string) ?? 'unknown',
                input: (event.input as Record<string, unknown>) ?? {},
                status: 'running',
              };
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== assistantId) return m;
                  return { ...m, blocks: [...m.blocks, { type: 'tool', tool: toolCall }] };
                })
              );
            } else if (event.type === 'tool_result') {
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== assistantId) return m;
                  const blocks = m.blocks.map((b) => {
                    if (b.type === 'tool' && b.tool && (b.tool.name === (event.name as string))) {
                      // Match by name since the backend yields name not id
                      if (b.tool.status === 'running') {
                        return { ...b, tool: { ...b.tool, result: event.result, status: 'done' as const } };
                      }
                    }
                    return b;
                  });
                  return { ...m, blocks };
                })
              );
            } else if (event.type === 'error') {
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== assistantId) return m;
                  return { ...m, blocks: [...m.blocks, { type: 'text', text: `\n\n**Error:** ${event.content ?? event.error ?? 'Unknown error'}` }] };
                })
              );
              setIsStreaming(false);
            } else if (event.type === 'done') {
              setIsStreaming(false);
            }
          }
        }

        setIsStreaming(false);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        const errorMsg = err instanceof Error ? err.message : 'Connection failed';
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, blocks: [...m.blocks, { type: 'text' as const, text: `\n\n**Error:** ${errorMsg}` }] }
              : m
          )
        );
        setIsStreaming(false);
      });
  }, [isStreaming]);

  return {
    messages,
    isStreaming,
    sendMessage,
    clearSession,
    sessionId: sessionIdRef.current,
  };
}
