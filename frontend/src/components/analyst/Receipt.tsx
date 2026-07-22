/**
 * The certified-decision receipt, and the action it licenses.
 *
 * Four rows, and they are not interchangeable: a claim, the evidence for it, an
 * *independent* check that would have failed if the claim were wrong, and the
 * provenance of every number involved. The engine emits all four; the console's only
 * job is to keep them apart and let an operator read them.
 *
 * The action beneath is what the engine recommends. It is shown as a real button
 * because that is what an operator would reach for - but this is a synthetic demo, so
 * pressing it dispatches nothing, and it says so.
 */

import { useState } from 'react'
import type { FaultPanelOut } from '../../api/types'
import { pct } from '../../lib/format'
import type { T } from '../../lib/i18n'
import { Icon, type IconName } from '../Icon'

/** The follow-on actions an operator would take once the engine has named an element. */
function actionsFor(panel: FaultPanelOut, tr: T): { icon: IconName; title: string; sub: string }[] {
  const recommended = panel.report.diagnosis?.recommended_action

  const primary = {
    icon: (panel.layer === 'home' ? 'phone' : 'wrench') as IconName,
    title: recommended ? sentenceCase(recommended) : tr('action.actOnElement'),
    sub: `${panel.entity} · ${panel.region}`,
  }

  return [
    primary,
    {
      icon: 'ticket',
      title: tr('action.openTicket'),
      sub: tr('action.openTicket.sub'),
    },
    {
      icon: 'bell',
      title: tr('action.preWarn'),
      sub: `${tr('action.preWarn.sub')} ${panel.affected.length} ${
        panel.affected.length === 1 ? tr('alerts.home') : tr('alerts.homes')
      }`,
    },
    {
      icon: 'share',
      title: tr('action.shareNoc'),
      sub: tr('action.shareNoc.sub'),
    },
  ]
}

function sentenceCase(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function Receipt({ panel, tr }: { panel: FaultPanelOut; tr: T }) {
  const [acted, setActed] = useState<string | null>(null)
  const receipt = panel.report.receipt
  const evidence = panel.report.diagnosis?.evidence
  const actions = actionsFor(panel, tr)

  return (
    <div className="right">
      <div className="rcol col">
        <section className="rsec">
          <div className="ct">
            <span className="ico">
              <Icon name="receipt" />
            </span>
            {tr('receipt.title')}
          </div>
          <p className="sub">
            {tr('receipt.why')}
          </p>

          {receipt ? (
            <>
              <div className="receipt">
                <div className="rr">
                  <div className="rk">{tr('receipt.claim')}</div>
                  <div className="rv">{receipt.claim}</div>
                </div>
                <div className="rr">
                  <div className="rk">{tr('receipt.evidence')}</div>
                  <div className="rv">
                    {receipt.evidence_lines.length === 1 ? (
                      receipt.evidence_lines[0]
                    ) : (
                      <ul>
                        {receipt.evidence_lines.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
                <div className="rr">
                  <div className="rk">{tr('receipt.check')}</div>
                  <div className="rv">{receipt.check}</div>
                </div>
                <div className="rr">
                  <div className="rk">{tr('receipt.provenance')}</div>
                  <div className="rv mono" style={{ fontSize: '10.5px' }}>
                    {receipt.provenance}
                  </div>
                </div>
              </div>

              <div className="conf-bar">
                <span style={{ color: 'var(--faint)', fontSize: '10.5px' }}>{tr('receipt.confidence').toUpperCase()}</span>
                <span className="track">
                  <i style={{ width: `${Math.round(receipt.confidence * 100)}%` }} />
                </span>
                <span className="cv">{pct(receipt.confidence)}</span>
              </div>
            </>
          ) : (
            <p className="sub">{tr('receipt.none')}</p>
          )}
        </section>

        {/* The homes the verdict actually rests on. Naming them is the provenance. */}
        {evidence && (
          <section className="rsec">
            <div className="ct">
              <span className="ico">
                <Icon name="target" />
              </span>
              {tr('receipt.whatItLookedAt')}
            </div>
            <p className="sub">
              {tr('receipt.intervals')}{' '}
              <b className="mono">
                {evidence.provenance.interval_start}–{evidence.provenance.interval_end}
              </b>{' '}
              · {evidence.provenance.entities_examined.length} {tr('receipt.entitiesExamined')} ·{' '}
              {evidence.provenance.note}
            </p>
            <div className="qmeta">
              {panel.affected.slice(0, 6).map((home) => (
                <span key={home} className="chip mono">
                  {home}
                </span>
              ))}
              {panel.affected.length > 6 && (
                <span className="chip">+{panel.affected.length - 6} more</span>
              )}
            </div>
          </section>
        )}
      </div>

      <div className="actions">
        <div className="ct">
          <span className="ico">
            <Icon name="wrench" />
          </span>
          {tr('action.title')}
        </div>

        {actions.map((action, index) => (
          <button
            key={action.title}
            type="button"
            className={`abtn${index === 0 ? ' primary' : ''}`}
            onClick={() => setActed(action.title)}
          >
            <span className="aico">
              <Icon name={action.icon} />
            </span>
            <span className="atxt">
              <b>{action.title}</b>
              <small>{action.sub}</small>
            </span>
            <span className="go">›</span>
          </button>
        ))}

        <p className="sub" style={{ margin: '4px 0 0' }}>
          {acted
            ? `“${acted}” — nothing was dispatched: this is a synthetic demo, on a synthetic network.`
            : tr('action.footer')}
        </p>
      </div>
    </div>
  )
}