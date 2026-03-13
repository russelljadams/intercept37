import { useState, useEffect, useCallback } from 'react';
import { useStats, useScanResults, useRequests } from '../hooks/useApi';
import { useWebSocket } from '../hooks/useWebSocket';
import { MethodBadge, StatusBadge, SeverityBadge } from '../components/StatusBadge';
import RequestInspector from '../components/RequestInspector';
import api from '../api/client';

// ── Drill-down Modal Shell ──────────────────────────────────────────

function DrillDown({ title, accent, onClose, children }: {
  title: string; accent: string; onClose: () => void; children: React.ReactNode;
}) {
  const borderMap: Record<string, string> = {
    green: 'border-alien-green/40', cyan: 'border-alien-cyan/40',
    red: 'border-alien-red/40', yellow: 'border-alien-yellow/40',
  };
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className={`bg-alien-dark border ${borderMap[accent]} rounded-t-lg sm:rounded-lg w-full sm:w-[700px] lg:w-[850px] max-h-[90vh] sm:max-h-[80vh] flex flex-col animate-slide-in`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-3 sm:p-4 border-b border-alien-border">
          <h2 className={`text-alien-${accent} text-sm font-bold uppercase tracking-wider`}>{title}</h2>
          <button onClick={onClose} className="text-alien-text-dim hover:text-alien-red text-lg font-bold w-8 h-8 flex items-center justify-center">x</button>
        </div>
        <div className="flex-1 overflow-auto p-3 sm:p-4">{children}</div>
      </div>
    </div>
  );
}

// ── Requests Drill-down ─────────────────────────────────────────────

function RequestsDrillDown({ onClose }: { onClose: () => void }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data, loading } = useRequests({ limit: 100 });
  const requests = data?.data || [];

  return (
    <DrillDown title={`All Requests (${data?.total || 0})`} accent="green" onClose={onClose}>
      {selectedId !== null && <RequestInspector requestId={selectedId} onClose={() => setSelectedId(null)} />}
      {loading ? <div className="text-alien-text-dim text-xs text-center py-8">Loading...</div> : (
        <div className="space-y-1.5">
          {requests.map((req) => (
            <div key={req.id} onClick={() => setSelectedId(req.id)}
              className="flex items-center gap-2 sm:gap-3 p-2 sm:p-3 rounded-lg bg-alien-panel border border-alien-border/40 hover:border-alien-green/30 cursor-pointer transition-colors">
              <span className="text-alien-text-dim text-[10px] w-8 text-right">#{req.id}</span>
              <MethodBadge method={req.method} />
              <div className="flex-1 min-w-0">
                <div className="text-alien-text text-xs truncate">{req.host}{req.path}</div>
              </div>
              <StatusBadge code={req.status_code} />
              <span className="text-alien-text-dim text-[10px]">{req.response_time}ms</span>
            </div>
          ))}
        </div>
      )}
    </DrillDown>
  );
}

// ── Hosts Drill-down ────────────────────────────────────────────────

