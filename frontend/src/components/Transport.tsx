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
 * Amber marks are the injected decoys, labelled "benign transient" in the legend rather
 * than "decoy": to an operator the ribbon reads as severity, where amber is a milder
 * red, so naming these by what they ARE - not a fault - beats naming them by the role
 * they play in the test harness. They never earn a green mark, which is what the
 * false-positive rate is counting.
 */

import { useCallback, useMemo, useRef, useState } from 'react'
import type { StreamFrameOut } from '../api/types'
import type { Alert } from '../lib/alerts'
import type { Onset, Speed } from '../hooks/useReplay'
import { C, clockAt } from '../lib/format'
import type { T } from '../lib/i18n'
import { Icon } from './Icon'

/** Half the tooltip's max width, for keeping it inside the bar at either end. */
const TIP_HALF = 190

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
  /** Named `tr`, not `t`: `t` is already the interval this bar is showing. */
  tr: T
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
  tr,
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

  // The marks explain themselves on hover, and the bar sits at the bottom of the screen,
  // so a native `title` would open downwards into nothing. This renders the same text
  // upwards instead, anchored over whatever is hovered and clamped inside the bar.
  const barRef = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<{ text: string; x: number } | null>(null)

  const showTip = useCallback(
    (text: string) => (event: { currentTarget: EventTarget | null }) => {
      const bar = barRef.current
      const target = event.currentTarget as HTMLElement | null
      if (!bar || !target) return
      const mark = target.getBoundingClientRect()
      const bounds = bar.getBoundingClientRect()
      const centre = mark.left + mark.width / 2 - bounds.left
      const limit = Math.max(TIP_HALF + 8, bounds.width - TIP_HALF - 8)
      setTip({ text, x: Math.min(Math.max(centre, TIP_HALF + 8), limit) })
    },
    [],
  )
  const hideTip = useCallback(() => setTip(null), [])

  /** Everything a hoverable mark needs: point at it, and it explains itself. */
  const tipProps = (text: string) => ({
    onMouseEnter: showTip(text),
    onFocus: showTip(text),
    onMouseLeave: hideTip,
    onBlur: hideTip,
    'aria-label': text,
    tabIndex: 0,
  })

  return (
    <div className="transport" ref={barRef}>
      {tip && (
        <div className="evtip" role="tooltip" style={{ left: tip.x }}>
          {tip.text}
        </div>
      )}
      <button
        type="button"
        className="play"
        onClick={onTogglePlay}
        disabled={frames.length === 0}
        title={playing ? tr('transport.pause') : tr('transport.play')}
        aria-label={playing ? tr('transport.pause') : tr('transport.play')}
      >
        <Icon name={playing ? 'pause' : 'play'} />
      </button>

      <button
        type="button"
        className="tbtn"
        onClick={onReset}
        disabled={frames.length === 0}
        title={tr('transport.reset')}
        aria-label={tr('transport.reset')}
      >
        ⏮
      </button>

      <button
        type="button"
        className="tbtn speed"
        onClick={onCycleSpeed}
        disabled={frames.length === 0}
        title={tr('transport.speed')}
      >
        {speed}×
      </button>

      {buffering ? (
        <div className="buffering">
          <span>{tr('transport.computing')}</span>
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
                {...tipProps(
                  onset.decoy
                    ? `${tr('mark.benign')}: ${onset.faultId} ${tr('mark.benign.body')} ` +
                      `${onset.interval}, ${clockAt(onset.interval, intervalSeconds)}. ` +
                      tr('mark.benign.tail')
                    : `${tr('mark.faultOnset')}: ${onset.faultId} ` +
                      `${tr('mark.faultOnset.body')} ${onset.interval}, ` +
                      `${clockAt(onset.interval, intervalSeconds)}. ` +
                      tr('mark.faultOnset.tail'),
                )}
              />
            ))}

            {/* where the engine named the element */}
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="ev"
                style={{ left: at(alert.namedAt), background: C.green }}
                {...tipProps(
                  `${tr('mark.named')} ${alert.panel.entity} ${tr('mark.named.body')} ` +
                    `${alert.namedAt}, ${clockAt(alert.namedAt, intervalSeconds)}` +
                    (alert.onsetAt !== null
                      ? `, ${alert.namedAt - alert.onsetAt} ${tr('mark.named.tail')}`
                      : '.'),
                )}
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
          {tr('transport.interval')} <span className="now mono">{t}</span>
          <span className="mono"> / {totalIntervals - 1}</span>
        </span>
        <span>
          <span className="clock mono">{clockAt(t, intervalSeconds)}</span>
        </span>
      </div>

      {/* The key is also the explanation: each entry says what the mark proves, because
          the whole demo is read off the relationship between the three. */}
      <div className="evkey">
        <span
          {...tipProps(tr('legend.faultOnset.tip'))}
        >
          <i style={{ background: C.red }} />
          {tr('legend.faultOnset')}
        </span>
        <span
          {...tipProps(tr('legend.benignTransient.tip'))}
        >
          <i style={{ background: C.amber }} />
          {tr('legend.benignTransient')}
        </span>
        <span
          {...tipProps(tr('legend.engineNames.tip'))}
        >
          <i style={{ background: C.green }} />
          {tr('legend.engineNames')}
        </span>
      </div>
    </div>
  )
}