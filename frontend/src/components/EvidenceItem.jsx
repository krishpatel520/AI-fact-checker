/**
 * EvidenceItem.jsx
 * ----------------
 * Renders a single piece of evidence for a claim.
 * Automatically switches between:
 *   - LLMEvidenceItem  (Ollama results — has confidence + reason fields)
 *   - NLIBars          (legacy heuristic results — has scores object)
 */

/** Legacy heuristic NLI score bars */
function NLIBars({ scores }) {
    if (!scores) return null
    const bars = [
        { label: 'Entails',      value: scores.entailment,   color: '#22c55e' },
        { label: 'Neutral',      value: scores.neutral,      color: '#94a3b8' },
        { label: 'Contradicts',  value: scores.contradiction, color: '#ef4444' },
    ]
    return (
        <div className="mt-2 space-y-1">
            {bars.map(b => (
                <div key={b.label} className="flex items-center gap-2">
                    <span className="text-xs muted w-20 shrink-0">{b.label}</span>
                    <div className="flex-1 rounded-full" style={{ background: '#33415544', height: 6 }}>
                        <div className="nli-bar"
                            style={{ width: `${(b.value || 0) * 100}%`, background: b.color }} />
                    </div>
                    <span className="text-xs muted w-8 text-right">
                        {((b.value || 0) * 100).toFixed(0)}%
                    </span>
                </div>
            ))}
        </div>
    )
}

/** Ollama LLM evidence card — verdict, reason, confidence bar */
function LLMEvidenceItem({ ev }) {
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

/** Smart dispatcher: picks the right card based on evidence shape */
export function EvidenceItem({ ev, index }) {
    return ev.confidence != null
        ? <LLMEvidenceItem key={index} ev={ev} />
        : (
            <div key={index} className="surface rounded-lg p-3">
                <a href={ev.url} target="_blank" rel="noopener noreferrer"
                    className="text-sm font-semibold text-indigo-400 hover:underline line-clamp-1">
                    {ev.title || 'Source'}
                </a>
                <NLIBars scores={ev.scores} />
            </div>
        )
}
