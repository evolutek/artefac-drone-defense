import { useEffect, useState } from 'react'
import { isTauri, startAll, stopAll, status } from '../utils/tauri'

export function SystemControl() {
  const [loading, setLoading] = useState(false)
  const [services, setServices] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    setError(null)
    try {
      const s = await status()
      setServices(s.services)
    } catch (e: any) {
      setError(e.message || String(e))
    }
  }

  async function handleStart() {
    setLoading(true)
    setError(null)
    try {
      await startAll()
      await refresh()
    } catch (e: any) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  async function handleStop() {
    setLoading(true)
    setError(null)
    try {
      await stopAll()
      await refresh()
    } catch (e: any) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isTauri) {
      refresh()
    }
  }, [])

  if (!isTauri) {
    return null
  }

  return (
    <div className="bg-white border rounded-lg p-4 shadow">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-bold">System Control</h2>
        <div className="flex gap-2">
          <button
            className="bg-green-600 text-white px-3 py-2 rounded disabled:opacity-50"
            onClick={handleStart}
            disabled={loading}
          >Start All</button>
          <button
            className="bg-red-600 text-white px-3 py-2 rounded disabled:opacity-50"
            onClick={handleStop}
            disabled={loading}
          >Stop All</button>
          <button
            className="bg-blue-600 text-white px-3 py-2 rounded disabled:opacity-50"
            onClick={refresh}
            disabled={loading}
          >Refresh</button>
        </div>
      </div>
      {error && <div className="text-red-700">{error}</div>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {Object.entries(services).map(([name, state]) => (
          <div key={name} className="flex items-center justify-between border rounded p-2">
            <span className="font-medium">{name}</span>
            <span className={state.includes('Up') ? 'text-green-700' : 'text-yellow-700'}>{state}</span>
          </div>
        ))}
      </div>
    </div>
  )
}