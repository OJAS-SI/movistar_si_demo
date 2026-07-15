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
import { Icon, type IconName } from '../Icon'

/** The follow-on actions an operator would take once the engine has named an element. */
function actionsFor(panel: FaultPanelOut): { icon: IconName; title: string; sub: string }[] {
  const recommended = panel.report.diagnosis?.recommended_action

  const primary = {
    icon: (panel.layer === 'home' ? 'phone' : 'wrench') as IconName,
    title: recommended ? sentenceCase(recommended) : 'Act on the named element',
    sub: `${panel.entity} · ${panel.region}`,
  }

  return [
    primary,
    {
      icon: 'ticket',
      title: 'Open a field ticket',
      sub: 'Pre-filled with the element, its layer, and the receipt',
    },
    {
      icon: 'bell',
      title: 'Pre-warn Customer Care',
      sub: `Suppress the inbound wave from ${panel.affected.length} home${
        panel.affected.length === 1 ? '' : 's'
      }`,
    },
    {
      icon: 'share',
      title: 'Share the receipt with the NOC',
      sub: 'Route the structural evidence to the transport desk',
    },
  ]
}

function sentenceCase(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function Receipt({ panel }: { panel: FaultPanelOut }) {
  const [acted, setActed] = useState<string | null>(null)
  const receipt = panel.report.receipt
  const evidence = panel.report.diagnosis?.evidence
  const actions = actionsFor(panel)

  return (
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
            Why the engine believes this, what would have proved it wrong, and where every
            number came from.
          </p>

          {receipt ? (
            <>
              <div className="receipt">
                <div className="rr">
                  <div className="rk">Claim</div>
                  <div className="rv">{receipt.claim}</div>
                </div>
                <div className="rr">
                  <div className="rk">Evidence</div>
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
                  <div className="rk">Check</div>
                  <div className="rv">{receipt.check}</div>
                </div>
                <div className="rr">
                  <div className="rk">Provenance</div>
                  <div className="rv mono" style={{ fontSize: '10.5px' }}>
                    {receipt.provenance}
                  </div>
                </div>
              </div>

              <div className="conf-bar">
                <span style={{ color: 'var(--faint)', fontSize: '10.5px' }}>CONFIDENCE</span>
                <span className="track">
                  <i style={{ width: `${Math.round(receipt.confidence * 100)}%` }} />
                </span>
                <span className="cv">{pct(receipt.confidence)}</span>
              </div>
            </>
          ) : (
            <p className="sub">This verdict carried no receipt.</p>
          )}
        </section>

        {/* The homes the verdict actually rests on. Naming them is the provenance. */}
        {evidence && (
          <section className="rsec">
            <div className="ct">
              <span className="ico">
                <Icon name="target" />
              </span>
              What it looked at
            </div>
            <p className="sub">
              Intervals{' '}
              <b className="mono">
                {evidence.provenance.interval_start}–{evidence.provenance.interval_end}
              </b>{' '}
              · {evidence.provenance.entities_examined.length} entities examined ·{' '}
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
          Recommended action
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
            : 'These are the actions the verdict licenses. Nothing here dispatches to a real network.'}
        </p>
      </div>
    </div>
  )
}