import { useState } from 'react';
import { MethodBadge, StatusBadge } from '../components/StatusBadge';
import api from '../api/client';

interface HistoryEntry {
  id: number;
  method: string;
  url: string;
  status: number;
  time: number;
  response_body: string;
  response_headers: Record<string, string>;
}

const DEFAULT_HEADERS = `Host: example.com
User-Agent: Intercept37/0.1
Accept: */*`;

export default function Repeater() {
  const [method, setMethod] = useState('GET');
  const [url, setUrl] = useState('');
  const [headers, setHeaders] = useState(DEFAULT_HEADERS);
  const [body, setBody] = useState('');
  const [sending, setSending] = useState(false);
  const [response, setResponse] = useState<{
    status: number;
    headers: Record<string, string>;
    body: string;
    time: number;
  } | null>(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyCounter, setHistoryCounter] = useState(0);
  const [showHistory, setShowHistory] = useState(false);

  const parseHeaders = (raw: string): Record<string, string> => {
    const result: Record<string, string> = {};
    raw.split('\n').forEach((line) => {
      const idx = line.indexOf(':');
      if (idx > 0) {
        result[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
      }
    });
    return result;
  };

  const handleSend = async () => {
    if (!url.trim()) { setError('URL is required'); return; }
    setSending(true);
    setError('');
    setResponse(null);
    try {
      const start = Date.now();
      const { data } = await api.post('/requests/send', {
        method,
        url: url.trim(),
        headers: parseHeaders(headers),
        body: body || undefined,
      });
      const elapsed = Date.now() - start;
      const resp = {
        status: data.status_code || 200,
        headers: data.response_headers || {},
        body: data.response_body || '',
        time: data.response_time || elapsed,
      };
      setResponse(resp);
      const entry: HistoryEntry = {
        id: historyCounter,
        method,
        url: url.trim(),
        status: resp.status,
        time: resp.time,
        response_body: resp.body,
        response_headers: resp.headers,
      };
      setHistory((prev) => [entry, ...prev].slice(0, 50));
      setHistoryCounter((c) => c + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    }
    setSending(false);
  };

  const loadFromHistory = (entry: HistoryEntry) => {
    setMethod(entry.method);
    setUrl(entry.url);
    setResponse({
      status: entry.status,
      headers: entry.response_headers,
      body: entry.response_body,
      time: entry.time,
    });
    setShowHistory(false);
  };

  const formatBody = (b: string) => {
    try { return JSON.stringify(JSON.parse(b), null, 2); } catch { return b; }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-3 sm:gap-4 h-full animate-slide-in">
      {/* Main area */}
      <div className="flex-1 flex flex-col gap-3 sm:gap-4 min-w-0">
        {/* Request Builder */}
        <div className="bg-alien-panel border border-alien-border rounded-lg p-3 sm:p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-alien-green text-xs uppercase tracking-[0.15em]">Request Builder</h3>
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="lg:hidden px-2 py-1 text-[10px] text-alien-cyan border border-alien-cyan/30 rounded"
            >
              History ({history.length})
            </button>
          </div>

          {/* Method + URL */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="bg-alien-black border border-alien-border rounded px-3 py-2 text-xs text-alien-green font-bold focus:border-alien-green/50 focus:outline-none"
            >
              {['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'].map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://target.com/api/endpoint"
              className="flex-1 bg-alien-black border border-alien-border rounded px-3 py-2 text-sm text-alien-text placeholder:text-alien-text-dim/50 focus:border-alien-green/50 focus:outline-none"
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button
              onClick={handleSend}
              disabled={sending}
              className="px-6 py-2 bg-alien-green/10 border border-alien-green/50 text-alien-green text-xs font-bold rounded hover:bg-alien-green/20 hover:shadow-alien transition-all disabled:opacity-50 tracking-wider"
            >
              {sending ? 'SENDING...' : 'SEND'}
            </button>
          </div>

          {/* Headers + Body */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-alien-text-dim text-[10px] uppercase tracking-wider block mb-1">Headers</label>
              <textarea
                value={headers}
                onChange={(e) => setHeaders(e.target.value)}
                rows={4}
                className="w-full bg-alien-black border border-alien-border rounded px-3 py-2 text-xs text-alien-text font-mono resize-none focus:border-alien-green/50 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-alien-text-dim text-[10px] uppercase tracking-wider block mb-1">Body</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={4}
                placeholder='{"key": "value"}'
                className="w-full bg-alien-black border border-alien-border rounded px-3 py-2 text-xs text-alien-text font-mono resize-none placeholder:text-alien-text-dim/30 focus:border-alien-green/50 focus:outline-none"
              />
            </div>
          </div>

          {error && <div className="text-alien-red text-xs">{error}</div>}
        </div>

        {/* Response */}
        <div className="flex-1 bg-alien-panel border border-alien-border rounded-lg p-3 sm:p-4 overflow-auto min-h-[200px]">
          <h3 className="text-alien-green text-xs uppercase tracking-[0.15em] mb-3">Response</h3>
          {!response && !sending ? (
            <div className="text-alien-text-dim text-xs text-center py-8 sm:py-12">
              Build a request above and click SEND.
            </div>
          ) : sending ? (
            <div className="text-alien-green text-xs animate-flicker text-center py-8 sm:py-12">
              Transmitting...
            </div>
          ) : response ? (
            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <StatusBadge code={response.status} />
                <span className="text-alien-text-dim text-xs">{response.time}ms</span>
              </div>
              <div>
                <h4 className="text-alien-text-dim text-[10px] uppercase tracking-wider mb-1">Headers</h4>
                <pre className="bg-alien-black border border-alien-border rounded p-2 sm:p-3 text-[10px] sm:text-xs text-alien-text-dim whitespace-pre-wrap max-h-32 overflow-auto break-all">
                  {Object.entries(response.headers).map(([k, v]) => `${k}: ${v}`).join('\n') || '(none)'}
                </pre>
              </div>
              <div>
                <h4 className="text-alien-text-dim text-[10px] uppercase tracking-wider mb-1">Body</h4>
                <pre className="bg-alien-black border border-alien-border rounded p-2 sm:p-3 text-[10px] sm:text-xs text-alien-cyan whitespace-pre-wrap overflow-auto max-h-64 sm:max-h-96 break-all">
                  {formatBody(response.body) || '(empty)'}
                </pre>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* History — mobile: dropdown overlay, desktop: sidebar */}
      {showHistory && (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setShowHistory(false)}>
          <div
            className="absolute right-0 top-0 h-full w-72 bg-alien-dark border-l border-alien-border p-3 overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-alien-green text-xs uppercase tracking-[0.15em]">History</h3>
              <button onClick={() => setShowHistory(false)} className="text-alien-text-dim text-lg">×</button>
            </div>
            <HistoryList history={history} onSelect={loadFromHistory} />
          </div>
        </div>
      )}
      <div className="hidden lg:block w-64 flex-shrink-0 bg-alien-panel border border-alien-border rounded-lg p-3 overflow-auto">
        <h3 className="text-alien-green text-xs uppercase tracking-[0.15em] mb-3">History</h3>
        <HistoryList history={history} onSelect={loadFromHistory} />
      </div>
    </div>
  );
}

function HistoryList({ history, onSelect }: { history: HistoryEntry[]; onSelect: (e: HistoryEntry) => void }) {
  if (history.length === 0) {
    return <div className="text-alien-text-dim text-[10px] text-center py-4">No requests sent yet</div>;
  }
  return (
    <div className="space-y-1">
      {history.map((entry) => (
        <button
          key={entry.id}
          onClick={() => onSelect(entry)}
          className="w-full text-left p-2 rounded hover:bg-alien-green/5 border border-transparent hover:border-alien-green/20 transition-colors"
        >
          <div className="flex items-center gap-2 mb-1">
            <MethodBadge method={entry.method} />
            <StatusBadge code={entry.status} />
            <span className="text-alien-text-dim text-[10px]">{entry.time}ms</span>
          </div>
          <div className="text-alien-text text-[10px] truncate">{entry.url}</div>
        </button>
      ))}
    </div>
  );
}
