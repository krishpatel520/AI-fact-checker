import { useState, useEffect, useRef } from 'react'

// API base URL — set VITE_API_BASE_URL in .env for non-localhost deployments.
// In dev mode the Vite proxy (vite.config.js) handles /api → localhost:8000 automatically.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

// ─────────────────────────────────────────────
//  CONSTANTS
// ─────────────────────────────────────────────

const BIAS_CONFIG = {
    'Left': { color: '#3b82f6', score: -1.0 },
    'Lean Left': { color: '#60a5fa', score: -0.5 },
    'Center': { color: '#94a3b8', score: 0.0 },
    'Center-Right': { color: '#fb923c', score: 0.4 },
    'Lean Right': { color: '#f97316', score: 0.5 },
    'Right': { color: '#ef4444', score: 1.0 },
    'Not Rated': { color: '#64748b', score: null },
    'N/A': { color: '#64748b', score: null },
}

const FACTUALITY_COLOR = {
    'Very High': '#22c55e',
    'High': '#86efac',
    'Mostly Factual': '#fbbf24',
    'Mixed': '#f97316',
    'Low': '#ef4444',
    'Very Low': '#b91c1c',
    'Not Rated': '#64748b',
    'N/A': '#64748b',
}

const LOADING_STEPS = [
    'Fetching article content…',
    'Extracting factual claims…',
    'Searching trusted sources…',
    'Analyzing media bias…',
    'Finding related coverage…',
    'Building your report…',
]

// ─────────────────────────────────────────────
//  SMALL REUSABLE COMPONENTS
// ─────────────────────────────────────────────

function BiasBadge({ bias, small }) {
    const cfg = BIAS_CONFIG[bias] || BIAS_CONFIG['Not Rated']
    const cls = small ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-xs font-semibold'
    return (
        <span className={`${cls} rounded-full font-semibold inline-flex items-center`}
            style={{ background: cfg.color + '22', color: cfg.color, border: `1px solid ${cfg.color}55` }}>
            {bias || 'Not Rated'}
        </span>
    )
}

function FactualityBadge({ rating }) {
    const color = FACTUALITY_COLOR[rating] || '#64748b'
    return (
        <span className="px-2 py-0.5 text-xs rounded-full font-medium"
            style={{ background: color + '1a', color, border: `1px solid ${color}44` }}>
            {rating || 'Not Rated'}
        </span>
    )
}

function VerdictBadge({ verdict }) {
    const map = {
        supported: { bg: '#22c55e22', text: '#4ade80', border: '#22c55e44', label: 'Supported' },
        refuted: { bg: '#ef444422', text: '#f87171', border: '#ef444444', label: 'Refuted' },
        not_enough_info: { bg: '#64748b22', text: '#94a3b8', border: '#64748b44', label: 'Not Enough Info' },
    }
    const s = map[verdict] || map.not_enough_info
    return (
        <span className="px-3 py-1 text-xs font-bold rounded-full whitespace-nowrap"
            style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}>
            {s.label}
        </span>
    )
}

function DocStatusBadge({ status }) {
    const map = {
        clean_document: { bg: '#22c55e22', text: '#4ade80', border: '#22c55e44', icon: '✓', label: 'Clean Document' },
        inaccuracies_found: { bg: '#ef444422', text: '#f87171', border: '#ef444444', icon: '⚠', label: 'Inaccuracies Found' },
        not_enough_info: { bg: '#64748b22', text: '#94a3b8', border: '#64748b44', icon: '?', label: 'Not Enough Info' },
    }
    const s = map[status] || map.not_enough_info
    return (
        <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold"
            style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}>
            {s.icon} {s.label}
        </span>
    )
}

function Spinner({ size = 20, color = '#818cf8' }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
            className="spinner" style={{ minWidth: size }}>
            <circle cx="12" cy="12" r="10" stroke={color + '33'} strokeWidth="3" />
            <path d="M12 2 A10 10 0 0 1 22 12" stroke={color} strokeWidth="3" strokeLinecap="round" />
        </svg>
    )
}

