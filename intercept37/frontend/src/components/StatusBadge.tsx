interface StatusBadgeProps {
  code: number;
}

export function StatusBadge({ code }: StatusBadgeProps) {
  let color = 'text-alien-text-dim';
  if (code >= 200 && code < 300) color = 'text-alien-green';
  else if (code >= 300 && code < 400) color = 'text-alien-cyan';
  else if (code >= 400 && code < 500) color = 'text-alien-orange';
  else if (code >= 500) color = 'text-alien-red';

  return (
    <span className={`${color} font-bold text-xs`}>
      {code}
    </span>
  );
}

export function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: 'text-alien-green bg-alien-green/10 border-alien-green/30',
    POST: 'text-alien-cyan bg-alien-cyan/10 border-alien-cyan/30',
    PUT: 'text-alien-orange bg-alien-orange/10 border-alien-orange/30',
    DELETE: 'text-alien-red bg-alien-red/10 border-alien-red/30',
    PATCH: 'text-alien-yellow bg-alien-yellow/10 border-alien-yellow/30',
    OPTIONS: 'text-alien-text-dim bg-alien-gray/10 border-alien-gray/30',
    HEAD: 'text-alien-blue bg-alien-blue/10 border-alien-blue/30',
  };

  const cls = colors[method.toUpperCase()] || 'text-alien-text bg-alien-panel border-alien-border';

  return (
    <span className={`${cls} border rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wider`}>
      {method.toUpperCase()}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'text-alien-red bg-alien-red/10 border-alien-red/40',
    high: 'text-alien-orange bg-alien-orange/10 border-alien-orange/40',
    medium: 'text-alien-yellow bg-alien-yellow/10 border-alien-yellow/40',
    low: 'text-alien-blue bg-alien-blue/10 border-alien-blue/40',
    info: 'text-alien-gray bg-alien-gray/10 border-alien-gray/40',
  };

  const cls = colors[severity] || colors.info;

  return (
    <span className={`${cls} border rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider`}>
      {severity}
    </span>
  );
}
