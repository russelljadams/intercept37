import { useState } from 'react';
import { useRequestDetail } from '../hooks/useApi';
import { repeatRequest, tagRequest, noteRequest } from '../api/client';
import { MethodBadge, StatusBadge } from './StatusBadge';

interface Props {
  requestId: number;
  onClose: () => void;
}

export default function RequestInspector({ requestId, onClose }: Props) {
  const { data: req, loading, error } = useRequestDetail(requestId);
  const [tab, setTab] = useState<'request' | 'response'>('request');
  const [repeating, setRepeating] = useState(false);
  const [tagInput, setTagInput] = useState('');
  const [noteInput, setNoteInput] = useState('');
  const [message, setMessage] = useState('');

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
        <div className="text-alien-green animate-flicker">Loading...</div>
      </div>
    );
  }

  if (error || !req) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
        <div className="bg-alien-panel border border-alien-red/40 rounded p-6">
          <p className="text-alien-red">{error || 'Not found'}</p>
          <button onClick={onClose} className="mt-4 text-alien-text-dim hover:text-alien-green text-xs">Close</button>
        </div>
      </div>
    );
  }

  const handleRepeat = async () => {
    setRepeating(true);
    try {
      await repeatRequest(req.id);
      setMessage('Request repeated');
    } catch {
      setMessage('Repeat failed');
    }
    setRepeating(false);
    setTimeout(() => setMessage(''), 2000);
  };

  const handleTag = async () => {
    if (!tagInput.trim()) return;
    try {
      await tagRequest(req.id, tagInput.split(',').map(t => t.trim()));
      setMessage('Tags saved');
      setTagInput('');
    } catch {
      setMessage('Tag failed');
    }
    setTimeout(() => setMessage(''), 2000);
  };

  const handleNote = async () => {
    if (!noteInput.trim()) return;
    try {
      await noteRequest(req.id, noteInput);
      setMessage('Note saved');
      setNoteInput('');
    } catch {
      setMessage('Note failed');
    }
    setTimeout(() => setMessage(''), 2000);
  };

  const formatHeaders = (headers: Record<string, string>) =>
    Object.entries(headers || {}).map(([k, v]) => `${k}: ${v}`).join('\n');

  const formatBody = (body: string) => {
    if (!body) return '(empty)';
    try { return JSON.stringify(JSON.parse(body), null, 2); } catch { return body; }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-alien-dark border border-alien-border rounded-t-lg sm:rounded-lg w-full sm:w-[900px] max-h-[90vh] sm:max-h-[85vh] flex flex-col animate-slide-in glow-border"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-3 sm:p-4 border-b border-alien-border">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
            <MethodBadge method={req.method} />
            <span className="text-alien-text text-xs sm:text-sm truncate">{req.url}</span>
            <StatusBadge code={req.status_code} />
          </div>
          <button
            onClick={onClose}
            className="text-alien-text-dim hover:text-alien-red text-lg font-bold w-8 h-8 flex items-center justify-center flex-shrink-0 ml-2"
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-alien-border">
          {(['request', 'response'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 sm:flex-none px-4 sm:px-6 py-2 text-xs uppercase tracking-wider border-b-2 transition-colors ${
                tab === t
                  ? 'border-alien-green text-alien-green'
                  : 'border-transparent text-alien-text-dim hover:text-alien-text'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
          {tab === 'request' ? (
            <>
              <div>
                <h3 className="text-alien-green text-xs uppercase tracking-wider mb-2">URL</h3>
                <div className="bg-alien-black rounded p-2 sm:p-3 text-xs sm:text-sm text-alien-text border border-alien-border break-all">
                  {req.method} {req.url}
                </div>
              </div>
              <div>
                <h3 className="text-alien-green text-xs uppercase tracking-wider mb-2">Headers</h3>
                <pre className="bg-alien-black rounded p-2 sm:p-3 text-[10px] sm:text-xs text-alien-text-dim border border-alien-border whitespace-pre-wrap break-all">
                  {formatHeaders(req.request_headers)}
                </pre>
              </div>
              <div>
                <h3 className="text-alien-green text-xs uppercase tracking-wider mb-2">Body</h3>
                <pre className="bg-alien-black rounded p-2 sm:p-3 text-[10px] sm:text-xs text-alien-cyan border border-alien-border whitespace-pre-wrap max-h-48 sm:max-h-60 overflow-auto break-all">
                  {formatBody(req.request_body)}
                </pre>
              </div>
            </>
          ) : (
            <>
              <div>
                <h3 className="text-alien-green text-xs uppercase tracking-wider mb-2">Status</h3>
                <div className="bg-alien-black rounded p-2 sm:p-3 text-sm border border-alien-border">
                  <StatusBadge code={req.status_code} />
                </div>
              </div>
              <div>
                <h3 className="text-alien-green text-xs uppercase tracking-wider mb-2">Headers</h3>
                <pre className="bg-alien-black rounded p-2 sm:p-3 text-[10px] sm:text-xs text-alien-text-dim border border-alien-border whitespace-pre-wrap break-all">
                  {formatHeaders(req.response_headers)}
                </pre>
              </div>
              <div>
                <h3 className="text-alien-green text-xs uppercase tracking-wider mb-2">Body</h3>
                <pre className="bg-alien-black rounded p-2 sm:p-3 text-[10px] sm:text-xs text-alien-cyan border border-alien-border whitespace-pre-wrap max-h-48 sm:max-h-60 overflow-auto break-all">
                  {formatBody(req.response_body)}
                </pre>
              </div>
            </>
          )}
        </div>

        {/* Actions */}
        <div className="p-3 sm:p-4 border-t border-alien-border space-y-2 sm:space-y-3">
          {message && <div className="text-alien-green text-xs animate-flicker">{message}</div>}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
            <button
              onClick={handleRepeat}
              disabled={repeating}
              className="px-4 py-1.5 bg-alien-green/10 border border-alien-green/40 text-alien-green text-xs rounded hover:bg-alien-green/20 transition-colors disabled:opacity-50"
            >
              {repeating ? 'Sending...' : 'Repeat Request'}
            </button>
            <div className="flex items-center gap-2 flex-1">
              <input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                placeholder="tag1, tag2"
                className="flex-1 bg-alien-black border border-alien-border rounded px-3 py-1.5 text-xs text-alien-text placeholder:text-alien-text-dim/50 focus:border-alien-green/50 focus:outline-none"
              />
              <button onClick={handleTag} className="px-3 py-1.5 text-xs text-alien-cyan border border-alien-cyan/30 rounded hover:bg-alien-cyan/10">
                Tag
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              value={noteInput}
              onChange={(e) => setNoteInput(e.target.value)}
              placeholder="Add a note..."
              className="flex-1 bg-alien-black border border-alien-border rounded px-3 py-1.5 text-xs text-alien-text placeholder:text-alien-text-dim/50 focus:border-alien-green/50 focus:outline-none"
            />
            <button onClick={handleNote} className="px-3 py-1.5 text-xs text-alien-yellow border border-alien-yellow/30 rounded hover:bg-alien-yellow/10">
              Note
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
