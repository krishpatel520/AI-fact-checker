/**
 * Badge.jsx
 * ---------
 * Pill-shaped badge components for bias, factuality, verdict, and doc status.
 */

export const BIAS_CONFIG = {
    'Left':         { color: '#3b82f6', score: -1.0 },
    'Lean Left':    { color: '#60a5fa', score: -0.5 },
    'Center':       { color: '#94a3b8', score:  0.0 },
    'Center-Right': { color: '#fb923c', score:  0.4 },
    'Lean Right':   { color: '#f97316', score:  0.5 },
    'Right':        { color: '#ef4444', score:  1.0 },
    'Not Rated':    { color: '#64748b', score: null  },
    'N/A':          { color: '#64748b', score: null  },
}

export const FACTUALITY_COLOR = {
    'Very High':      '#22c55e',
    'High':           '#86efac',
    'Mostly Factual': '#fbbf24',
    'Mixed':          '#f97316',
    'Low':            '#ef4444',
    'Very Low':       '#b91c1c',
    'Not Rated':      '#64748b',
    'N/A':            '#64748b',
}

export function BiasBadge({ bias, small }) {
    const cfg = BIAS_CONFIG[bias] || BIAS_CONFIG['Not Rated']
    const cls = small ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-xs font-semibold'
    return (
        <span
            className={`${cls} rounded-full font-semibold inline-flex items-center`}
            style={{ background: cfg.color + '22', color: cfg.color, border: `1px solid ${cfg.color}55` }}
        >
            {bias || 'Not Rated'}
        </span>
    )
}

export function FactualityBadge({ rating }) {
    const color = FACTUALITY_COLOR[rating] || '#64748b'
    return (
        <span
            className="px-2 py-0.5 text-xs rounded-full font-medium"
            style={{ background: color + '1a', color, border: `1px solid ${color}44` }}
        >
            {rating || 'Not Rated'}
        </span>
    )
}

export function VerdictBadge({ verdict }) {
    const map = {
        supported:       { bg: '#22c55e22', text: '#4ade80', border: '#22c55e44', label: 'Supported' },
        refuted:         { bg: '#ef444422', text: '#f87171', border: '#ef444444', label: 'Refuted' },
        not_enough_info: { bg: '#64748b22', text: '#94a3b8', border: '#64748b44', label: 'Not Enough Info' },
    }
    const s = map[verdict] || map.not_enough_info
    return (
        <span
            className="px-3 py-1 text-xs font-bold rounded-full whitespace-nowrap"
            style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}
        >
            {s.label}
        </span>
    )
}

export function DocStatusBadge({ status }) {
    const map = {
        clean_document:     { bg: '#22c55e22', text: '#4ade80', border: '#22c55e44', icon: '✓', label: 'Clean Document' },
        inaccuracies_found: { bg: '#ef444422', text: '#f87171', border: '#ef444444', icon: '⚠', label: 'Inaccuracies Found' },
        not_enough_info:    { bg: '#64748b22', text: '#94a3b8', border: '#64748b44', icon: '?', label: 'Not Enough Info' },
    }
    const s = map[status] || map.not_enough_info
    return (
        <span
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold"
            style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}
        >
            {s.icon} {s.label}
        </span>
    )
}
