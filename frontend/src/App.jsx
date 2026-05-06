/**
 * App.jsx — Veritas root application shell
 *
 * This file is intentionally lean. All business logic lives in:
 *   hooks/useAnalysis.js       — WebSocket + polling state machine
 *   components/HomePage.jsx    — Landing / input page
 *   components/LoadingState.jsx — Animated pipeline progress
 *   components/ResultsPage.jsx  — Full analysis report
 *   components/ui/Badge.jsx    — Pill badges
 *   components/ui/Spinner.jsx  — Loading spinner
 *   components/CredibilityRing.jsx
 *   components/SpectrumBar.jsx
 *   components/EvidenceItem.jsx
 */

import { useState, useEffect } from 'react'
import { useAnalysis } from './hooks/useAnalysis.js'
import { HomePage }    from './components/HomePage.jsx'
import { LoadingState } from './components/LoadingState.jsx'
import { ResultsPage }  from './components/ResultsPage.jsx'

// ── Theme toggle ────────────────────────────────────────────────────────────
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

// ── App ─────────────────────────────────────────────────────────────────────
export default function App() {
    const [theme, setTheme] = useState('dark')
    const { appState, taskInput, resultsData, error, handleStart, handleReset } = useAnalysis()

    useEffect(() => { document.body.className = theme }, [theme])

    return (
        <>
            <ThemeToggle theme={theme} onToggle={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} />

            {appState === 'home' && (
                <HomePage onStartAnalysis={handleStart} />
            )}

            {appState === 'loading' && (
                <LoadingState input={taskInput} />
            )}

            {appState === 'results' && (
                <ResultsPage data={resultsData} onReset={handleReset} />
            )}

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
