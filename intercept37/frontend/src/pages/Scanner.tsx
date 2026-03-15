import { useState } from 'react';
import { useScanResults } from '../hooks/useApi';
import { SeverityBadge } from '../components/StatusBadge';

const SEVERITIES = ['', 'critical', 'high', 'medium', 'low', 'info'];

export default function Scanner() {
  const [severity, setSeverity] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const { data: results, loading } = useScanResults(severity || undefined);

  const severityCounts = results.reduce(
    (acc, r) => {
      acc[r.severity] = (acc[r.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-4 animate-slide-in">
      {/* Header with severity summary */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-alien-green text-sm uppercase tracking-[0.15em]">Scan Results</h2>
          <div className="flex items-center gap-2">
            {['critical', 'high', 'medium', 'low', 'info'].map((s) => (
              <button
                key={s}
                onClick={() => setSeverity(severity === s ? '' : s)}
                className={`transition-all ${severity === s ? 'scale-110' : 'opacity-60 hover:opacity-100'}`}
              >
                <SeverityBadge severity={s} />
                {severityCounts[s] ? (
                  <span className="ml-1 text-alien-text-dim text-[10px]">{severityCounts[s]}</span>
                ) : null}
              </button>
            ))}
          </div>
        </div>

        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="bg-alien-black border border-alien-border rounded px-3 py-1.5 text-xs text-alien-text focus:border-alien-green/50 focus:outline-none"
        >
          <option value="">All Severities</option>
          {SEVERITIES.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
      </div>

      {/* Results List */}
      <div className="space-y-2">
        {loading ? (
          <div className="text-alien-text-dim text-xs text-center py-12">Scanning...</div>
        ) : results.length === 0 ? (
          <div className="bg-alien-panel border border-alien-border rounded-lg p-8 text-center">
            <div className="text-alien-text-dim text-xs">
              No vulnerabilities found{severity ? ` with severity: ${severity}` : ''}. Run a scan to populate results.
            </div>
          </div>
        ) : (
          results.map((result) => {
            const isExpanded = expandedId === result.id;
            return (
              <div
                key={result.id}
                className={`bg-alien-panel border rounded-lg transition-all cursor-pointer ${
                  isExpanded ? 'border-alien-green/40 glow-border' : 'border-alien-border hover:border-alien-green/20'
                }`}
              >
                <div
                  className="flex items-center gap-4 p-4"
                  onClick={() => setExpandedId(isExpanded ? null : result.id)}
                >
                  <SeverityBadge severity={result.severity} />
                  <div className="flex-1 min-w-0">
                    <div className="text-alien-text text-sm font-medium">{result.title}</div>
                    <div className="text-alien-text-dim text-xs truncate">{result.url}</div>
                  </div>
                  {result.parameter && (
                    <span className="text-alien-cyan text-xs bg-alien-cyan/10 border border-alien-cyan/20 rounded px-2 py-0.5">
                      {result.parameter}
                    </span>
                  )}
                  <span className="text-alien-text-dim text-[10px]">
                    {new Date(result.timestamp).toLocaleDateString()}
                  </span>
                  <span className={`text-alien-text-dim text-xs transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                    &gt;
                  </span>
                </div>

                {isExpanded && (
                  <div className="border-t border-alien-border p-4 space-y-3 animate-slide-in">
                    <div>
                      <h4 className="text-alien-green text-[10px] uppercase tracking-wider mb-1">Description</h4>
                      <p className="text-alien-text text-xs leading-relaxed">{result.description}</p>
                    </div>
                    {result.evidence && (
                      <div>
                        <h4 className="text-alien-green text-[10px] uppercase tracking-wider mb-1">Evidence</h4>
                        <pre className="bg-alien-black border border-alien-border rounded p-3 text-xs text-alien-cyan whitespace-pre-wrap overflow-auto max-h-48">
                          {result.evidence}
                        </pre>
                      </div>
                    )}
                    <div className="flex items-center gap-4 text-[10px] text-alien-text-dim">
                      <span>URL: <span className="text-alien-text">{result.url}</span></span>
                      {result.parameter && (
                        <span>Param: <span className="text-alien-cyan">{result.parameter}</span></span>
                      )}
                      <span>Request ID: <span className="text-alien-text">{result.request_id}</span></span>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
