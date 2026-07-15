/**
 * The analyst's screen: one verdict, in full.
 *
 * Left, the queue of what is forming and what has been named. Centre, the four-beat
 * narrative and the shape the engine read. Right, the receipt and the action.
 *
 * The centre column is the argument in order: what the engine streamed, the shape that
 * formed, where it projected it, what it prescribes. The beats light up as the run
 * reaches them, so the story is told by the timeline rather than asserted all at once.
 */

import type { ConsoleOut, StreamFrameOut } from '../../api/types'
import { alertStateAt, formationProgress, type Alert } from '../../lib/alerts'
import {
  bandClass,
  clockAt,
  layerLabel,
  leadTime,
  num,
  pct,
  SHAPE_LABEL,
  severityColor,
} from '../../lib/format'
import { Icon } from '../Icon'
import { AlertQueue } from './AlertQueue'
import { Receipt } from './Receipt'
import { ShapeGraph } from './ShapeGraph'

interface AnalystTabProps {
  model: ConsoleOut
  alerts: Alert[]
  selected: Alert | null
  onSelect: (useCase: string) => void
  t: number
  frame: StreamFrameOut | null
  intervalSeconds: number
}

export function AnalystTab({
  model,
  alerts,
  selected,
  onSelect,
  t,
  frame,
  intervalSeconds,
}: AnalystTabProps) {
  return (
    <div className="analyst">
      <AlertQueue
        model={model}
        alerts={alerts}
        t={t}
        intervalSeconds={intervalSeconds}
        selected={selected?.useCase ?? null}
        onSelect={onSelect}
      />

      <main className="center col">
        {selected && alertStateAt(selected, t) === 'named' ? (
          <NamedVerdict alert={selected} t={t} intervalSeconds={intervalSeconds} />
        ) : (
          <Watching model={model} frame={frame} t={t} alerts={alerts} intervalSeconds={intervalSeconds} />
        )}
      </main>

      {selected && alertStateAt(selected, t) === 'named' ? (
        <Receipt panel={selected.panel} />
      ) : (
        <div className="right">
          <div className="rcol col">
            <section className="rsec">
              <div className="ct">
                <span className="ico">
                  <Icon name="receipt" />
                </span>
                Certified-decision receipt
              </div>
              <p className="sub">
                A receipt is written when — and only when — the engine names an element. Until
                then there is nothing to certify, and the panel stays empty rather than
                filling with a guess.
              </p>
            </section>
          </div>
        </div>
      )}
    </div>
  )
}

