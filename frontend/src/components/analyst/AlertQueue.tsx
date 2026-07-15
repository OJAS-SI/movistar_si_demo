/**
 * The left rail: what the engine is currently saying, and what it is refusing to say.
 *
 * The queue only shows an alert once the engine has actually named it. Before that the
 * card appears dimmed and dashed while the shape is still forming - present, but not
 * yet a claim. That distinction is the demo's honesty in miniature, and it is why the
 * honest instruments (the abstention, the decoys that held, the false-positive rate)
 * sit in the same rail rather than being tucked away on another screen.
 */

import type { ConsoleOut } from '../../api/types'
import { alertStateAt, type Alert } from '../../lib/alerts'
import { clockAt, layerLabel, pct, severityColor } from '../../lib/format'
import { Icon, ShapeGlyph } from '../Icon'

interface AlertQueueProps {
  model: ConsoleOut
  alerts: Alert[]
  t: number
  intervalSeconds: number
  selected: string | null
  onSelect: (useCase: string) => void
}

export function AlertQueue({
  model,
  alerts,
  t,
  intervalSeconds,
  selected,
  onSelect,
}: AlertQueueProps) {
  const visible = alerts.filter((alert) => alertStateAt(alert, t) !== 'quiet')
  const named = visible.filter((alert) => alertStateAt(alert, t) === 'named')
  const { honest } = model

  return (
    <aside className="rail col">
      <div className="rail-head">
        <h2>Active alerts</h2>
        <span className={`count-pill${named.length === 0 ? ' zero' : ''}`}>
          {named.length}
        </span>
      </div>

      {visible.length === 0 ? (
        <p className="empty-q">
          Nothing is forming yet. The engine is watching{' '}
          <span className="mono">{model.config_summary.split(',')[0]}</span> and learning
          what normal looks like.
        </p>
      ) : (
        <div className="queue">
          {visible.map((alert) => {
            const state = alertStateAt(alert, t)
            const isNamed = state === 'named'
            const { panel } = alert
            const confidence = panel.report.diagnosis?.confidence ?? 0

            return (
              <button
                key={alert.useCase}
                type="button"
                className={[
                  'qcard',
                  selected === alert.useCase && isNamed ? 'active' : '',
                  isNamed ? '' : 'forming',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onClick={() => isNamed && onSelect(alert.useCase)}
                aria-pressed={selected === alert.useCase}
                title={
                  isNamed
                    ? panel.report.headline
                    : 'A shape is forming here. The engine has not yet resolved it to an element.'
                }
              >
                <span className={`sev sev-${alert.severity}`} />

                <div className="qrow1">
                  <span className="shape-badge">
                    <ShapeGlyph shape={panel.shape} />
                  </span>
                  <span className="qtitle">
                    {isNamed ? panel.title : 'Shape forming — not yet resolved'}
                  </span>
                </div>

                <div className="qmeta">
                  <span className="chip">
                    <b>{isNamed ? panel.entity : '—'}</b>
                  </span>
                  <span className="chip layer">{layerLabel(isNamed ? panel.layer : null)}</span>
                  <span className="chip">{panel.region}</span>
                  {isNamed && (
                    <span className="chip">
                      <b>{alert.nAffected}</b> home{alert.nAffected === 1 ? '' : 's'}
                    </span>
                  )}
                </div>

                {isNamed ? (
                  <div className="qshi">
                    <span className="shibar">
                      <i
                        style={{
                          width: `${Math.round(confidence * 100)}%`,
                          background: severityColor(alert.severity),
                        }}
                      />
                    </span>
                    <span className="val" style={{ color: severityColor(alert.severity) }}>
                      {pct(confidence)}
                    </span>
                  </div>
                ) : (
                  <div className="qshi">
                    <span className="val" style={{ color: 'var(--faint)' }}>
                      began {clockAt(alert.onsetAt ?? t, intervalSeconds)} · below the dwell gate
                    </span>
                  </div>
                )}
              </button>
            )
          })}
        </div>
      )}

      {/* The competence boundary: the engine declining to guess. */}
      {honest.abstention && (
        <div className="abstain">
          <h3>Competence boundary</h3>
          <p>{honest.abstention.headline}</p>
          <div className="at">
            abstained at interval {honest.abstention.timestamp} ·{' '}
            {clockAt(honest.abstention.timestamp, intervalSeconds)}
          </div>
        </div>
      )}

      {/* What did not happen, which is the harder thing to show. */}
      <div className="honesty">
        <h3>Honest instruments</h3>
        <div className="h-sub">
          Measured over the whole run, against ground truth the engine never sees.
        </div>

        <div className="hrow">
          <Icon name="shield" className="tick ok" />
          <span className="h-lbl">Decoys that fired</span>
          <span className={`h-val ${honest.n_decoys_fired === 0 ? 'ok' : 'warnc'}`}>
            {honest.n_decoys_fired} / {honest.n_decoys}
          </span>
        </div>

        <div className="hrow">
          <Icon name="check" className="tick ok" />
          <span className="h-lbl">False-positive rate</span>
          <span className={`h-val ${honest.false_positive_rate === 0 ? 'ok' : 'warnc'}`}>
            {pct(honest.false_positive_rate, 1)}
          </span>
        </div>

        <div className="hrow">
          <Icon name="eye" className="tick" />
          <span className="h-lbl">Quiet intervals watched</span>
          <span className="h-val">{honest.n_non_fault_intervals}</span>
        </div>
      </div>
    </aside>
  )
}