import { useState, useEffect, useCallback } from 'react';
import { useRequests } from '../hooks/useApi';
import { useWebSocket } from '../hooks/useWebSocket';
import { MethodBadge, StatusBadge } from '../components/StatusBadge';
import RequestInspector from '../components/RequestInspector';

const METHODS = ['', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'];
const PAGE_SIZE = 50;

export default function Traffic() {
  const [method, setMethod] = useState('');
  const [host, setHost] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [debouncedHost, setDebouncedHost] = useState('');

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); setDebouncedHost(host); }, 300);
    return () => clearTimeout(t);
  }, [search, host]);

  const { data, loading, refetch } = useRequests({
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    method: method || undefined,
    host: debouncedHost || undefined,
    status: statusFilter ? Number(statusFilter) : undefined,
    search: debouncedSearch || undefined,
  });

  const { lastMessage } = useWebSocket();

  // Auto-refresh on new websocket messages
  useEffect(() => {
    if (lastMessage?.type === 'new_request') {
      refetch();
    }
  }, [lastMessage, refetch]);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const requests = data?.data || [];

  const formatTime = useCallback((ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  }, []);

  return (
    <div className="space-y-4 animate-slide-in h-full flex flex-col">
      {/* Filters */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <select
          value={method}
          onChange={(e) => { setMethod(e.target.value); setPage(0); }}
          className="bg-alien-black border border-alien-border rounded px-3 py-1.5 text-xs text-alien-text focus:border-alien-green/50 focus:outline-none"
        >
          <option value="">All Methods</option>
          {METHODS.filter(Boolean).map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>

        <input
          value={host}
          onChange={(e) => { setHost(e.target.value); setPage(0); }}
          placeholder="Filter host..."
          className="bg-alien-black border border-alien-border rounded px-3 py-1.5 text-xs text-alien-text placeholder:text-alien-text-dim/50 focus:border-alien-green/50 focus:outline-none w-48"
        />

        <input
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value.replace(/\D/g, '')); setPage(0); }}
          placeholder="Status code"
          className="bg-alien-black border border-alien-border rounded px-3 py-1.5 text-xs text-alien-text placeholder:text-alien-text-dim/50 focus:border-alien-green/50 focus:outline-none w-28"
        />

        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          placeholder="Search requests..."
          className="flex-1 bg-alien-black border border-alien-border rounded px-3 py-1.5 text-xs text-alien-text placeholder:text-alien-text-dim/50 focus:border-alien-green/50 focus:outline-none"
        />

        <button
          onClick={refetch}
          className="px-3 py-1.5 text-xs text-alien-green border border-alien-green/30 rounded hover:bg-alien-green/10 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto bg-alien-panel border border-alien-border rounded-lg">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-alien-dark border-b border-alien-border z-10">
            <tr className="text-alien-text-dim uppercase tracking-wider text-[10px]">
              <th className="text-left py-2.5 px-3 w-12">#</th>
              <th className="text-left py-2.5 px-3 w-20">Method</th>
              <th className="text-left py-2.5 px-3 w-40">Host</th>
              <th className="text-left py-2.5 px-3">Path</th>
              <th className="text-left py-2.5 px-3 w-16">Status</th>
              <th className="text-left py-2.5 px-3 w-28">Content-Type</th>
              <th className="text-left py-2.5 px-3 w-16">Time</th>
              <th className="text-left py-2.5 px-3 w-20">Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {loading && requests.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-8 text-alien-text-dim">
                  Loading...
                </td>
              </tr>
            ) : requests.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-8 text-alien-text-dim">
                  No requests captured. Traffic will appear here when the proxy intercepts requests.
                </td>
              </tr>
            ) : (
              requests.map((req) => (
                <tr
                  key={req.id}
                  onClick={() => setSelectedId(req.id)}
                  className="border-b border-alien-border/20 hover:bg-alien-green/5 cursor-pointer transition-colors"
                >
                  <td className="py-2 px-3 text-alien-text-dim">{req.id}</td>
                  <td className="py-2 px-3"><MethodBadge method={req.method} /></td>
                  <td className="py-2 px-3 text-alien-text truncate max-w-[160px]">{req.host}</td>
                  <td className="py-2 px-3 text-alien-text truncate max-w-[300px]">{req.path}</td>
                  <td className="py-2 px-3"><StatusBadge code={req.status_code} /></td>
                  <td className="py-2 px-3 text-alien-text-dim truncate max-w-[110px]">{req.content_type || '-'}</td>
                  <td className="py-2 px-3 text-alien-text-dim">{req.response_time}ms</td>
                  <td className="py-2 px-3 text-alien-text-dim">{formatTime(req.timestamp)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between flex-shrink-0">
          <span className="text-alien-text-dim text-xs">
            Page {page + 1} of {totalPages} ({data?.total} total)
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-3 py-1 text-xs border border-alien-border rounded text-alien-text-dim hover:text-alien-green hover:border-alien-green/30 disabled:opacity-30 transition-colors"
            >
              Prev
            </button>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="px-3 py-1 text-xs border border-alien-border rounded text-alien-text-dim hover:text-alien-green hover:border-alien-green/30 disabled:opacity-30 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Request Inspector Modal */}
      {selectedId !== null && (
        <RequestInspector requestId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  );
}
