/**
 * useAnalysis.js
 * ---------------
 * Custom hook that manages the full analysis lifecycle:
 *   1. Submit a URL / file / text to the backend
 *   2. Connect via WebSocket for instant push delivery
 *   3. Fall back to polling /api/job/{job_id} if WS fails or times out
 *
 * Returns: { appState, taskInput, resultsData, error, handleStart, handleReset }
 */

import { useState, useRef, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const WS_BASE = import.meta.env.VITE_WS_URL ??
    (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host

export function useAnalysis() {
    const [appState, setAppState]     = useState('home')      // home | loading | results | error
    const [taskInput, setTaskInput]   = useState(null)
    const [resultsData, setResultsData] = useState(null)
    const [error, setError]           = useState('')
    const pollRef = useRef(null)
    const wsRef   = useRef(null)

    // Cleanup on unmount
    useEffect(() => () => {
        clearInterval(pollRef.current)
        wsRef.current?.close()
    }, [])

    // ── Polling fallback ──────────────────────────────────────────────────────
    const startJobPolling = (jobId) => {
        pollRef.current = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/api/job/${jobId}`)
                if (!res.ok) throw new Error('Network error')
                const data = await res.json()

                if (data.status === 'done') {
                    clearInterval(pollRef.current)
                    setResultsData({ status: 'SUCCESS', result: data.result })
                    setAppState('results')
                } else if (data.status === 'failed') {
                    clearInterval(pollRef.current)
                    setError(data.error || 'Analysis failed.')
                    setAppState('error')
                }
                // pending | running → keep polling
            } catch (e) {
                clearInterval(pollRef.current)
                setError('Could not reach the server. Is the backend running?')
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
                const msg = JSON.parse(evt.data)
                if (msg.status_event === 'done') {
                    clearInterval(pollRef.current)
                    const { status_event, job_id, ...result } = msg
                    setResultsData({ status: 'SUCCESS', result })
                    setAppState('results')
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

        const endpoint =
            input.type === 'url'  ? `${API_BASE}/api/verify/url`  :
            input.type === 'file' ? `${API_BASE}/api/verify/file` :
                                    `${API_BASE}/api/verify/text`

        const formData = new FormData()
        if (input.type === 'file') formData.append('file', input.value)
        else formData.append(input.type, input.value)

        try {
            const res = await fetch(endpoint, { method: 'POST', body: formData })
            if (!res.ok) throw new Error(`Server error ${res.status}`)
            const data = await res.json()

            if (data.status === 'SUCCESS') {
                // Cache hit — instant result
                setResultsData(data)
                setAppState('results')
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
    }

    return { appState, taskInput, resultsData, error, handleStart, handleReset }
}