function CredibilityRing({ score }) {
    const r = 44
    const circ = 2 * Math.PI * r
    const offset = circ - (score / 100) * circ
    const color = score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444'
    const label = score >= 70 ? 'High' : score >= 40 ? 'Moderate' : 'Low'
    return (
        <div className="flex flex-col items-center">
            <svg width="110" height="110" viewBox="0 0 110 110" className="ring-svg">
                <circle cx="55" cy="55" r={r} className="ring-bg" />
                <circle cx="55" cy="55" r={r} className="ring-fill" stroke={color}
                    strokeDasharray={circ} strokeDashoffset={offset} />
            </svg>
            <div style={{ marginTop: -80, marginBottom: 30 }} className="text-center pointer-events-none">
                <div className="text-3xl font-black" style={{ color }}>{score}</div>
                <div className="text-xs font-semibold secondary">{label} Credibility</div>
            </div>
        </div>
    )
}

function NLIBars({ scores }) {
    if (!scores) return null
    const bars = [
        { label: 'Entails', value: scores.entailment, color: '#22c55e' },
        { label: 'Neutral', value: scores.neutral, color: '#94a3b8' },
        { label: 'Contradicts', value: scores.contradiction, color: '#ef4444' },
    ]
    return (
        <div className="mt-2 space-y-1">
            {bars.map(b => (
                <div key={b.label} className="flex items-center gap-2">
                    <span className="text-xs muted w-20 shrink-0">{b.label}</span>
                    <div className="flex-1 rounded-full" style={{ background: '#33415544', height: 6 }}>
                        <div className="nli-bar" style={{ width: `${(b.value || 0) * 100}%`, background: b.color }} />
                    </div>
                    <span className="text-xs muted w-8 text-right">{((b.value || 0) * 100).toFixed(0)}%</span>
                </div>
            ))}
        </div>
    )
}

