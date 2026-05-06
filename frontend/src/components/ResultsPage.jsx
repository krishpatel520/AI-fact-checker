/**
 * ResultsPage.jsx
 * ---------------
 * Full analysis report page — source header, coverage map, AI summary, claims list.
 */
import { useState } from 'react'
import { BiasBadge, FactualityBadge, FACTUALITY_COLOR } from './ui/Badge.jsx'
import { DocStatusBadge, VerdictBadge } from './ui/Badge.jsx'
import { CredibilityRing } from './CredibilityRing.jsx'
import { SpectrumBar } from './SpectrumBar.jsx'
import { EvidenceItem } from './EvidenceItem.jsx'

export function ResultsPage({ data, onReset }) {
    const {
        status, credibility_score, article_title, publish_date,
        source_analysis, related_coverage, results,
    } = data.result

    const [biasFilter,   setBiasFilter]   = useState('All')
    const [openEvidence, setOpenEvidence] = useState({})
    const [summaryOpen,  setSummaryOpen]  = useState(false)
    const [summaryText,  setSummaryText]  = useState('')

    const toggleEvidence = i => setOpenEvidence(p => ({ ...p, [i]: !p[i] }))

    const filteredCoverage = (related_coverage || []).filter(o => {
        if (biasFilter === 'All')    return true
        if (biasFilter === 'Left')   return ['Left', 'Lean Left'].includes(o.bias)
        if (biasFilter === 'Center') return ['Center', 'Center-Right'].includes(o.bias)
        if (biasFilter === 'Right')  return ['Lean Right', 'Right'].includes(o.bias)
        return true
    })

    const generateSummary = () => {
        const raw   = (data.result.text || '').replace(/\s+/g, ' ').trim()
        let sents   = raw.split(/(?<=[.!?])\s+/).filter(s => s.length > 40).slice(0, 5)
        if (!sents.length && results?.length)
            sents = results.map(r => r.claim).filter(Boolean).slice(0, 5)
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
                    <button id="new-analysis-btn" onClick={onReset}
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
                            <img
                                src={source_analysis.logo_url || `https://www.google.com/s2/favicons?domain=${source_analysis.domain}&sz=64`}
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
                                    <button key={f} id={`filter-${f.toLowerCase()}`}
                                        onClick={() => setBiasFilter(f)}
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
                                    <button id={`evidence-toggle-${idx}`} onClick={() => toggleEvidence(idx)}
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
                                            {item.evidence.length > 0
                                                ? item.evidence.map((ev, ei) => <EvidenceItem key={ei} ev={ev} index={ei} />)
                                                : <p className="text-sm secondary">No evidence found for this claim.</p>
                                            }
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
