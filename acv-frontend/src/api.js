import { useCallback, useRef, useState } from 'react'

// POST to the API and read its Server-Sent Events stream.
async function streamAgent(url, body, onEvent) {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!res.ok || !res.body) throw new Error(`Request failed (${res.status})`)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, i)
      buf = buf.slice(i + 2)
      const line = chunk.split('\n').find((l) => l.startsWith('data: '))
      if (line) onEvent(JSON.parse(line.slice(6)))
    }
  }
}

const EMPTY = null

// One agent run: its activity log, pending question, and final values.
export function useAgent(agent) {
  const [run, setRun] = useState(EMPTY)
  const thread = useRef(null) // read synchronously by resume(), so it lives outside state

  const handle = useCallback((ev) => {
    if (ev.type === 'start') thread.current = ev.thread_id
    setRun((r) => {
      if (!r) return r
      switch (ev.type) {
        case 'start': return { ...r, thread: ev.thread_id }
        case 'log': return { ...r, log: [...r.log, ev.line] }
        case 'interrupt': return { ...r, pending: ev.value }
        case 'done': return { ...r, busy: false, values: ev.values, pending: ev.pending ? r.pending : null }
        case 'error': return { ...r, busy: false, error: ev.message }
        default: return r
      }
    })
  }, [])

  const start = useCallback(async (payload, userText) => {
    setRun({ thread: null, log: [], pending: null, values: {}, busy: true, userText, error: null })
    try {
      await streamAgent(`/api/${agent}/start`, { payload }, handle)
    } catch (e) {
      setRun((r) => ({ ...r, busy: false, error: e.message }))
    }
  }, [agent, handle])

  const resume = useCallback(async (value, choiceText) => {
    setRun((r) => ({ ...r, busy: true, pending: null, choices: [...(r.choices || []), { at: r.log.length, text: choiceText }] }))
    try {
      await streamAgent(`/api/${agent}/resume`, { thread_id: thread.current, resume: value }, handle)
    } catch (e) {
      setRun((r) => ({ ...r, busy: false, error: e.message }))
    }
  }, [agent, handle])

  const clear = useCallback(() => { thread.current = null; setRun(EMPTY) }, [])
  return { run, start, resume, clear }
}

export const money = (n) => (n == null ? '' : `$${Math.round(n).toLocaleString('en-US')}`)
export const miles = (n) => `${Math.round(n).toLocaleString('en-US')} mi`
