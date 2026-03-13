import { useStats } from '../hooks/useApi';
import { useWebSocket } from '../hooks/useWebSocket';
import { MethodBadge, StatusBadge } from '../components/StatusBadge';

function StatCard({ label, value, accent = 'green' }: { label: string; value: string | number; accent?: string }) {
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
    <div className={`bg-alien-panel border ${borderMap[accent]} rounded-lg p-3 sm:p-5 animate-glow-pulse`}>
      <div className="text-alien-text-dim text-[9px] sm:text-[10px] uppercase tracking-[0.15em] sm:tracking-[0.2em] mb-1 sm:mb-2">{label}</div>
      <div className={`${textMap[accent]} text-xl sm:text-3xl font-bold glow-text`}>{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const { data: stats, loading } = useStats();
  const { connected } = useWebSocket();

  const mockStats = {
    total_requests: 0,
    unique_hosts: 0,
    vulnerabilities_found: 0,
    active_connections: connected ? 1 : 0,
    method_distribution: {} as Record<string, number>,
    recent_requests: [],
  };

  const s = stats || mockStats;

  const methodEntries = Object.entries(s.method_distribution);
  const maxMethodCount = Math.max(...methodEntries.map(([, v]) => v), 1);

  return (
    <div className="space-y-4 sm:space-y-6 animate-slide-in">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4">
        <StatCard label="Total Requests" value={s.total_requests} accent="green" />
        <StatCard label="Unique Hosts" value={s.unique_hosts} accent="cyan" />
        <StatCard label="Vulnerabilities" value={s.vulnerabilities_found} accent="red" />
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
                    <div
                      className="h-full bg-gradient-to-r from-alien-green/80 to-alien-cyan/60 rounded-full transition-all duration-500"
                      style={{ width: `${(count / maxMethodCount) * 100}%` }}
                    />
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
            <div className="text-alien-text-dim text-xs">
              No intercepted requests yet. Configure your proxy to capture traffic.
            </div>
          ) : (
            <div className="space-y-1 overflow-x-auto">
              {/* Mobile: card layout */}
              <div className="sm:hidden space-y-2">
                {s.recent_requests.slice(0, 10).map((req) => (
                  <div key={req.id} className="bg-alien-black/50 rounded p-2 border border-alien-border/30">
                    <div className="flex items-center gap-2 mb-1">
                      <MethodBadge method={req.method} />
                      <StatusBadge code={req.status_code} />
                      <span className="text-alien-text-dim text-[10px] ml-auto">{req.response_time}ms</span>
                    </div>
                    <div className="text-alien-text text-[11px] truncate">{req.host}{req.path}</div>
                  </div>
                ))}
              </div>
              {/* Desktop: table layout */}
              <div className="hidden sm:block">
                <div className="grid grid-cols-[60px_1fr_80px_60px_100px] gap-2 text-[10px] text-alien-text-dim uppercase tracking-wider pb-2 border-b border-alien-border">
                  <span>Method</span>
                  <span>URL</span>
                  <span>Host</span>
                  <span>Status</span>
                  <span>Time</span>
                </div>
                {s.recent_requests.slice(0, 10).map((req) => (
                  <div
                    key={req.id}
                    className="grid grid-cols-[60px_1fr_80px_60px_100px] gap-2 py-1.5 text-xs border-b border-alien-border/30 hover:bg-alien-green/5 transition-colors"
                  >
                    <MethodBadge method={req.method} />
                    <span className="text-alien-text truncate">{req.path}</span>
                    <span className="text-alien-text-dim truncate">{req.host}</span>
                    <StatusBadge code={req.status_code} />
                    <span className="text-alien-text-dim">{req.response_time}ms</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ASCII art divider — hidden on mobile */}
      <div className="hidden sm:block text-center text-alien-green/20 text-[8px] select-none py-2">
        {'='.repeat(80)}<br />
        {'// INTERCEPT37 :: ALIEN INTERCEPTOR :: PROXY ACTIVE //'}<br />
        {'='.repeat(80)}
      </div>
    </div>
  );
}
