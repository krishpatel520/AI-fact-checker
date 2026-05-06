/**
 * LoadingState.jsx
 * ----------------
 * Animated step-tracker shown while the agentic pipeline runs.
 */
import { useState, useEffect } from 'react'
import { Spinner } from './ui/Spinner.jsx'

const LOADING_STEPS = [
    'Fetching article content…',
    'Analyzing source bias…',
    'Extracting factual claims…',
    'Verifying claims with Ollama LLM…',
    'Finding related coverage…',
    'Building your report…',
]

export function LoadingState({ input }) {
    const [step, setStep] = useState(0)

    useEffect(() => {
        const t = setInterval(() => setStep(s => Math.min(s + 1, LOADING_STEPS.length - 1)), 2200)
        return () => clearInterval(t)
    }, [])

    const label =
        input.type === 'url'  ? (() => { try { return new URL(input.value).hostname } catch { return input.value } })() :
        input.type === 'file' ? input.value.name :
                                'Pasted text'

    return (
        <div className="min-h-screen flex flex-col items-center justify-center text-center px-4">
            <Spinner size={56} color="#818cf8" />
            <h2 className="mt-6 text-2xl font-bold" style={{ color: '#e2e8f0' }}>Analyzing…</h2>
            <p className="secondary text-sm mt-1 max-w-xs truncate">{label}</p>
            <div className="mt-10 space-y-2 text-left w-full max-w-xs">
                {LOADING_STEPS.map((s, i) => (
                    <div key={i} className={`flex items-center gap-3 text-sm transition-all duration-300 ${
                        i < step ? 'opacity-40' : i === step ? 'opacity-100 step-active' : 'opacity-20'
                    }`}>
                        <span className="text-base">{i < step ? '✓' : i === step ? '▶' : '○'}</span>
                        <span style={{ color: i === step ? '#818cf8' : undefined }}>{s}</span>
                    </div>
                ))}
            </div>
        </div>
    )
}
