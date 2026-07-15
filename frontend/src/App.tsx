/**
 * The Service Intelligence console.
 *
 * The whole app is a view of two things: one run's console payload (the verdicts, the
 * receipts, the scorecard) and that run's replayed stream (what the engine saw, interval
 * by interval). Everything on screen is derived from those. There is no local model of
 * the network, no second source of truth, and nothing invented to fill a gap - if the
 * API did not measure it, the console does not show it.
 */

import { useEffect, useMemo, useState } from 'react'
import { Header, type TabKey } from './components/Header'
import { Transport } from './components/Transport'
import { LiveDeck } from './components/LiveDeck'
import { AnalystTab } from './components/analyst/AnalystTab'
import { ManagementTab } from './components/management/ManagementTab'
import { MapTab } from './components/map/MapTab'
import { Icon } from './components/Icon'
import { useDemoRun } from './hooks/useDemoRun'
import { useReplay } from './hooks/useReplay'
import { buildAlerts, liveFaults, mostRecentlyNamed } from './lib/alerts'
import type { ScaleName } from './api/types'

export default function App() {
  const { phase, run, console: model, computing, error, restart, scale } = useDemoRun('tiny')

  const replay = useReplay(
    phase === 'ready' && run ? run.run_id : null,
    run?.config.run_intervals ?? 0,
  )

  const [tab, setTab] = useState<TabKey>('analyst')
  const [pinned, setPinned] = useState<string | null>(null)

  const intervalSeconds = run?.config.interval_seconds ?? 300

  const alerts = useMemo(
    () => (model ? buildAlerts(model, replay.onsets) : []),
    [model, replay.onsets],
  )

  // While the full run is still computing, the faults the engine has already named,
  // straight off the stream. This is what makes the toggle feel instant: the deck fills
  // as detection happens, instead of waiting for the whole run.
  const live = useMemo(() => liveFaults(replay.frames), [replay.frames])
  const frontier = replay.frames.length > 0 ? replay.frames[replay.frames.length - 1] : null

  // Follow the run unless the operator has pinned an alert: as each verdict lands, the
  // console turns to it. Pinning is how you stop it moving under you while you read.
  const following = useMemo(() => mostRecentlyNamed(alerts, replay.t), [alerts, replay.t])

  const selected = useMemo(() => {
    const pin = alerts.find((alert) => alert.useCase === pinned)
    // A pinned alert the timeline has scrubbed back past is not a verdict yet, so fall
    // back to following rather than showing a call that has not happened.
    if (pin && replay.t >= pin.namedAt) return pin
    return following
  }, [alerts, pinned, following, replay.t])

  // Space plays and pauses; the arrows step interval by interval. Someone presenting this
  // should not have to reach for the mouse to stop on the moment that matters.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target && ['INPUT', 'TEXTAREA', 'BUTTON'].includes(target.tagName)) return

      if (event.code === 'Space') {
        event.preventDefault()
        replay.togglePlay()
      } else if (event.code === 'ArrowRight') {
        replay.setT(replay.t + 1)
      } else if (event.code === 'ArrowLeft') {
        replay.setT(replay.t - 1)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [replay])

  const openAlert = (useCase: string) => {
    setPinned(useCase)
    setTab('analyst')
  }

  const onScale = (next: ScaleName) => {
    setPinned(null)
    restart(next)
  }

  return (
    <div className="app">
      <Header
        model={model}
        run={run}
        scale={scale}
        busy={phase === 'starting' || computing}
        tab={tab}
        onTab={setTab}
        onScale={onScale}
      />

      <div id="content">
        {phase === 'starting' && <Starting scale={scale} />}
        {phase === 'failed' && <Failed error={error} onRetry={() => restart(scale)} />}

        {phase === 'ready' && !model && (
          <LiveDeck
            live={live}
            frame={frontier}
            t={frontier?.timestamp ?? 0}
            totalIntervals={replay.totalIntervals || (run?.config.run_intervals ?? 1)}
            intervalSeconds={intervalSeconds}
            progress={replay.progress}
          />
        )}

        {phase === 'ready' && model && (
          <>
            {tab === 'analyst' && (
              <AnalystTab
                model={model}
                alerts={alerts}
                selected={selected}
                onSelect={setPinned}
                t={replay.t}
                frame={replay.frame}
                intervalSeconds={intervalSeconds}
              />
            )}
            {tab === 'mgmt' && <ManagementTab model={model} run={run} alerts={alerts} />}
            {tab === 'map' && (
              <MapTab
                run={run}
                alerts={alerts}
                t={replay.t}
                intervalSeconds={intervalSeconds}
                onOpenAlert={openAlert}
              />
            )}
          </>
        )}
      </div>

      <Transport
        frames={replay.frames}
        totalIntervals={replay.totalIntervals || (run?.config.run_intervals ?? 1)}
        intervalSeconds={intervalSeconds}
        alerts={alerts}
        onsets={replay.onsets}
        t={replay.t}
        playing={replay.playing}
        speed={replay.speed}
        buffering={phase === 'ready' && !replay.complete}
        progress={replay.progress}
        onSeek={replay.setT}
        onTogglePlay={replay.togglePlay}
        onCycleSpeed={replay.cycleSpeed}
        onReset={replay.reset}
      />
    </div>
  )
}

function Starting({ scale }: { scale: ScaleName }) {
  return (
    <div className="splash">
      <div className="inner">
        <div className="spin" />
        <h2>Running the {scale === 'tiny' ? 'tiny' : 'full six-region'} network</h2>
        <p>
          Building the service graph, injecting the faults and the decoys, and letting the
          engine watch the four-field stream. The run is deterministic from its seed, so it
          produces exactly the same story every time.
        </p>
      </div>
    </div>
  )
}

function Failed({ error, onRetry }: { error: string | null; onRetry: () => void }) {
  return (
    <div className="splash bad">
      <div className="inner">
        <Icon name="alert" style={{ width: 34, height: 34, color: 'var(--red)' }} />
        <h2>The run did not start</h2>
        <p>{error ?? 'Something went wrong.'}</p>
        <p style={{ marginTop: 10, color: 'var(--faint)' }}>
          The console needs the API. Start it with{' '}
          <span className="mono">uvicorn si_api.main:app --reload --app-dir backend</span>
        </p>
        <button type="button" className="retry" onClick={onRetry}>
          Try again
        </button>
      </div>
    </div>
  )
}