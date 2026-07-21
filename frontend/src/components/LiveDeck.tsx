/**
 * The live deck: what the operator sees the instant a run starts, before the full
 * console has finished computing.
 *
 * There is no waiting screen here. The engine is already watching the four-field stream
 * interval by interval, and every fault it names is piped straight onto this deck as it
 * happens. The rich analyst view - the settled receipts, the scorecard measured against
 * ground truth - takes over the moment the run finishes; until then, this is the honest
 * live picture, and it is never blank for more than the first interval.
 */

import { layerLabelOf, type T } from '../lib/i18n'
import type { StreamFrameOut } from '../api/types'
import type { LiveFault } from '../lib/alerts'
import { clockAt, LAYER_COLOR, num, pct } from '../lib/format'
import { Icon, ShapeGlyph } from './Icon'

interface LiveDeckProps {
  live: LiveFault[]
  frame: StreamFrameOut | null
  t: number
  totalIntervals: number
  intervalSeconds: number
  progress: number
  tr: T
}

export function LiveDeck({
  live,
  frame,
  t,
  totalIntervals,
  intervalSeconds,
  progress,
  tr,
}: LiveDeckProps) {
  const pctDone = Math.round(progress * 100)

  return (
    <div className="livedeck">
      <div className="alert-head">
        <span className="pulse" />
        <div>
          <h2>{tr('live.watching')}</h2>
          <div className="headmeta" style={{ marginLeft: 0 }}>
            <span className="hm">
              <b className="mono">{live.length}</b> named so far
            </span>
            <span className="hm">
              interval <b className="mono">{t}</b> / {totalIntervals - 1}
            </span>
            <span className="hm">
              <b className="mono">{clockAt(t, intervalSeconds)}</b>
            </span>
            <span className="hm">
              <b className="mono">{frame?.n_core_records ?? 0}</b> four-field records this interval
            </span>
          </div>
        </div>
      </div>

      {/* How much of the run the engine has computed so far. */}
      <div className="live-progress" role="progressbar" aria-valuenow={pctDone}>
        <i style={{ width: `${pctDone}%` }} />
        <span className="live-progress-label">
          computing the full picture · <b className="mono">{pctDone}%</b>
        </span>
      </div>

      {live.length === 0 ? (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="ct">
            <span className="ico">
              <Icon name="eye" />
            </span>
            Learning what normal looks like
          </div>
          <p style={{ margin: 0, color: 'var(--muted)', fontSize: 12.5, lineHeight: 1.6 }}>
            The engine is establishing each edge's baseline from the four-field stream. Nothing
            has cleared the dwell gate yet — the first named fault will appear here the interval
            it does, and the rest will follow as the run computes.
          </p>
        </div>
      ) : (
        <div className="live-grid">
          {live.map((fault) => {
            const color = fault.layer ? LAYER_COLOR[fault.layer] : 'var(--cyan)'
            return (
              <div className="live-card" key={fault.entity}>
                <span className="live-accent" style={{ background: color }} />
                <div className="qrow1">
                  <span className="shape-badge">
                    <ShapeGlyph shape={fault.shape} />
                  </span>
                  <span className="qtitle mono">{fault.entity}</span>
                </div>
                <div className="qmeta">
                  <span className="chip layer">{layerLabelOf(fault.layer, tr)}</span>
                  <span className="chip">
                    named <b className="mono">{clockAt(fault.firstSeen, intervalSeconds)}</b>
                  </span>
                  {fault.nAffected > 0 && (
                    <span className="chip">
                      <b>{fault.nAffected}</b> home{fault.nAffected === 1 ? '' : 's'}
                    </span>
                  )}
                </div>
                {fault.claim && <p className="live-claim">{fault.claim}</p>}
                <div className="qshi">
                  <span className="shibar">
                    <i style={{ width: `${Math.round(fault.confidence * 100)}%`, background: color }} />
                  </span>
                  <span className="val" style={{ color }}>
                    {pct(fault.confidence)}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <p className="live-foot">
        The full analyst view — the four-beat narrative, the certified receipts, and the
        scorecard measured against ground truth — opens automatically once the run finishes
        computing. Mean magnitude this interval{' '}
        <b className="mono">{num(frame?.mean_magnitude, 2)}</b>.
      </p>
    </div>
  )
}