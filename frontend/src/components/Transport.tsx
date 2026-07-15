/**
 * The transport bar: the run on a timeline.
 *
 * The ribbon carries three things at once, and their relationship is the whole demo:
 *
 *   the trace   mean magnitude per interval - literally the four-field stream, the only
 *               thing the engine is allowed to read.
 *   red marks   where a fault truly began (ground truth).
 *   green marks where the engine named the element responsible.
 *
 * A green mark sitting to the *right* of a red one, by a visible gap, is the lead time.
 * Amber marks are decoys: benign disturbances that never earn a green mark, which is
 * what the false-positive rate is counting.
 */

import { useMemo } from 'react'
import type { StreamFrameOut } from '../api/types'
import type { Alert } from '../lib/alerts'
import type { Onset, Speed } from '../hooks/useReplay'
import { C, clockAt } from '../lib/format'
import { Icon } from './Icon'

interface TransportProps {
  frames: StreamFrameOut[]
  totalIntervals: number
  intervalSeconds: number
  alerts: Alert[]
  onsets: Onset[]
  t: number
  playing: boolean
  speed: Speed
  buffering: boolean
  progress: number
  onSeek: (t: number) => void
  onTogglePlay: () => void
  onCycleSpeed: () => void
  onReset: () => void
}

export function Transport({
  frames,
  totalIntervals,
  intervalSeconds,
  alerts,
  onsets,
  t,
  playing,
  speed,
  buffering,
  progress,
  onSeek,
  onTogglePlay,
  onCycleSpeed,
  onReset,
}: TransportProps) {
  const lastIndex = Math.max(0, frames.length - 1)
  const span = Math.max(1, totalIntervals - 1)
  const at = (interval: number) => `${(interval / span) * 100}%`

  // The magnitude trace, normalised over the run so the ramp is visible at any scale.
  const trace = useMemo(() => {
    if (frames.length < 2) return ''
    const values = frames.map((frame) => frame.mean_magnitude)
    const low = Math.min(...values)
    const high = Math.max(...values)
    const range = high - low || 1
    return values
      .map((value, index) => {
        const x = (index / span) * 100
        const y = 100 - ((value - low) / range) * 88 - 6 // keep it off the edges
        return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
      })
      .join(' ')
  }, [frames, span])

  return (
    <div className="transport">
      <button
        type="button"
        className="play"
        onClick={onTogglePlay}
        disabled={frames.length === 0}
        title={playing ? 'Pause' : 'Play the run'}
        aria-label={playing ? 'Pause' : 'Play'}
      >
        <Icon name={playing ? 'pause' : 'play'} />
      </button>

      <button
        type="button"
        className="tbtn"
        onClick={onReset}
        disabled={frames.length === 0}
        title="Back to the first interval"
        aria-label="Reset to start"
      >
        ⏮
      </button>

      <button
        type="button"
        className="tbtn speed"
        onClick={onCycleSpeed}
        disabled={frames.length === 0}
        title="Playback speed"
      >
        {speed}×
      </button>

      {buffering ? (
        <div className="buffering">
          <span>Computing the run…</span>
          <span className="bar">
            <i style={{ width: `${Math.round(progress * 100)}%` }} />
          </span>
          <span className="mono">{Math.round(progress * 100)}%</span>
        </div>
      ) : (
        <div className="tline">
          <div className="ribbon" id="ribbon">
            {/* what the engine reads */}
            <svg
              className="trace"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <path d={trace} fill="none" stroke="#2a557c" strokeWidth="1.4" vectorEffect="non-scaling-stroke" />
            </svg>

            <div className="fill" style={{ width: at(t) }} />

            {/* where each fault truly began, and where a decoy tried to look like one */}
            {onsets.map((onset) => (
              <div
                key={`${onset.faultId}-${onset.interval}`}
                className="ev"
                style={{
                  left: at(onset.interval),
                  background: onset.decoy ? C.amber : C.red,
                  opacity: onset.decoy ? 0.75 : 1,
                }}
                title={
                  onset.decoy
                    ? `Decoy ${onset.faultId} begins at interval ${onset.interval} — the engine must not fire`
                    : `Fault ${onset.faultId} begins at interval ${onset.interval}`
                }
              />
            ))}

            {/* where the engine named the element */}
            {alerts.map((alert) => (
              <div
                key={alert.useCase}
                className="ev"
                style={{ left: at(alert.namedAt), background: C.green }}
                title={`Engine named ${alert.panel.entity} at interval ${alert.namedAt}`}
              />
            ))}
          </div>

          <input
            className="scrub"
            type="range"
            min={0}
            max={lastIndex}
            value={Math.min(t, lastIndex)}
            onChange={(event) => onSeek(Number(event.target.value))}
            aria-label="Timeline scrubber"
          />
        </div>
      )}

      <div className="tmeta">
        <span>
          Interval <span className="now mono">{t}</span>
          <span className="mono"> / {totalIntervals - 1}</span>
        </span>
        <span>
          <span className="clock mono">{clockAt(t, intervalSeconds)}</span>
        </span>
      </div>

      <div className="evkey">
        <span>
          <i style={{ background: C.red }} />
          fault onset
        </span>
        <span>
          <i style={{ background: C.amber }} />
          decoy
        </span>
        <span>
          <i style={{ background: C.green }} />
          engine names it
        </span>
      </div>
    </div>
  )
}