function SpectrumBar({ outlets }) {
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

// ─────────────────────────────────────────────
//  HOME PAGE
// ─────────────────────────────────────────────

function HomePage({ onStartAnalysis }) {
    const [tab, setTab] = useState('url')
    const [url, setUrl] = useState('')
    const [file, setFile] = useState(null)
    const [text, setText] = useState('')
    const [drag, setDrag] = useState(false)
    const fileRef = useRef(null)

    const valid =
        (tab === 'url' && url.trim()) ||
        (tab === 'file' && file) ||
        (tab === 'text' && text.trim().length > 50)

    const submit = () => {
        if (!valid) return
        onStartAnalysis({ type: tab, value: tab === 'url' ? url : tab === 'file' ? file : text })
    }

    const Tab = ({ id, icon, label }) => (
        <button onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-semibold rounded-lg transition-all ${tab === id ? 'tab-active' : 'tab-idle'}`}>
            {icon} {label}
        </button>
    )

    return (
        <div className="min-h-screen flex flex-col">
            <header className="text-center pt-16 pb-10 px-6 fade-up">
                <div className="inline-flex items-center gap-3 mb-6">
                    <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                        <circle cx="20" cy="20" r="19" stroke="url(#g1)" strokeWidth="2" />
                        <path d="M12 20l5 5 11-11" stroke="url(#g1)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                        <defs>
                            <linearGradient id="g1" x1="0" y1="0" x2="40" y2="40">
                                <stop stopColor="#818cf8" /><stop offset="0.5" stopColor="#38bdf8" /><stop offset="1" stopColor="#34d399" />
                            </linearGradient>
                        </defs>
                    </svg>
                    <h1 className="text-5xl font-black tracking-tight wordmark">VERITAS</h1>
                </div>
                <p className="text-lg secondary max-w-xl mx-auto leading-relaxed">
                    AI-powered fact-checking with full media bias transparency.
                    See how outlets across the political spectrum cover the same story.
                </p>
            </header>

            <main className="mx-auto w-full max-w-2xl px-4 pb-20 fade-up" style={{ animationDelay: '0.1s' }}>
                <div className="card border rounded-2xl shadow-2xl p-6">
                    {/* Tabs */}
                    <div className="flex gap-1 p-1 rounded-xl surface mb-6">
                        <Tab id="url" icon="🔗" label="Verify URL" />
                        <Tab id="file" icon="📄" label="Upload File" />
                        <Tab id="text" icon="✍️" label="Paste Text" />
                    </div>

                    {/* URL */}
                    {tab === 'url' && (
                        <div className="scale-in">
                            <input id="url-input" type="url" value={url}
                                onChange={e => setUrl(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && submit()}
                                placeholder="https://www.example.com/news/article..."
                                className="inp w-full rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition" />
                            <p className="text-xs muted mt-2 pl-1">Supports any publicly accessible news article URL.</p>
                        </div>
                    )}

                    {/* File */}
                    {tab === 'file' && (
                        <div className="scale-in">
                            <div className={`drop-zone border-2 border-dashed rounded-xl p-10 text-center cursor-pointer ${drag ? 'drag-over' : 'border-slate-600'}`}
                                onDragOver={e => { e.preventDefault(); setDrag(true) }}
                                onDragLeave={() => setDrag(false)}
                                onDrop={e => { e.preventDefault(); setDrag(false); e.dataTransfer.files[0] && setFile(e.dataTransfer.files[0]) }}
                                onClick={() => fileRef.current.click()}>
                                <input type="file" ref={fileRef} className="hidden" accept=".pdf,.doc,.docx,.txt"
                                    onChange={e => e.target.files[0] && setFile(e.target.files[0])} />
                                {file ? (
                                    <div>
                                        <p className="text-2xl mb-2">📄</p>
                                        <p className="font-semibold text-indigo-400">{file.name}</p>
                                        <p className="text-xs muted mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                                    </div>
                                ) : (
                                    <div>
                                        <p className="text-3xl mb-3">☁️</p>
                                        <p className="font-semibold secondary">
                                            Drop a file here or <span className="text-indigo-400">click to browse</span>
                                        </p>
                                        <p className="text-xs muted mt-1">PDF, DOCX, DOC, TXT</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Text */}
                    {tab === 'text' && (
                        <div className="scale-in">
                            <textarea id="text-input" value={text} onChange={e => setText(e.target.value)}
                                placeholder="Paste the full article text here (minimum 50 characters)..."
                                rows={7}
                                className="inp w-full rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition resize-none" />
                            <p className="text-xs muted mt-1.5 pl-1">{text.length} characters</p>
                        </div>
                    )}

                    <button id="analyze-btn" onClick={submit} disabled={!valid}
                        className="mt-5 w-full py-4 rounded-xl text-base font-bold text-white transition-all
                             bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed
                             hover:shadow-lg hover:shadow-indigo-500/25 active:scale-[.98]">
                        Disseminate →
                    </button>
                </div>

                <p className="text-center text-xs muted mt-5">
                    Try:{' '}
                    <button className="text-indigo-400 hover:underline"
                        onClick={() => { setTab('url'); setUrl('https://apnews.com/') }}>
                        AP News
                    </button>
                </p>
            </main>
        </div>
    )
}

// ─────────────────────────────────────────────
//  LOADING STATE
// ─────────────────────────────────────────────

function LoadingState({ input }) {
    const [step, setStep] = useState(0)
    useEffect(() => {
        const t = setInterval(() => setStep(s => Math.min(s + 1, LOADING_STEPS.length - 1)), 2200)
        return () => clearInterval(t)
    }, [])
    const label = input.type === 'url'
        ? (() => { try { return new URL(input.value).hostname } catch { return input.value } })()
        : input.type === 'file' ? input.value.name : 'Pasted text'

    return (
        <div className="min-h-screen flex flex-col items-center justify-center text-center px-4">
            <Spinner size={56} color="#818cf8" />
            <h2 className="mt-6 text-2xl font-bold" style={{ color: '#e2e8f0' }}>Analyzing…</h2>
            <p className="secondary text-sm mt-1 max-w-xs truncate">{label}</p>
            <div className="mt-10 space-y-2 text-left w-full max-w-xs">
                {LOADING_STEPS.map((s, i) => (
                    <div key={i} className={`flex items-center gap-3 text-sm transition-all duration-300 ${i < step ? 'opacity-40' : i === step ? 'opacity-100 step-active' : 'opacity-20'
                        }`}>
                        <span className="text-base">{i < step ? '✓' : i === step ? '▶' : '○'}</span>
                        <span style={{ color: i === step ? '#818cf8' : undefined }}>{s}</span>
                    </div>
                ))}
            </div>
        </div>
    )
}

// ─────────────────────────────────────────────
//  RESULTS PAGE
// ─────────────────────────────────────────────

function ResultsPage({ data, onReset }) {
    const { status, credibility_score, article_title, publish_date, source_analysis, related_coverage, results } = data.result
    const [biasFilter, setBiasFilter] = useState('All')
    const [openEvidence, setOpenEvidence] = useState({})
    const [summaryOpen, setSummaryOpen] = useState(false)
    const [summaryText, setSummaryText] = useState('')

    const toggleEvidence = i => setOpenEvidence(p => ({ ...p, [i]: !p[i] }))

    const filteredCoverage = (related_coverage || []).filter(o => {
        if (biasFilter === 'All') return true
        if (biasFilter === 'Left') return ['Left', 'Lean Left'].includes(o.bias)
        if (biasFilter === 'Center') return ['Center', 'Center-Right'].includes(o.bias)
        if (biasFilter === 'Right') return ['Lean Right', 'Right'].includes(o.bias)
        return true
    })

    const generateSummary = () => {
        const raw = (data.result.text || '').replace(/\s+/g, ' ').trim()
        let sents = raw.split(/(?<=[.!?])\s+/).filter(s => s.length > 40).slice(0, 5)
        if (!sents.length && results?.length) sents = results.map(r => r.claim).filter(Boolean).slice(0, 5)
        setSummaryText(sents.length ? sents.join(' ') : 'No summary available.')
        setSummaryOpen(true)
    }

    return (
        <div className="min-h-screen">
            {/* Sticky nav */}
            <nav className="sticky top-0 z-30 backdrop-blur-lg border-b"
                style={{ borderColor: 'rgba(71,85,105,0.4)', background: 'rgba(11,15,26,0.85)' }}>
                <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
                    <span className="text-lg font-black wordmark tracking-tight">VERITAS</span>
                    <button onClick={onReset}
                        className="px-4 py-1.5 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition">
                        ← New Analysis
                    </button>
                </div>
            </nav>

            <div className="max-w-5xl mx-auto px-4 py-8 space-y-6 fade-up">

                {/* ── Source Header ── */}
                <div className="card border rounded-2xl p-6">
                    <div className="flex flex-col md:flex-row gap-6 items-start">
                        <div className="flex items-start gap-4 flex-1 min-w-0">
                            <img src={source_analysis.logo_url || `https://www.google.com/s2/favicons?domain=${source_analysis.domain}&sz=64`}
                                alt={source_analysis.domain}
                                className="w-14 h-14 rounded-xl object-contain bg-slate-800 border border-slate-700 p-1 shrink-0"
                                onError={e => e.target.style.display = 'none'} />
                            <div className="min-w-0">
                                <h2 className="text-xl font-bold truncate" style={{ color: '#e2e8f0' }}>
                                    {source_analysis.domain || 'Uploaded Document'}
                                </h2>
                                {article_title && (
                                    <p className="text-sm secondary mt-1 leading-snug line-clamp-2">{article_title}</p>
                                )}
                                <div className="flex flex-wrap items-center gap-2 mt-3">
                                    <BiasBadge bias={source_analysis.bias} />
                                    <FactualityBadge rating={source_analysis.factual_reporting} />
                                    {source_analysis.country && <span className="text-xs muted">{source_analysis.country}</span>}
                                    {publish_date && <span className="text-xs muted">📅 {publish_date.slice(0, 10)}</span>}
                                </div>
                            </div>
                        </div>
                        <div className="flex flex-col items-center gap-3 shrink-0">
                            <DocStatusBadge status={status} />
                            <CredibilityRing score={credibility_score ?? 50} />
                        </div>
                    </div>
                </div>

                {/* ── Related Coverage ── */}
                {related_coverage?.length > 0 && (
                    <div className="card border rounded-2xl p-6 space-y-5">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                            <h3 className="font-bold text-lg" style={{ color: '#e2e8f0' }}>
                                📰 {related_coverage.length} Outlets Cover This Story
                            </h3>
                            <div className="flex gap-1.5 flex-wrap">
                                {['All', 'Left', 'Center', 'Right'].map(f => (
                                    <button key={f} onClick={() => setBiasFilter(f)}
                                        className={`pill border text-xs font-semibold px-3 py-1 rounded-full transition ${biasFilter === f ? 'pill-active' : ''}`}>
                                        {f}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="relative" style={{ padding: '8px 0' }}>
                            <SpectrumBar outlets={related_coverage} />
                        </div>

                        {filteredCoverage.length > 0 ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                {filteredCoverage.map((o, i) => {
                                    const facColor = FACTUALITY_COLOR[o.factual_reporting] || '#64748b'
                                    return (
                                        <a key={i} href={o.url} target="_blank" rel="noopener noreferrer"
                                            className="outlet-card card border rounded-xl p-4 flex flex-col gap-2 no-underline">
                                            <div className="flex items-center gap-2">
                                                <img src={o.logo_url} alt={o.domain}
                                                    className="w-8 h-8 rounded-lg object-contain bg-slate-800 border border-slate-700 p-0.5 shrink-0"
                                                    onError={e => { e.target.src = `https://www.google.com/s2/favicons?domain=${o.domain}&sz=64` }} />
                                                <span className="text-sm font-semibold truncate" style={{ color: '#e2e8f0' }}>{o.domain}</span>
                                            </div>
                                            <p className="text-xs secondary leading-snug line-clamp-2">{o.title}</p>
                                            {o.snippet && <p className="text-xs muted leading-snug line-clamp-2">{o.snippet}</p>}
                                            <div className="flex items-center justify-between mt-auto pt-1 flex-wrap gap-1">
                                                <BiasBadge bias={o.bias} small />
                                                <span className="text-xs font-medium" style={{ color: facColor }}>
                                                    {o.factual_reporting || 'Not Rated'}
                                                </span>
                                                {o.date && <span className="text-xs muted">{o.date}</span>}
                                            </div>
                                        </a>
                                    )
                                })}
                            </div>
                        ) : (
                            <p className="text-sm secondary text-center py-4">No outlets match this filter.</p>
                        )}
                    </div>
                )}

                {/* ── AI Summary ── */}
                <div className="card border rounded-2xl p-6">
                    <div className="flex items-center justify-between gap-4">
                        <div>
                            <h3 className="font-bold text-lg" style={{ color: '#e2e8f0' }}>✨ AI Summary</h3>
                            <p className="text-xs muted mt-0.5">Auto-generated from article text</p>
                        </div>
                        <button id="summary-btn" onClick={generateSummary}
                            className="shrink-0 px-4 py-2 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition">
                            Generate Summary
                        </button>
                    </div>
                    {summaryOpen && (
                        <div className="mt-4 p-4 rounded-xl surface text-sm prose-txt leading-relaxed scale-in">
                            {summaryText}
                        </div>
                    )}
                </div>

                {/* ── Claims ── */}
                <div>
                    <h3 className="font-bold text-lg mb-4" style={{ color: '#e2e8f0' }}>
                        🔍 Claim Analysis ({results.length} claims)
                    </h3>
                    {results.length > 0 ? (
                        <div className="space-y-3">
                            {results.map((item, idx) => (
                                <div key={idx} className="claim-card card border rounded-xl p-4 transition-all">
                                    <div className="flex flex-col sm:flex-row justify-between gap-3">
                                        <p className="text-sm leading-relaxed flex-1 prose-txt">{item.claim}</p>
                                        <VerdictBadge verdict={item.verdict} />
                                    </div>
                                    <button onClick={() => toggleEvidence(idx)}
                                        className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition">
                                        <svg className={`w-3.5 h-3.5 transition-transform ${openEvidence[idx] ? 'rotate-180' : ''}`}
                                            fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7" />
                                        </svg>
                                        {openEvidence[idx] ? 'Hide' : 'Show'} Evidence ({item.evidence.length})
                                    </button>
                                    {openEvidence[idx] && (
                                        <div className="mt-3 border-t pt-3 space-y-3 scale-in"
                                            style={{ borderColor: 'rgba(71,85,105,0.4)' }}>
                                            {item.evidence.length > 0 ? item.evidence.map((ev, ei) => (
                                                <div key={ei} className="surface rounded-lg p-3">
                                                    <a href={ev.url} target="_blank" rel="noopener noreferrer"
                                                        className="text-sm font-semibold text-indigo-400 hover:underline line-clamp-1">
                                                        {ev.title || 'Source'}
                                                    </a>
                                                    {ev.url && (
                                                        <p className="text-xs muted mt-0.5">
                                                            {(() => { try { return new URL(ev.url).hostname } catch { return ev.url } })()}
                                                        </p>
                                                    )}
                                                    <NLIBars scores={ev.scores} />
                                                </div>
                                            )) : (
                                                <p className="text-sm secondary">No evidence found for this claim.</p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="card border rounded-xl p-12 text-center">
                            <p className="text-4xl mb-3">🔎</p>
                            <h4 className="font-semibold text-base" style={{ color: '#e2e8f0' }}>No Verifiable Claims Found</h4>
                            <p className="text-sm secondary mt-2 max-w-sm mx-auto">
                                The AI did not identify concrete, verifiable claims. Common for opinion pieces or narrative articles.
                            </p>
                        </div>
                    )}
                </div>

                <div className="text-center pb-8">
                    <button onClick={onReset}
                        className="px-8 py-3 rounded-xl font-semibold text-sm bg-indigo-600 hover:bg-indigo-500 text-white transition">
                        ← Analyze Another Article
                    </button>
                </div>
            </div>
        </div>
    )
}

// ─────────────────────────────────────────────
//  THEME TOGGLE
// ─────────────────────────────────────────────

function ThemeToggle({ theme, onToggle }) {
    return (
        <button id="theme-toggle" onClick={onToggle}
            className="fixed top-4 right-4 z-50 w-10 h-10 rounded-full border backdrop-blur-md flex items-center justify-center transition"
            style={{ borderColor: 'rgba(99,102,241,0.4)', background: 'rgba(30,41,59,0.8)' }}
            title="Toggle theme">
            {theme === 'dark' ? '🌙' : '☀️'}
        </button>
    )
}

// ─────────────────────────────────────────────
//  ROOT APP
// ─────────────────────────────────────────────

export default function App() {
    const [appState, setAppState] = useState('home')
    const [taskInput, setTaskInput] = useState(null)
    const [resultsData, setResultsData] = useState(null)
    const [error, setError] = useState('')
    const [theme, setTheme] = useState('dark')
    const pollRef = useRef(null)

    useEffect(() => { document.body.className = theme }, [theme])
    useEffect(() => () => clearInterval(pollRef.current), [])

    const startPolling = taskId => {
        pollRef.current = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/api/result/${taskId}`)
                if (!res.ok) throw new Error('Network error')
                const data = await res.json()
                if (data.status === 'SUCCESS') {
                    clearInterval(pollRef.current)
                    setResultsData(data)
                    setAppState('results')
                } else if (data.status === 'FAILURE') {
                    clearInterval(pollRef.current)
                    setError(data.error || 'Analysis failed.')
                    setAppState('error')
                }
            } catch (e) {
                clearInterval(pollRef.current)
                setError('Could not reach the server. Is the backend running?')
                setAppState('error')
            }
        }, 3000)
    }

    const handleStart = async input => {
        clearInterval(pollRef.current)
        setAppState('loading')
        setTaskInput(input)
        setError('')

        const endpoint =
            input.type === 'url' ? `${API_BASE}/api/verify/url` :
                input.type === 'file' ? `${API_BASE}/api/verify/file` :
                    `${API_BASE}/api/verify/text`

        const formData = new FormData()
        formData.append(input.type, input.value)

        try {
            const res = await fetch(endpoint, { method: 'POST', body: formData })
            if (!res.ok) throw new Error(`Server error ${res.status}`)
            const data = await res.json()
            if (data.status === 'SUCCESS') {
                setResultsData(data)
                setAppState('results')
            } else if (data.task_id) {
                startPolling(data.task_id)
            } else {
                throw new Error('Unexpected server response.')
            }
        } catch (e) {
            setError(e.message)
            setAppState('error')
        }
    }

    const handleReset = () => {
        clearInterval(pollRef.current)
        setAppState('home')
        setResultsData(null)
        setTaskInput(null)
        setError('')
    }

    return (
        <>
            <ThemeToggle theme={theme} onToggle={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} />
            {appState === 'home' && <HomePage onStartAnalysis={handleStart} />}
            {appState === 'loading' && <LoadingState input={taskInput} />}
            {appState === 'results' && <ResultsPage data={resultsData} onReset={handleReset} />}
            {appState === 'error' && (
                <div className="min-h-screen flex flex-col items-center justify-center text-center px-4 gap-4">
                    <p className="text-4xl">⚠️</p>
                    <h2 className="text-xl font-bold" style={{ color: '#f87171' }}>Analysis Failed</h2>
                    <p className="text-sm secondary max-w-sm">{error}</p>
                    <button onClick={handleReset}
                        className="mt-4 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition">
                        Try Again
                    </button>
                </div>
            )}
        </>
    )
}
