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
  const [filtersOpen, setFiltersOpen] = useState(false);

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
    <div className="space-y-3 sm:space-y-4 animate-slide-in h-full flex flex-col">
      {/* Filters — collapsible on mobile */}
      <div className="flex-shrink-0">
        <div className="flex items-center gap-2 sm:hidden mb-2">
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder="Search..."
            className="flex-1 bg-alien-black border border-alien-border rounded px-3 py-1.5 text-xs text-alien-text placeholder:text-alien-text-dim/50 focus:border-alien-green/50 focus:outline-none"
          />
          <button
            onClick={() => setFiltersOpen(!filtersOpen)}
            className="px-3 py-1.5 text-xs text-alien-cyan border border-alien-cyan/30 rounded"
          >
            Filters
          </button>
          <button
            onClick={refetch}
            className="px-3 py-1.5 text-xs text-alien-green border border-alien-green/30 rounded"
          >
            ↻
          </button>
        </div>
        {filtersOpen && (
          <div className="flex flex-wrap gap-2 sm:hidden mb-2">
            <select
              value={method}
              onChange={(e) => { setMethod(e.target.value); setPage(0); }}
              className="bg-alien-black border border-alien-border rounded px-2 py-1.5 text-xs text-alien-text focus:border-alien-green/50 focus:outline-none"
            >
              <option value="">All Methods</option>
              {METHODS.filter(Boolean).map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <input
              value={host}
              onChange={(e) => { setHost(e.target.value); setPage(0); }}
              placeholder="Host..."
              className="flex-1 min-w-[100px] bg-alien-black border border-alien-border rounded px-2 py-1.5 text-xs text-alien-text placeholder:text-alien-text-dim/50 focus:border-alien-green/50 focus:outline-none"
            />
            <input
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value.replace(/\D/g, '')); setPage(0); }}
              placeholder="Status"
              className="w-20 bg-alien-black border border-alien-border rounded px-2 py-1.5 text-xs text-alien-text placeholder:text-alien-text-dim/50 focus:border-alien-green/50 focus:outline-none"
            />
          </div>
        )}

        {/* Desktop filters */}
        <div className="hidden sm:flex items-center gap-3">
          <select
            value={method}
            onChange={(e) => { setMethod(e.target.value); setPage(0); }}
            className="bg-alien-black border border-alien-border rounded px-3 py-1.5 text-xs text-alien-text focus:border-alien-green/50 focus:outline-none"
          >
            <option value="">All Methods</option>
            {METHODS.filter(Boolean).map((m) => <option key={m} value={m}>{m}</option>)}
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
      </div>

      {/* Mobile: card layout */}
      <div className="flex-1 overflow-auto sm:hidden space-y-2">
        {loading && requests.length === 0 ? (
          <div className="text-center py-8 text-alien-text-dim text-xs">Loading...</div>
        ) : requests.length === 0 ? (
          <div className="text-center py-8 text-alien-text-dim text-xs">No requests captured yet.</div>
        ) : (
          requests.map((req) => (
            <div
              key={req.id}
              onClick={() => setSelectedId(req.id)}
              className="bg-alien-panel border border-alien-border/40 rounded-lg p-3 active:bg-alien-green/5"
            >
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-alien-text-dim text-[10px]">#{req.id}</span>
                <MethodBadge method={req.method} />
                <StatusBadge code={req.status_code} />
                <span className="text-alien-text-dim text-[10px] ml-auto">{req.response_time}ms</span>
              </div>
              <div className="text-alien-text text-xs truncate">{req.host}</div>
              <div className="text-alien-text-dim text-[11px] truncate">{req.path}</div>
              <div className="text-alien-text-dim text-[10px] mt-1">{formatTime(req.timestamp)}</div>
            </div>
          ))
        )}
      </div>

      {/* Desktop: table layout */}
      <div className="flex-1 overflow-auto bg-alien-panel border border-alien-border rounded-lg hidden sm:block">
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
              <tr><td colSpan={8} className="text-center py-8 text-alien-text-dim">Loading...</td></tr>
            ) : requests.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-8 text-alien-text-dim">No requests captured.</td></tr>
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
          <span className="text-alien-text-dim text-[10px] sm:text-xs">
            {page + 1}/{totalPages} ({data?.total})
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

      {selectedId !== null && (
        <RequestInspector requestId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  );
}
