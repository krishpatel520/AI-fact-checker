/** SpectrumBar.jsx — Ground News-style political spectrum visualiser */
import { BIAS_CONFIG } from './ui/Badge.jsx'

export function SpectrumBar({ outlets }) {
    const rated = outlets.filter(o => o.political_leaning_score != null)
    return (
        <div className="px-1 py-2">
            <div className="flex justify-between text-xs muted mb-1.5 px-1">
                <span>◀ Left</span><span>Center</span><span>Right ▶</span>
            </div>
            <div className="spectrum-bar">
                {rated.map((o, i) => {
                    const pct = ((o.political_leaning_score + 1) / 2) * 100
                    const cfg = BIAS_CONFIG[o.bias] || BIAS_CONFIG['Not Rated']
                    return (
                        <div key={i} title={`${o.domain} — ${o.bias}`}
                            className="absolute -translate-x-1/2 -translate-y-1/2 top-1/2 cursor-pointer"
                            style={{ left: `${pct}%` }}>
                            <img src={o.logo_url} alt={o.domain}
                                className="w-5 h-5 rounded-full border-2 object-cover bg-slate-800"
                                style={{ borderColor: cfg.color }}
                                onError={e => { e.target.style.display = 'none' }} />
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