function HostsDrillDown({ onClose }: { onClose: () => void }) {
  const [hosts, setHosts] = useState<{ host: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedHost, setExpandedHost] = useState<string | null>(null);
  const [hostRequests, setHostRequests] = useState<Record<string, unknown[]>>({});

  useEffect(() => {
    // Fetch all requests and group by host
    api.get('/requests?limit=500').then(({ data }) => {
      const map: Record<string, number> = {};
      for (const r of (data.data || data.requests || [])) {
        map[r.host] = (map[r.host] || 0) + 1;
      }
      const sorted = Object.entries(map).map(([host, count]) => ({ host, count })).sort((a, b) => b.count - a.count);
      setHosts(sorted);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const toggleHost = useCallback((host: string) => {
    if (expandedHost === host) { setExpandedHost(null); return; }
    setExpandedHost(host);
    if (!hostRequests[host]) {
      api.get(`/requests?host=${host}&limit=20`).then(({ data }) => {
        setHostRequests((prev) => ({ ...prev, [host]: data.data || data.requests || [] }));
      });
    }
  }, [expandedHost, hostRequests]);

  return (
    <DrillDown title={`Unique Hosts (${hosts.length})`} accent="cyan" onClose={onClose}>
      {loading ? <div className="text-alien-text-dim text-xs text-center py-8">Loading...</div> : (
        <div className="space-y-2">
          {hosts.map(({ host, count }) => (
            <div key={host} className="bg-alien-panel border border-alien-border/40 rounded-lg overflow-hidden">
              <div onClick={() => toggleHost(host)}
                className="flex items-center gap-3 p-3 cursor-pointer hover:bg-alien-cyan/5 transition-colors">
                <span className={`text-alien-text-dim text-xs transition-transform ${expandedHost === host ? 'rotate-90' : ''}`}>&gt;</span>
                <span className="text-alien-cyan text-xs font-mono flex-1">{host}</span>
                <span className="text-alien-text-dim text-[10px] bg-alien-cyan/10 border border-alien-cyan/20 rounded px-2 py-0.5">{count} requests</span>
              </div>
              {expandedHost === host && (
                <div className="border-t border-alien-border p-3 space-y-1">
                  {(hostRequests[host] || []).map((r: any) => (
                    <div key={r.id} className="flex items-center gap-2 text-xs py-1">
                      <MethodBadge method={r.method} />
                      <span className="text-alien-text truncate flex-1">{r.path}</span>
                      <StatusBadge code={r.status_code} />
                    </div>
                  ))}
                  {!hostRequests[host] && <div className="text-alien-text-dim text-xs">Loading...</div>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </DrillDown>
  );
}

// ── Vulnerabilities Drill-down ──────────────────────────────────────

function VulnsDrillDown({ onClose }: { onClose: () => void }) {
  const [severity, setSeverity] = useState('');
  const [expandedTitle, setExpandedTitle] = useState<string | null>(null);
  const { data: results, loading } = useScanResults(severity || undefined);

  // Group by title to deduplicate
  interface VulnGroup { title: string; severity: string; description: string; evidence: string; count: number; request_ids: number[]; instances: typeof results; }
  const grouped: VulnGroup[] = [];
  const seen = new Map<string, VulnGroup>();
  for (const r of results) {
    const key = r.title;
    if (seen.has(key)) {
      const g = seen.get(key)!;
      g.count++;
      if (!g.request_ids.includes(r.request_id)) g.request_ids.push(r.request_id);
      g.instances.push(r);
    } else {
      const g: VulnGroup = { title: r.title, severity: r.severity, description: r.description, evidence: r.evidence, count: 1, request_ids: [r.request_id], instances: [r] };
      seen.set(key, g);
      grouped.push(g);
    }
  }

  const severityCounts = grouped.reduce((acc, g) => {
    acc[g.severity] = (acc[g.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <DrillDown title={`Vulnerabilities (${grouped.length} unique, ${results.length} total)`} accent="red" onClose={onClose}>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <button onClick={() => setSeverity('')}
          className={`px-2 py-1 rounded text-[10px] uppercase tracking-wider border transition-colors ${
            !severity ? 'border-alien-red/50 text-alien-red bg-alien-red/10' : 'border-alien-border text-alien-text-dim hover:text-alien-text'
          }`}>All ({grouped.length})</button>
        {['critical', 'high', 'medium', 'low', 'info'].map((s) => (
          <button key={s} onClick={() => setSeverity(severity === s ? '' : s)}
            className={`transition-all flex items-center gap-1 ${severity === s ? 'scale-110' : 'opacity-70 hover:opacity-100'}`}>
            <SeverityBadge severity={s} />
            <span className="text-alien-text-dim text-[10px]">{severityCounts[s] || 0}</span>
          </button>
        ))}
      </div>

      {loading ? <div className="text-alien-text-dim text-xs text-center py-8">Loading...</div> : grouped.length === 0 ? (
        <div className="text-alien-text-dim text-xs text-center py-8">No vulnerabilities{severity ? ` with severity: ${severity}` : ''}.</div>
      ) : (
        <div className="space-y-2">
          {grouped.map((group) => {
            const isExpanded = expandedTitle === group.title;
            return (
              <div key={group.title}
                className={`bg-alien-panel border rounded-lg transition-all cursor-pointer ${
                  isExpanded ? 'border-alien-red/30' : 'border-alien-border/40 hover:border-alien-red/20'
                }`}>
                <div className="flex items-center gap-2 sm:gap-3 p-3" onClick={() => setExpandedTitle(isExpanded ? null : group.title)}>
                  <SeverityBadge severity={group.severity} />
                  <div className="flex-1 min-w-0">
                    <div className="text-alien-text text-xs font-medium">{group.title}</div>
                    {group.count > 1 && (
                      <div className="text-alien-text-dim text-[10px] mt-0.5">Affects {group.count} requests across {group.request_ids.length} endpoints</div>
                    )}
                  </div>
                  {group.count > 1 && (
                    <span className="text-alien-red/80 text-[10px] bg-alien-red/10 border border-alien-red/20 rounded px-1.5 py-0.5">{group.count}x</span>
                  )}
                  <span className={`text-alien-text-dim text-xs transition-transform ${isExpanded ? 'rotate-90' : ''}`}>&gt;</span>
                </div>
                {isExpanded && (
                  <div className="border-t border-alien-border p-3 space-y-3 animate-slide-in">
                    <div>
                      <h4 className="text-alien-red text-[10px] uppercase tracking-wider mb-1">Description</h4>
                      <p className="text-alien-text text-xs leading-relaxed">{group.description}</p>
                    </div>
                    {group.evidence && (
                      <div>
                        <h4 className="text-alien-red text-[10px] uppercase tracking-wider mb-1">Evidence</h4>
                        <pre className="bg-alien-black border border-alien-border rounded p-2 text-[10px] text-alien-cyan whitespace-pre-wrap break-all overflow-auto max-h-40">{group.evidence}</pre>
                      </div>
                    )}
                    {group.count > 1 && (
                      <div>
                        <h4 className="text-alien-red text-[10px] uppercase tracking-wider mb-1">Affected Requests ({group.count})</h4>
                        <div className="flex flex-wrap gap-1.5">
                          {group.request_ids.map((rid) => (
                            <span key={rid} className="text-[10px] text-alien-text bg-alien-black border border-alien-border rounded px-1.5 py-0.5">#{rid}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </DrillDown>
  );
}

// ── Stat Card (now clickable) ───────────────────────────────────────

function StatCard({ label, value, accent = 'green', onClick }: {
  label: string; value: string | number; accent?: string; onClick?: () => void;
}) {
  const borderMap: Record<string, string> = {
    green: 'border-alien-green/30 shadow-alien',
    cyan: 'border-alien-cyan/30 shadow-cyan',
    red: 'border-alien-red/30 shadow-red',
    yellow: 'border-alien-yellow/30',
  };
  const textMap: Record<string, string> = {
    green: 'text-alien-green',
    cyan: 'text-alien-cyan',
    red: 'text-alien-red',
    yellow: 'text-alien-yellow',
  };
  return (
    <div
      onClick={onClick}
      className={`bg-alien-panel border ${borderMap[accent]} rounded-lg p-3 sm:p-5 animate-glow-pulse ${
        onClick ? 'cursor-pointer hover:bg-alien-green/5 active:scale-[0.98] transition-all' : ''
      }`}
    >
      <div className="text-alien-text-dim text-[9px] sm:text-[10px] uppercase tracking-[0.15em] sm:tracking-[0.2em] mb-1 sm:mb-2">{label}</div>
      <div className={`${textMap[accent]} text-xl sm:text-3xl font-bold glow-text`}>{value}</div>
      {onClick && <div className="text-alien-text-dim text-[8px] mt-1 uppercase tracking-wider">Tap to view</div>}
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────────────────────

export default function Dashboard() {
  const { data: stats, loading } = useStats();
  const { connected } = useWebSocket();
  const [drillDown, setDrillDown] = useState<'requests' | 'hosts' | 'vulns' | null>(null);

  const s = stats || {
    total_requests: 0, unique_hosts: 0, vulnerabilities_found: 0,
    active_connections: connected ? 1 : 0,
    method_distribution: {} as Record<string, number>, recent_requests: [],
  };

  const methodEntries = Object.entries(s.method_distribution);
  const maxMethodCount = Math.max(...methodEntries.map(([, v]) => v), 1);

  return (
    <div className="space-y-4 sm:space-y-6 animate-slide-in">
      {/* Drill-down modals */}
      {drillDown === 'requests' && <RequestsDrillDown onClose={() => setDrillDown(null)} />}
      {drillDown === 'hosts' && <HostsDrillDown onClose={() => setDrillDown(null)} />}
      {drillDown === 'vulns' && <VulnsDrillDown onClose={() => setDrillDown(null)} />}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4">
        <StatCard label="Total Requests" value={s.total_requests} accent="green" onClick={() => setDrillDown('requests')} />
        <StatCard label="Unique Hosts" value={s.unique_hosts} accent="cyan" onClick={() => setDrillDown('hosts')} />
        <StatCard label="Vulnerabilities" value={s.vulnerabilities_found} accent="red" onClick={() => setDrillDown('vulns')} />
        <StatCard label="Connections" value={s.active_connections} accent="yellow" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 sm:gap-4">
        {/* Method Distribution */}
        <div className="bg-alien-panel border border-alien-border rounded-lg p-3 sm:p-5">
          <h3 className="text-alien-green text-xs uppercase tracking-[0.15em] mb-3 sm:mb-4">Method Distribution</h3>
          {loading && !stats ? (
            <div className="text-alien-text-dim text-xs">Loading...</div>
          ) : methodEntries.length === 0 ? (
            <div className="text-alien-text-dim text-xs">No data yet</div>
          ) : (
            <div className="space-y-3">
              {methodEntries.map(([method, count]) => (
                <div key={method} className="flex items-center gap-3">
                  <MethodBadge method={method} />
                  <div className="flex-1 h-2 bg-alien-black rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-alien-green/80 to-alien-cyan/60 rounded-full transition-all duration-500"
                      style={{ width: `${(count / maxMethodCount) * 100}%` }} />
                  </div>
                  <span className="text-alien-text-dim text-xs w-8 text-right">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Requests */}
        <div className="lg:col-span-2 bg-alien-panel border border-alien-border rounded-lg p-3 sm:p-5">
          <h3 className="text-alien-green text-xs uppercase tracking-[0.15em] mb-3 sm:mb-4">Recent Requests</h3>
          {loading && !stats ? (
            <div className="text-alien-text-dim text-xs">Loading...</div>
          ) : s.recent_requests.length === 0 ? (
            <div className="text-alien-text-dim text-xs">No intercepted requests yet.</div>
          ) : (
            <div className="space-y-1.5">
              {s.recent_requests.slice(0, 10).map((req) => (
                <div key={req.id} className="flex items-center gap-2 py-1.5 text-xs border-b border-alien-border/20 hover:bg-alien-green/5 transition-colors">
                  <MethodBadge method={req.method} />
                  <span className="text-alien-text truncate flex-1">{req.host}{req.path}</span>
                  <StatusBadge code={req.status_code} />
                  <span className="text-alien-text-dim text-[10px]">{req.response_time}ms</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
