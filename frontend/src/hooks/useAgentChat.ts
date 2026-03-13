import { useState, useCallback, useRef } from 'react';

export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  result?: unknown;
  status: 'running' | 'done' | 'error';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
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
  }, []);

  const sendMessage = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;

    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    };

    const assistantId = generateId();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      toolCalls: [],
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

            let event: { type: string; content?: string; id?: string; name?: string; input?: Record<string, unknown>; tool_call_id?: string; result?: unknown; error?: string };
            try {
              event = JSON.parse(trimmedLine.slice(6));
            } catch {
              continue;
            }

            if (event.type === 'text') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + (event.content ?? '') }
                    : m
                )
              );
            } else if (event.type === 'tool_use') {
              const toolCall: ToolCall = {
                id: event.id ?? generateId(),
                name: event.name ?? 'unknown',
                input: event.input ?? {},
                status: 'running',
              };
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, toolCalls: [...(m.toolCalls ?? []), toolCall] }
                    : m
                )
              );
            } else if (event.type === 'tool_result') {
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== assistantId) return m;
                  const calls = (m.toolCalls ?? []).map((tc) =>
                    tc.id === event.tool_call_id
                      ? { ...tc, result: event.result, status: 'done' as const }
                      : tc
                  );
                  return { ...m, toolCalls: calls };
                })
              );
            } else if (event.type === 'error') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + `\n\n**Error:** ${event.error ?? 'Unknown error'}` }
                    : m
                )
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
              ? { ...m, content: m.content + `\n\n**Error:** ${errorMsg}` }
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
