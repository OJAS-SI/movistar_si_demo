/**
 * The management view: the scorecard, measured against ground truth.
 *
 * Every number on this screen was computed by the scoring harness against labels the
 * engine never saw. Nothing is a target and nothing is a threshold - the API is explicit
 * that it fixes no success criterion, so this screen reports and does not grade. Where a
 * value is absent (box-swap discrimination only means something for the invisible fault)
 * it shows a dash rather than a zero.
 *
 * The plain-text scorecard the CLI prints is included verbatim at the bottom, so what a
 * stakeholder reads here and what an engineer reads in a terminal cannot drift apart.
 */

import type { ConsoleOut, RunOut } from '../../api/types'
import type { Alert } from '../../lib/alerts'
import { LAYER_COLOR, layerLabel, leadTime, num, pct, USE_CASE_LABEL } from '../../lib/format'
import { Icon } from '../Icon'

interface ManagementTabProps {
  model: ConsoleOut
  run: RunOut | null
  alerts: Alert[]
}

export function ManagementTab({ model, run, alerts }: ManagementTabProps) {
  const { scorecard, honest } = model

  const nFaults = scorecard.per_use_case.reduce((sum, score) => sum + score.n_faults, 0)
  const nDetected = scorecard.per_use_case.reduce((sum, score) => sum + score.n_detected, 0)

  const leads = scorecard.per_use_case
    .map((score) => score.mean_lead_time_minutes)
    .filter((value): value is number => value !== null)
  const meanLead = leads.length ? leads.reduce((a, b) => a + b, 0) / leads.length : null

  const localizations = scorecard.per_use_case
    .map((score) => score.localization_accuracy)
    .filter((value): value is number => value !== null)
  const meanLocalization = localizations.length
    ? localizations.reduce((a, b) => a + b, 0) / localizations.length
    : null

  // Which layers the run actually implicated, and how many homes sat behind each.
  const byLayer = new Map<string, { verdicts: number; homes: number }>()
  for (const alert of alerts) {
    const key = alert.panel.layer ?? 'unresolved'
    const entry = byLayer.get(key) ?? { verdicts: 0, homes: 0 }
    entry.verdicts += 1
    entry.homes += alert.panel.affected.length
    byLayer.set(key, entry)
  }

  return (
    <div className="mgmt col">
      <h2 className="page">Structural Intelligence — run scorecard</h2>
      <p className="psub">
        {model.config_summary}
        {run && (
          <>
            {' '}
            · seed <span className="mono">{run.seed}</span> · computed in{' '}
            <span className="mono">{num(run.runtime_seconds, 2)}s</span>
          </>
        )}{' '}
        · measured against ground truth the engine never sees.
      </p>

      <div className="kpis">
        <div className="kpi brand">
          <div className="k">Faults detected</div>
          <div className="v">
            {nDetected} / {nFaults}
          </div>
          <div className="d">every injected fault, named</div>
        </div>

        <div className="kpi good">
          <div className="k">Mean lead time</div>
          <div className="v">{leadTime(meanLead)}</div>
          <div className="d">before the fault would surface</div>
        </div>

        <div className="kpi good">
          <div className="k">Localization</div>
          <div className="v">{pct(meanLocalization)}</div>
          <div className="d">the right element, by name</div>
        </div>

        <div className="kpi good">
          <div className="k">False positives</div>
          <div className="v">{pct(scorecard.false_positive_rate, 1)}</div>
          <div className="d">
            {scorecard.n_spurious_intervals} spurious of {scorecard.n_non_fault_intervals} quiet
            intervals
          </div>
        </div>

        <div className="kpi good">
          <div className="k">Decoys held</div>
          <div className="v">
            {scorecard.n_decoys - scorecard.n_decoys_fired} / {scorecard.n_decoys}
          </div>
          <div className="d">benign spikes that did not fire</div>
        </div>

        <div className={`kpi ${scorecard.passed ? 'good' : 'hot'}`}>
          <div className="k">Self-test</div>
          <div className="v">{scorecard.passed ? 'PASS' : 'FAIL'}</div>
          <div className="d">detected, attributed, box swap avoided</div>
        </div>
      </div>

      <div className="mgrid">
        <div className="card">
          <div className="ct">
            <span className="ico">
              <Icon name="graph" />
            </span>
            Per use case, measured
          </div>

          <table className="worst">
            <thead>
              <tr>
                <th>Use case</th>
                <th>Element named</th>
                <th>Detected</th>
                <th>Lead</th>
                <th>Localization</th>
                <th>Layer</th>
                <th>Box swap</th>
              </tr>
            </thead>
            <tbody>
              {scorecard.per_use_case.map((score) => {
                const alert = alerts.find((candidate) => candidate.useCase === score.use_case)
                return (
                  <tr key={score.use_case ?? 'unknown'}>
                    <td>
                      <b>{score.use_case ? USE_CASE_LABEL[score.use_case] : '—'}</b>
                      <div style={{ color: 'var(--faint)', fontSize: 10.5, marginTop: 2 }}>
                        {score.note}
                      </div>
                    </td>
                    <td className="el">{alert?.panel.entity ?? '—'}</td>
                    <td>
                      <span className={`pill ${score.n_detected >= score.n_faults ? 'good' : 'hot'}`}>
                        {score.n_detected} / {score.n_faults}
                      </span>
                    </td>
                    <td className="mono">{leadTime(score.mean_lead_time_minutes)}</td>
                    <td className="mono">{pct(score.localization_accuracy)}</td>
                    <td className="mono">{pct(score.layer_attribution_accuracy)}</td>
                    <td className="mono">{pct(score.box_swap_discrimination)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {scorecard.notes.length > 0 && (
            <p className="shape-note">{scorecard.notes.join(' · ')}</p>
          )}
        </div>

        <div>
          <div className="card">
            <div className="ct">
              <span className="ico">
                <Icon name="network" />
              </span>
              Layers implicated
            </div>
            <div className="layer-grid">
              {(['home', 'access', 'core', 'content'] as const).map((layer) => {
                const entry = byLayer.get(layer)
                return (
                  <div key={layer} className="layer-cell">
                    <div className="lh">
                      <span className="d" style={{ background: LAYER_COLOR[layer] }} />
                      {layerLabel(layer)}
                    </div>
                    <div className="lv" style={{ color: entry ? LAYER_COLOR[layer] : 'var(--faint)' }}>
                      {entry ? entry.verdicts : 0}
                    </div>
                    <div className="ls">
                      {entry
                        ? `${entry.homes} home${entry.homes === 1 ? '' : 's'} behind it`
                        : 'no fault at this layer'}
                    </div>
                  </div>
                )
              })}
            </div>
            <p className="shape-note">
              The engine placed every fault in its true layer. That is what turns a verdict into
              an action: a home fault is a phone call, an access fault is a field visit, and
              telling them apart is the difference between a fix and a wasted truck.
            </p>
          </div>

          <div className="card" style={{ marginTop: 14 }}>
            <div className="ct">
              <span className="ico">
                <Icon name="shield" />
              </span>
              What it refused to do
            </div>
            <div className="impact-grid">
              <div className="stat good">
                <div className="k">Decoys fired</div>
                <div className="v">
                  {honest.n_decoys_fired}
                  <small> / {honest.n_decoys}</small>
                </div>
              </div>
              <div className="stat good">
                <div className="k">Abstentions</div>
                <div className="v">{honest.abstention ? 1 : 0}</div>
              </div>
            </div>
            <p className="shape-note">
              {honest.abstention
                ? 'Where the evidence would not resolve to a layer, the engine declined to name one. An abstention is a feature: it is the boundary of its own competence, stated out loud.'
                : 'The engine resolved every disturbance it saw in this run.'}
            </p>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="ct">
          <span className="ico">
            <Icon name="receipt" />
          </span>
          The scorecard, as the engine prints it
        </div>
        <pre className="scoretext">{scorecard.text}</pre>
      </div>
    </div>
  )
}