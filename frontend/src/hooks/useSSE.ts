import { useCallback, useRef, useState } from 'react'

interface SSEOptions {
  url: string
  method?: 'POST' | 'GET'
  body?: any
  onEvent?: (event: { type: string; data: any }) => void
  onError?: (error: any) => void
  onDone?: () => void
}

export function useSSE() {
  const [isConnected, setIsConnected] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const connect = useCallback(async (opts: SSEOptions) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setIsConnected(true)

    try {
      const res = await fetch(opts.url, {
        method: opts.method || 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: opts.body ? JSON.stringify(opts.body) : undefined,
        signal: controller.signal,
      })

      const reader = res.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const eventMatch = line.match(/^event: (.+)$/)
          const dataMatch = line.match(/^data: (.+)$/)

          if (eventMatch) {
            continue // event type line, not actionable here
          }

          if (dataMatch) {
            try {
              const parsed = JSON.parse(dataMatch[1])
              if (parsed.type === 'done') {
                opts.onDone?.()
              } else {
                opts.onEvent?.({ type: parsed.type, data: parsed.data })
              }
            } catch { /* skip unparseable */ }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        opts.onError?.(err)
      }
    } finally {
      setIsConnected(false)
    }
  }, [])

  const disconnect = useCallback(() => {
    abortRef.current?.abort()
    setIsConnected(false)
  }, [])

  return { isConnected, connect, disconnect }
}