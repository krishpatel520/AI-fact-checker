/** CredibilityRing.jsx — circular SVG score gauge */
export function CredibilityRing({ score }) {
    const r      = 44
    const circ   = 2 * Math.PI * r
    const offset = circ - (score / 100) * circ
    const color  = score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444'
    const label  = score >= 70 ? 'High'    : score >= 40 ? 'Moderate' : 'Low'
    return (
        <div className="flex flex-col items-center">
            <svg width="110" height="110" viewBox="0 0 110 110" className="ring-svg">
                <circle cx="55" cy="55" r={r} className="ring-bg" />
                <circle cx="55" cy="55" r={r} className="ring-fill"
                    stroke={color} strokeDasharray={circ} strokeDashoffset={offset} />
            </svg>
            <div style={{ marginTop: -80, marginBottom: 30 }} className="text-center pointer-events-none">
                <div className="text-3xl font-black" style={{ color }}>{score}</div>
                <div className="text-xs font-semibold secondary">{label} Credibility</div>
            </div>
        </div>
    )
}
