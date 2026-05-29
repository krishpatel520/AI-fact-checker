/**
 * EvidenceItem.jsx
 * ----------------
 * Renders a single piece of evidence for a claim.
 * The v3 backend always returns Ollama-style evidence objects
 * {confidence, verdict, reason, method}, so we render that unconditionally.
 */

/** Ollama LLM evidence card — verdict, reason, confidence bar */
export function EvidenceItem({ ev }) {
    const verdictColor = {
        supported:       '#22c55e',
        refuted:         '#ef4444',
        not_enough_info: '#94a3b8',
    }
    const color = verdictColor[ev.verdict] || '#94a3b8'
    const pct   = Math.round((ev.confidence || 0) * 100)
    return (
        <div className="surface rounded-lg p-3 space-y-1.5">
            <div className="flex items-start justify-between gap-2">
                <a href={ev.url} target="_blank" rel="noopener noreferrer"
                    aria-label={`Open source: ${ev.title || 'Source'}`}
                    className="text-sm font-semibold text-indigo-400 hover:underline line-clamp-1 flex-1">
                    {ev.title || 'Source'}
                </a>
                <span className="text-xs font-bold px-2 py-0.5 rounded-full shrink-0"
                    style={{ background: color + '22', color, border: `1px solid ${color}44` }}>
                    {ev.verdict?.replace(/_/g, ' ') || 'unknown'}
                </span>
            </div>

            {ev.reason && (
                <p className="text-xs muted italic leading-snug">"{ev.reason}"</p>
            )}

            <div className="flex items-center gap-2">
                <div className="flex-1 rounded-full" style={{ background: '#33415544', height: 5 }}>
                    <div style={{ width: `${pct}%`, background: color, height: 5, borderRadius: 9999 }} />
                </div>
                <span className="text-xs muted text-right whitespace-nowrap">
                    {pct}% {ev.method === 'heuristic' ? '(heuristic)' : '(LLM)'}
                </span>
            </div>
        </div>
    )
}
