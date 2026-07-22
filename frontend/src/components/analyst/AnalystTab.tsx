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
  leadTime,
  num,
  pct,
  severityColor,
} from '../../lib/format'
import { Icon } from '../Icon'
import { layerLabelOf, shapeLabelOf, type T } from '../../lib/i18n'
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
  /** Named `tr`: `t` is already the interval. */
  tr: T
}

export function AnalystTab({
  model,
  alerts,
  selected,
  onSelect,
  t,
  frame,
  intervalSeconds,
  tr,
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
        tr={tr}
      />

      <main className="center col">
        {selected && alertStateAt(selected, t) === 'named' ? (
          <NamedVerdict alert={selected} t={t} intervalSeconds={intervalSeconds} tr={tr} />
        ) : (
          <Watching model={model} frame={frame} t={t} alerts={alerts} intervalSeconds={intervalSeconds} tr={tr} />
        )}
      </main>

      {selected && alertStateAt(selected, t) === 'named' ? (
        <Receipt panel={selected.panel} tr={tr} />
      ) : (
        <div className="right">
          <div className="rcol col">
            <section className="rsec">
              <div className="ct">
                <span className="ico">
                  <Icon name="receipt" />
                </span>
                {tr('receipt.emptyTitle')}
              </div>
              <p className="sub">{tr('receipt.empty')}</p>
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
  tr,
}: {
  model: ConsoleOut
  frame: StreamFrameOut | null
  t: number
  alerts: Alert[]
  intervalSeconds: number
  tr: T
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
            {forming.length > 0 ? tr('watch.formingTitle') : tr('watch.title')}
          </h2>
          <div className="headmeta" style={{ marginLeft: 0 }}>
            <span className="hm">
              <b className="mono">{frame?.n_core_records ?? 0}</b> {tr('watch.records')}
            </span>
            <span className="hm">
              {tr('watch.meanMagnitude')} <b className="mono">{num(frame?.mean_magnitude, 2)}</b>
            </span>
            <span className="hm">
              {tr('watch.peak')} <b className="mono">{num(frame?.max_magnitude, 2)}</b>
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
          {tr('watch.allowedToSee')}
        </div>
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 12.5, lineHeight: 1.6 }}>
          <span className="mono">entity_src</span>, <span className="mono">entity_dst</span>,{' '}
          <span className="mono">timestamp</span>, <span className="mono">magnitude</span>.{' '}
          {tr('watch.allowedToSee.body')}
          {next && (
            <>
              {' '}
              {forming.length > 0 ? tr('watch.drifting') : tr('watch.nothingYet')}{' '}
              {tr('watch.nextVerdict')} <b className="mono">{next.namedAt}</b> (
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
            {tr('watch.holdingFire')}
          </div>
          <div className="impact-grid">
            <div className="stat good">
              <div className="k">{tr('watch.decoysFired')}</div>
              <div className="v">
                {model.honest.n_decoys_fired}
                <small> / {model.honest.n_decoys}</small>
              </div>
            </div>
            <div className="stat good">
              <div className="k">{tr('watch.falsePositives')}</div>
              <div className="v">{pct(model.honest.false_positive_rate, 1)}</div>
            </div>
          </div>
          <p className="shape-note">
            {tr('watch.holdingFire.body')}
          </p>
        </div>

        <div className="card">
          <div className="ct">
            <span className="ico">
              <Icon name="alert" />
            </span>
            {tr('watch.formingNotNamed')}
          </div>
          {forming.length === 0 ? (
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 12 }}>
              {tr('watch.nothingForming')}
            </p>
          ) : (
            forming.map((alert) => (
              <div key={alert.id} className="mini-alert">
                <span className="md" style={{ background: 'var(--amber)' }} />
                <div>
                  <div className="mt">{alert.panel.region}</div>
                  <div className="me">
                    {tr('watch.beganAt')} {alert.onsetAt} · {tr('watch.namedAt')} {alert.namedAt}
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
  tr,
}: {
  alert: Alert
  t: number
  intervalSeconds: number
  tr: T
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
          {/* The heading names the element and what is wrong with it. The engine's full
              sentence is NOT repeated here - it is already the claim on the receipt in
              the right-hand panel, and printing it twice cost the header two lines it
              could not spare. The full text stays available as the heading's tooltip. */}
          <h2 title={panel.report.headline}>
            {panel.report.headline_short || panel.report.headline}
          </h2>

          <div className="headmeta">
            <span className="hm">
              {tr('verdict.element')} <b className="mono">{panel.entity}</b>
            </span>
            <span className="hm">
              {tr('verdict.layer')} <b>{layerLabelOf(panel.layer, tr)}</b>
            </span>
            <span className="hm">
              {tr('verdict.shape')} <b>{shapeLabelOf(panel.shape, tr)}</b>
            </span>
            <span className="hm">
              {tr('verdict.region')} <b>{panel.region}</b>
            </span>
            {score.mean_lead_time_minutes !== null && (
              <span className="hm lead">
                {tr('verdict.caught')} <b>{leadTime(score.mean_lead_time_minutes)}</b>{' '}
                {tr('verdict.beforeSurfacing')}
              </span>
            )}
            {diagnosis && (
              <span className="hm conf">
                {tr('verdict.confidence')} <b className="mono">{pct(diagnosis.confidence)}</b>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Two columns that both run to the transport bar, so their bottoms line up and
          no vertical space is left dead. The graph takes whatever the left column has
          left over after the narrative beneath it. */}
      <div className="verdict-grid">
        <div className="vcol">
          <div className="card shape-card">
            <div className="ct">
              <span className="ico">
                <Icon name="network" />
              </span>
              {tr('verdict.shapeOnGraph')}
            </div>
            <ShapeGraph tr={tr} panel={panel} progress={progress} named={t >= alert.namedAt} />
            <p className="shape-note">
            {panel.shape === 'single' ? (
              <>
                {tr('shapeNote.single.a')}{' '}
                <b>{panel.entity.split('-').slice(0, 2).join('-')}</b>{' '}
                {tr('shapeNote.single.b')}
              </>
            ) : panel.shape === 'cluster' ? (
              <>
                {tr('shapeNote.cluster.a')} {panel.affected.length}{' '}
                {tr('shapeNote.cluster.b')} <b>{panel.entity}</b>
                {tr('shapeNote.cluster.c')}
              </>
            ) : panel.shape === 'path' ? (
              <>
                {tr('shapeNote.path.a')} <b>{panel.entity}</b>
                {tr('shapeNote.path.b')}
              </>
            ) : (
              <>
                {tr('shapeNote.source.a')} <b>{panel.entity}</b>
                {tr('shapeNote.source.b')}
              </>
            )}
            </p>
          </div>

          {/* The four beats, moved out of a full-width strip and under the graph: they
              are the same argument the shape makes, read in order. */}
          <div className="card narrative-card">
            <div className="ct">
              <span className="ico">
                <Icon name="graph" />
              </span>
              {tr('verdict.detectionNarrative')}
            </div>
            <div className="beats">
              {panel.beats.map((beat, index) => (
                <div
                  key={beat.name}
                  className={`beat${
                    index === activeBeat ? ' on' : index < activeBeat ? ' done' : ''
                  }`}
                >
                  <div className="n">0{index + 1}</div>
                  <h4>{beat.name}</h4>
                  <p title={beat.text}>{beat.text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="vcol">
          <div className="card call-card">
            <div className="ct">
              <span className="ico">
                <Icon name="target" />
              </span>
              {tr('verdict.theCall')}
            </div>

            <div className="shi-flex">
              <Gauge value={diagnosis?.confidence ?? 0} color={severityColor(alert.severity)} tr={tr} />
              <div className="shi-info">
                <h4>{panel.entity}</h4>
                <span
                  className={`shi-band ${bandClass(panel.report.health_band)}`}
                  title={panel.report.health_band}
                >
                  {panel.report.health_band_short || panel.report.health_band}
                </span>
                <p>
                  {tr('verdict.namedAt')} <b className="mono">{alert.namedAt}</b> (
                  {clockAt(alert.namedAt, intervalSeconds)})
                  {alert.onsetAt !== null && (
                    <>
                      {tr('verdict.formingSince')}{' '}
                      <b className="mono">{alert.onsetAt}</b> {tr('verdict.notSurfaced')}
                    </>
                  )}
                </p>
                {diagnosis?.trajectory && (
                  <div className="traj">
                    <Icon name="alert" style={{ width: 14, height: 14 }} />
                    <span>
                      {diagnosis.trajectory.rising ? tr('verdict.rising') : tr('verdict.stable')} —{' '}
                      {diagnosis.trajectory.detail}
                      {diagnosis.trajectory.horizon_interval !== null && (
                        <>
                          {tr('verdict.onThisTrend')}{' '}
                          <span className="mono">{diagnosis.trajectory.horizon_interval}</span>
                        </>
                      )}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="card measured-card">
            <div className="ct">
              <span className="ico">
                <Icon name="graph" />
              </span>
              {tr('measured.title')}
            </div>
            <div className="impact-grid">
              <div className="stat hot">
                <div className="k">{tr('measured.homesAffected')}</div>
                <div className="v">{panel.affected.length}</div>
              </div>
              <div className="stat good">
                <div className="k">{tr('measured.leadTime')}</div>
                <div className="v">{leadTime(score.mean_lead_time_minutes)}</div>
              </div>
              <div className="stat good">
                <div className="k">{tr('measured.localization')}</div>
                <div className="v">{pct(score.localization_accuracy)}</div>
              </div>
              <div className="stat good">
                <div className="k">{tr('measured.layerAttribution')}</div>
                <div className="v">{pct(score.layer_attribution_accuracy)}</div>
              </div>
            </div>
            {score.box_swap_discrimination !== null && (
              <p className="shape-note">
                <b>
                  {tr('measured.boxSwap')} {pct(score.box_swap_discrimination)}.
                </b>{' '}
                {tr('measured.boxSwap.body')}
              </p>
            )}
          </div>
        </div>
      </div>

    </>
  )
}

/** The confidence dial. */
function Gauge({ value, color, tr }: { value: number; color: string; tr: T }) {
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
        <small>{tr('gauge.confidence')}</small>
      </div>
    </div>
  )
}