/** Before anything is named: what the engine is reading, and what it is holding back on. */
function Watching({
  model,
  frame,
  t,
  alerts,
  intervalSeconds,
}: {
  model: ConsoleOut
  frame: StreamFrameOut | null
  t: number
  alerts: Alert[]
  intervalSeconds: number
}) {
  const forming = alerts.filter((alert) => alertStateAt(alert, t) === 'forming')
  const next = alerts
    .filter((alert) => t < alert.namedAt)
    .sort((a, b) => a.namedAt - b.namedAt)[0]

  return (
    <>
      <div className="alert-head">
        <span className="pulse" style={{ background: forming.length ? undefined : 'var(--cyan)' }} />
        <div>
          <h2>
            {forming.length > 0
              ? 'A shape is forming — the engine has not yet resolved it'
              : 'Watching the network'}
          </h2>
          <div className="headmeta" style={{ marginLeft: 0 }}>
            <span className="hm">
              <b className="mono">{frame?.n_core_records ?? 0}</b> four-field records this
              interval
            </span>
            <span className="hm">
              mean magnitude <b className="mono">{num(frame?.mean_magnitude, 2)}</b>
            </span>
            <span className="hm">
              peak <b className="mono">{num(frame?.max_magnitude, 2)}</b>
            </span>
            <span className="hm">
              <b className="mono">{clockAt(t, intervalSeconds)}</b>
            </span>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="ct">
          <span className="ico">
            <Icon name="eye" />
          </span>
          What the engine is allowed to see
        </div>
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 12.5, lineHeight: 1.6 }}>
          Four fields per record — <span className="mono">entity_src</span>,{' '}
          <span className="mono">entity_dst</span>, <span className="mono">timestamp</span>,{' '}
          <span className="mono">magnitude</span>. No error codes, no alarms, no labels. It
          learns each edge's own baseline from the history it observes, and watches the graph
          for structure.
          {next && (
            <>
              {' '}
              {forming.length > 0
                ? 'Something is drifting above baseline right now, but it has not cleared the dwell gate — so nothing is claimed.'
                : 'Nothing has departed from baseline yet.'}{' '}
              The next verdict lands at interval <b className="mono">{next.namedAt}</b> (
              {clockAt(next.namedAt, intervalSeconds)}).
            </>
          )}
        </p>
      </div>

      <div className="grid2">
        <div className="card">
          <div className="ct">
            <span className="ico">
              <Icon name="shield" />
            </span>
            Holding fire
          </div>
          <div className="impact-grid">
            <div className="stat good">
              <div className="k">Decoys fired</div>
              <div className="v">
                {model.honest.n_decoys_fired}
                <small> / {model.honest.n_decoys}</small>
              </div>
            </div>
            <div className="stat good">
              <div className="k">False positives</div>
              <div className="v">{pct(model.honest.false_positive_rate, 1)}</div>
            </div>
          </div>
          <p className="shape-note">
            Benign disturbances — a prime-time surge, a one-off glitch, a reboot — are injected
            deliberately. An engine that fired on them would be useless in an operations room,
            so what it <b>ignores</b> is measured just as carefully as what it catches.
          </p>
        </div>

        <div className="card">
          <div className="ct">
            <span className="ico">
              <Icon name="alert" />
            </span>
            Forming, not yet named
          </div>
          {forming.length === 0 ? (
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 12 }}>
              Nothing is forming at this interval.
            </p>
          ) : (
            forming.map((alert) => (
              <div key={alert.useCase} className="mini-alert">
                <span className="md" style={{ background: 'var(--amber)' }} />
                <div>
                  <div className="mt">{alert.panel.region}</div>
                  <div className="me">
                    began at interval {alert.onsetAt} · named at {alert.namedAt}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  )
}

/** After the call: the verdict, the beats, the shape, and what it costs. */
function NamedVerdict({
  alert,
  t,
  intervalSeconds,
}: {
  alert: Alert
  t: number
  intervalSeconds: number
}) {
  const { panel } = alert
  const diagnosis = panel.report.diagnosis
  const score = panel.score
  const progress = formationProgress(alert, t)

  // The beat the run has reached. Before the call the engine is streaming and watching a
  // shape form; the call itself is the predict-and-prescribe moment.
  const sinceNamed = t - alert.namedAt
  const activeBeat = sinceNamed <= 0 ? 1 : sinceNamed < 3 ? 2 : 3

  return (
    <>
      <div className="alert-head">
        <span className={`pulse${alert.severity === 'warn' ? ' warn' : ''}`} />
        <div>
          <h2>{panel.report.headline}</h2>

          <div className="headmeta">
            <span className="hm">
              element <b className="mono">{panel.entity}</b>
            </span>
            <span className="hm">
              layer <b>{layerLabel(panel.layer)}</b>
            </span>
            <span className="hm">
              shape <b>{SHAPE_LABEL[panel.shape]}</b>
            </span>
            <span className="hm">
              region <b>{panel.region}</b>
            </span>
            {score.mean_lead_time_minutes !== null && (
              <span className="hm lead">
                caught <b>{leadTime(score.mean_lead_time_minutes)}</b> before it would surface
              </span>
            )}
            {diagnosis && (
              <span className="hm conf">
                confidence <b className="mono">{pct(diagnosis.confidence)}</b>
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="grid2">
        <div className="card">
          <div className="ct">
            <span className="ico">
              <Icon name="network" />
            </span>
            The shape on the graph
          </div>
          <ShapeGraph panel={panel} progress={progress} named={t >= alert.namedAt} />
          <p className="shape-note">
            {panel.shape === 'single' ? (
              <>
                One home is impaired while every peer on <b>{panel.entity.split('-').slice(0, 2).join('-')}</b>{' '}
                stays at baseline. Isolation is the attribution: the fault is inside this
                household, so the fix is a call and a reconfiguration — not a truck.
              </>
            ) : panel.shape === 'cluster' ? (
              <>
                All {panel.affected.length} impaired homes sit behind <b>{panel.entity}</b>. A
                shared parent is the attribution: the fault lives at the access node, not in
                any one home.
              </>
            ) : panel.shape === 'path' ? (
              <>
                The impairment runs along a route through <b>{panel.entity}</b>, crossing homes
                that share nothing else. That is a core-transport signature.
              </>
            ) : (
              <>
                Homes with no network parent in common degrade together behind{' '}
                <b>{panel.entity}</b>. Only a shared content source explains that.
              </>
            )}
          </p>
        </div>

        <div>
          <div className="card">
            <div className="ct">
              <span className="ico">
                <Icon name="target" />
              </span>
              The call
            </div>

            <div className="shi-flex">
              <Gauge value={diagnosis?.confidence ?? 0} color={severityColor(alert.severity)} />
              <div className="shi-info">
                <h4>{panel.entity}</h4>
                <span className={`shi-band ${bandClass(panel.report.health_band)}`}>
                  {panel.report.health_band}
                </span>
                <p>
                  Named at interval <b className="mono">{alert.namedAt}</b> (
                  {clockAt(alert.namedAt, intervalSeconds)})
                  {alert.onsetAt !== null && (
                    <>
                      , while the fault had been forming since{' '}
                      <b className="mono">{alert.onsetAt}</b> and had not yet surfaced to a
                      single customer.
                    </>
                  )}
                </p>
                {diagnosis?.trajectory && (
                  <div className="traj">
                    <Icon name="alert" style={{ width: 14, height: 14 }} />
                    <span>
                      {diagnosis.trajectory.rising ? 'Rising' : 'Stable'} —{' '}
                      {diagnosis.trajectory.detail}
                      {diagnosis.trajectory.horizon_interval !== null && (
                        <>
                          ; on this trend it would broaden around interval{' '}
                          <span className="mono">{diagnosis.trajectory.horizon_interval}</span>
                        </>
                      )}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 14 }}>
            <div className="ct">
              <span className="ico">
                <Icon name="graph" />
              </span>
              Measured against ground truth
            </div>
            <div className="impact-grid">
              <div className="stat hot">
                <div className="k">Homes affected</div>
                <div className="v">{panel.affected.length}</div>
              </div>
              <div className="stat good">
                <div className="k">Lead time</div>
                <div className="v">{leadTime(score.mean_lead_time_minutes)}</div>
              </div>
              <div className="stat good">
                <div className="k">Localization</div>
                <div className="v">{pct(score.localization_accuracy)}</div>
              </div>
              <div className="stat good">
                <div className="k">Layer attribution</div>
                <div className="v">{pct(score.layer_attribution_accuracy)}</div>
              </div>
            </div>
            {score.box_swap_discrimination !== null && (
              <p className="shape-note">
                <b>Box-swap discrimination {pct(score.box_swap_discrimination)}.</b> The
                signature survives a set-top-box replacement, so the box is exonerated and the
                futile swap is avoided.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* The four beats: stream, form, predict, prescribe. */}
      <div className="beats" style={{ marginTop: 18 }}>
        {panel.beats.map((beat, index) => (
          <div
            key={beat.name}
            className={`beat${index === activeBeat ? ' on' : index < activeBeat ? ' done' : ''}`}
          >
            <div className="n">0{index + 1}</div>
            <h4>{beat.name}</h4>
            <p>{beat.text}</p>
          </div>
        ))}
      </div>
    </>
  )
}

/** The confidence dial. */
function Gauge({ value, color }: { value: number; color: string }) {
  const radius = 50
  const circumference = 2 * Math.PI * radius
  const filled = circumference * value

  return (
    <div className="gauge">
      <svg viewBox="0 0 118 118" width="118" height="118">
        <circle cx="59" cy="59" r={radius} fill="none" stroke="#0c2135" strokeWidth="9" />
        <circle
          cx="59"
          cy="59"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference - filled}`}
          transform="rotate(-90 59 59)"
          style={{ transition: 'stroke-dasharray .5s' }}
        />
      </svg>
      <div className="num">
        <b style={{ color }}>{Math.round(value * 100)}</b>
        <small>confidence</small>
      </div>
    </div>
  )
}