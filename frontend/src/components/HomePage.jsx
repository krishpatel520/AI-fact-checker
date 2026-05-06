/**
 * HomePage.jsx
 * ------------
 * Landing page with URL / File / Text input tabs.
 */
import { useState, useRef } from 'react'

export function HomePage({ onStartAnalysis }) {
    const [tab,  setTab]  = useState('url')
    const [url,  setUrl]  = useState('')
    const [file, setFile] = useState(null)
    const [text, setText] = useState('')
    const [drag, setDrag] = useState(false)
    const fileRef = useRef(null)

    const valid =
        (tab === 'url'  && url.trim()) ||
        (tab === 'file' && file) ||
        (tab === 'text' && text.trim().length > 50)

    const submit = () => {
        if (!valid) return
        onStartAnalysis({
            type:  tab,
            value: tab === 'url' ? url : tab === 'file' ? file : text,
        })
    }

    const Tab = ({ id, icon, label }) => (
        <button id={`tab-${id}`} onClick={() => setTab(id)}
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
                        <path d="M12 20l5 5 11-11" stroke="url(#g1)" strokeWidth="2.5"
                            strokeLinecap="round" strokeLinejoin="round" />
                        <defs>
                            <linearGradient id="g1" x1="0" y1="0" x2="40" y2="40">
                                <stop stopColor="#818cf8" />
                                <stop offset="0.5" stopColor="#38bdf8" />
                                <stop offset="1" stopColor="#34d399" />
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
                        <Tab id="url"  icon="🔗" label="Verify URL" />
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
