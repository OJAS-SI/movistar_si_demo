/**
 * One run, from "start it" to "here is everything it produced".
 *
 * A run is deterministic from its scale and seed, so there is nothing to keep in sync:
 * we ask the API to execute one, wait for it, and then read the console it produced.
 * Every panel in the app is a view of that single payload, which is exactly why the
 * console, the scorecard and the map can never contradict each other.
 */

import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { ConsoleOut, RunOut, ScaleName } from '../api/types'

export type RunPhase = 'starting' | 'ready' | 'failed'

export interface DemoRun {
  phase: RunPhase
  run: RunOut | null
  console: ConsoleOut | null
  /** The run is created and rendering, but its full console is still being computed. */
  computing: boolean
  error: string | null
  /** Start a fresh run at this scale, replacing the current one. */
  restart: (scale: ScaleName) => void
  scale: ScaleName
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export function useDemoRun(initialScale: ScaleName = 'tiny'): DemoRun {
  const [scale, setScale] = useState<ScaleName>(initialScale)
  const [phase, setPhase] = useState<RunPhase>('starting')
  const [run, setRun] = useState<RunOut | null>(null)
  const [consoleModel, setConsoleModel] = useState<ConsoleOut | null>(null)
  const [computing, setComputing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Bumping this re-runs the effect below, which is how "run it again" works even when
  // the scale has not changed.
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function start() {
      setPhase('starting')
      setError(null)
      setRun(null)
      setConsoleModel(null)
      setComputing(false)

      try {
        // A tiny run lands in well under a second, so we let the server compute it and
        // hand back the finished answer. A full run takes ~80s, so we do NOT wait: create
        // it lazily (execute=false), render immediately, and let the live stream compute
        // it once while faults appear. The console is polled for and swapped in when it is
        // ready - the UI is never blocked on the whole run.
        const eager = scale === 'tiny'
        const started = await api.createRun(
          { scale },
          { waitSeconds: eager ? 30 : 0, execute: eager },
        )
        if (cancelled) return

        if (started.status === 'failed') {
          throw new ApiError(500, started.error ?? 'The run failed inside the engine.')
        }

        // A run that already finished (tiny): fetch its console, then reveal the full
        // view in one step - no flash of the live deck.
        if (started.status === 'complete') {
          const model = await api.getConsole(started.run_id)
          if (cancelled) return
          setRun(started)
          setConsoleModel(model)
          setPhase('ready')
          return
        }

        // A lazy run (full): render now. The stream, opened by the console once it has a
        // run id, both drives the live view and computes the run. Poll until it has been
        // computed and stored, then swap in the full console - faults are visible live the
        // whole time.
        setRun(started)
        setPhase('ready')
        setComputing(true)
        for (;;) {
          await sleep(1200)
          if (cancelled) return
          let latest: RunOut
          try {
            latest = await api.getRun(started.run_id)
          } catch {
            continue // transient; keep polling
          }
          if (latest.status === 'failed') {
            throw new ApiError(500, latest.error ?? 'The run failed inside the engine.')
          }
          if (latest.status === 'complete') {
            const model = await api.getConsole(started.run_id)
            if (cancelled) return
            setRun(latest)
            setConsoleModel(model)
            setComputing(false)
            return
          }
        }
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : String(err))
        setPhase('failed')
        setComputing(false)
      }
    }

    void start()
    return () => {
      cancelled = true
    }
  }, [scale, attempt])

  const restart = useCallback((next: ScaleName) => {
    setScale(next)
    setAttempt((n) => n + 1)
  }, [])

  return { phase, run, console: consoleModel, computing, error, restart, scale }
}