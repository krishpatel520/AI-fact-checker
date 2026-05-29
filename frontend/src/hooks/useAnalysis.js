/**
 * useAnalysis.js
 * ---------------
 * Custom hook that manages the full analysis lifecycle:
 *   1. Submit a URL / file / text to the backend
 *   2. Connect via WebSocket for instant push delivery
 *   3. Fall back to polling /api/job/{job_id} if WS fails or times out
 *
 * Returns: { appState, taskInput, resultsData, error, analysisComplete, handleStart, handleReset }
 */

import { useState, useRef, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const WS_BASE = import.meta.env.VITE_WS_URL ??
    (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host

export function useAnalysis() {
    const [appState, setAppState]         = useState('home')      // home | loading | results | error
    const [taskInput, setTaskInput]       = useState(null)
    const [resultsData, setResultsData]   = useState(null)
    const [error, setError]               = useState('')
    const [analysisComplete, setAnalysisComplete] = useState(false)
    const pollRef = useRef(null)
    const wsRef   = useRef(null)

    // Cleanup on unmount
    useEffect(() => () => {
        clearInterval(pollRef.current)
        wsRef.current?.close()
    }, [])

    // ── Helpers ───────────────────────────────────────────────────────────────

    const _finishWithResult = (result) => {
        setAnalysisComplete(true)
        // Small delay so the LoadingState animation can show the final step.
        setTimeout(() => {
            setResultsData(result)
            setAppState('results')
        }, 400)
    }

    // Parse server error bodies so users see actionable messages.
    const _fetchErrorMessage = async (res) => {
        try {
            const ct = res.headers.get('content-type') || ''
            if (ct.includes('application/json')) {
                const body = await res.json()
                return body.detail || body.error || `Server error ${res.status}`
            }
        } catch {
            // ignore parse failure
        }
        return `Server error ${res.status}`
    }

    // ── Polling fallback ──────────────────────────────────────────────────────
    const startJobPolling = (jobId) => {
        pollRef.current = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/api/job/${jobId}`)
                if (!res.ok) throw new Error(await _fetchErrorMessage(res))
                const data = await res.json()

                if (data.status === 'done') {
                    clearInterval(pollRef.current)
                    _finishWithResult({ status: 'SUCCESS', result: data.result })
                } else if (data.status === 'failed') {
                    clearInterval(pollRef.current)
                    setError(data.error || 'Analysis failed.')
                    setAppState('error')
                }
                // pending | running → keep polling
            } catch (e) {
                clearInterval(pollRef.current)
                setError(e.message || 'Could not reach the server. Is the backend running?')
                setAppState('error')
            }
        }, 3000)
    }

    // ── WebSocket primary ─────────────────────────────────────────────────────
    const connectWebSocket = (jobId) => {
        try {
            const ws = new WebSocket(`${WS_BASE}/ws/${jobId}`)
            wsRef.current = ws

            ws.onmessage = (evt) => {
                let msg
                try {
                    msg = JSON.parse(evt.data)
                } catch {
                    return  // ignore unparseable frames
                }
                if (!msg || typeof msg.status_event !== 'string') return

                if (msg.status_event === 'done') {
                    clearInterval(pollRef.current)
                    const { status_event, job_id, ...result } = msg  // eslint-disable-line no-unused-vars
                    _finishWithResult({ status: 'SUCCESS', result })
                } else if (msg.status_event === 'timeout') {
                    startJobPolling(jobId)
                } else if (msg.status_event === 'error') {
                    setError(msg.detail || 'Analysis error.')
                    setAppState('error')
                }
            }
            ws.onerror = () => { ws.close(); startJobPolling(jobId) }
        } catch {
            startJobPolling(jobId)
        }
    }

    // ── Submit ────────────────────────────────────────────────────────────────
    const handleStart = async (input) => {
        clearInterval(pollRef.current)
        wsRef.current?.close()
        setAppState('loading')
        setTaskInput(input)
        setError('')
        setAnalysisComplete(false)

        const endpoint =
            input.type === 'url'  ? `${API_BASE}/api/verify/url`  :
            input.type === 'file' ? `${API_BASE}/api/verify/file` :
                                    `${API_BASE}/api/verify/text`

        const formData = new FormData()
        if (input.type === 'file') formData.append('file', input.value)
        else formData.append(input.type, input.value)

        try {
            const res = await fetch(endpoint, { method: 'POST', body: formData })
            if (!res.ok) throw new Error(await _fetchErrorMessage(res))
            const data = await res.json()

            if (data.status === 'SUCCESS') {
                // Cache hit — instant result
                _finishWithResult(data)
            } else if (data.job_id) {
                connectWebSocket(data.job_id)
            } else {
                throw new Error('Unexpected server response.')
            }
        } catch (e) {
            setError(e.message)
            setAppState('error')
        }
    }

    // ── Reset ─────────────────────────────────────────────────────────────────
    const handleReset = () => {
        clearInterval(pollRef.current)
        wsRef.current?.close()
        setAppState('home')
        setResultsData(null)
        setTaskInput(null)
        setError('')
        setAnalysisComplete(false)
    }

    return { appState, taskInput, resultsData, error, analysisComplete, handleStart, handleReset }
}
