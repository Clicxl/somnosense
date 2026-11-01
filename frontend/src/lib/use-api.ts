import { useCallback, useEffect, useState } from 'react'
import { api, type ApiError } from './api'

// Fetches `path` (null = nothing to fetch), again every `pollMs` if given. Keeps the last data through an error.
export function useApi<T>(path: string | null, pollMs?: number) {
  const [state, setState] = useState<{ path: string | null; data?: T; error?: ApiError }>({ path })
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!path) return
    let busy = false
    let live = true
    const load = () => {
      if (busy) return // a reply slower than pollMs must still land, not be overtaken by the next poll
      busy = true
      api<T>(path)
        .then(
          (data) => live && setState({ path, data }),
          (error: ApiError) => live && setState((s) => ({ path, data: s.path === path ? s.data : undefined, error })),
        )
        .finally(() => (busy = false))
    }
    load()
    const timer = pollMs ? setInterval(load, pollMs) : undefined
    return () => {
      live = false
      clearInterval(timer)
    }
  }, [path, pollMs, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  const mine = state.path === path
  return { data: mine ? state.data : undefined, error: mine ? state.error : undefined, reload }
}
