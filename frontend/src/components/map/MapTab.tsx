/**
 * The map: where in Spain this is happening, at this interval.
 *
 * The regions are the run's own regions, taken from its config, and they light up only
 * when the engine has actually named an element in them. A region with a fault forming
 * but not yet named pulses amber - visible, but not claimed.
 *
 * The twin console hardcoded eight cities and a fake OLT tree. This does not: the
 * central offices listed under a region are the ones the run was configured with, and
 * the element shown against one is the element the engine named. If the config changes,
 * the map changes with it.
 */

import { useState } from 'react'
import type { RunOut } from '../../api/types'
import { alertStateAt, type Alert } from '../../lib/alerts'
import { C, clockAt, layerLabel, pct } from '../../lib/format'
import { MAP_VIEWBOX, placeOf, PORTUGAL_PATH, SPAIN_PATH } from '../../lib/geo'
import { Icon } from '../Icon'

interface MapTabProps {
  /** The regions are the run's own: the map draws whatever this run was configured with. */
  run: RunOut | null
  alerts: Alert[]
  t: number
  intervalSeconds: number
  onOpenAlert: (useCase: string) => void
}

type RegionStatus = 'named' | 'forming' | 'clear'

export function MapTab({ run, alerts, t, intervalSeconds, onOpenAlert }: MapTabProps) {
  const regions = run?.config.regions ?? []
  const [selected, setSelected] = useState<string | null>(null)

  /** Which alerts belong to a region, and how loud it should be right now. */
  const alertsIn = (regionName: string) =>
    alerts.filter((alert) => alert.panel.region === regionName)

  const statusOf = (regionName: string): RegionStatus => {
    const here = alertsIn(regionName)
    if (here.some((alert) => alertStateAt(alert, t) === 'named')) return 'named'
    if (here.some((alert) => alertStateAt(alert, t) === 'forming')) return 'forming'
    return 'clear'
  }

  const colorOf = (status: RegionStatus) =>
    status === 'named' ? C.red : status === 'forming' ? C.amber : C.green

  const selectedRegion = regions.find((region) => region.name === selected) ?? null

  return (
    <div className="maptab">
      <div className="mapwrap">
        <svg
          className="mapsvg"
          viewBox={MAP_VIEWBOX}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Map of Spain"
        >
          <defs>
            <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="16" />
            </filter>
          </defs>

          {/* Spain first, then Portugal back over it: the outline spans all of Iberia. */}
          <path d={SPAIN_PATH} fill="#0e2135" stroke={C.line} strokeWidth="1.5" />
          <path
            d={PORTUGAL_PATH}
            fill="#0a1927"
            stroke="#16324a"
            strokeWidth="1"
            strokeDasharray="4 4"
          />
          <text x="180" y="470" fill={C.faint} fontSize="11" opacity="0.7">
            Portugal
          </text>

          {/* The Balearics, sketched in. Nothing in this demo is monitored there. */}
          <circle cx="742" cy="430" r="7" fill="#0e2135" stroke={C.line} />
          <circle cx="770" cy="415" r="4" fill="#0e2135" stroke={C.line} />

          {regions.map((region) => {
            const place = placeOf(region.province_code)
            const status = statusOf(region.name)
            const color = colorOf(status)
            const here = alertsIn(region.name)
            const named = here.filter((alert) => alertStateAt(alert, t) === 'named')
            const isSelected = selected === region.name

            // The halo scales with how many homes the engine has actually implicated.
            const homes = named.reduce((sum, alert) => sum + alert.panel.affected.length, 0)
            const halo = status === 'clear' ? 0 : 14 + Math.min(26, homes * 1.2)

            return (
              <g
                key={region.province_code}
                onClick={() => setSelected(isSelected ? null : region.name)}
                style={{ cursor: 'pointer' }}
              >
                {halo > 0 && (
                  <circle cx={place.x} cy={place.y} r={halo} fill={color} opacity={0.18} filter="url(#glow)">
                    <animate
                      attributeName="opacity"
                      values="0.28;0.08;0.28"
                      dur={status === 'named' ? '1.8s' : '2.6s'}
                      repeatCount="indefinite"
                    />
                  </circle>
                )}

                <circle
                  cx={place.x}
                  cy={place.y}
                  r={isSelected ? 8 : 6}
                  fill={color}
                  stroke={isSelected ? '#fff' : 'none'}
                  strokeWidth={1.5}
                />

                <text
                  x={place.x + (place.anchor === 'end' ? -12 : place.anchor === 'start' ? 12 : 0)}
                  y={place.y - 14}
                  textAnchor={place.anchor}
                  fill={status === 'clear' ? C.muted : '#fff'}
                  fontSize="12"
                  fontWeight={600}
                >
                  {region.name}
                </text>

                {named.length > 0 && (
                  <text
                    x={place.x + (place.anchor === 'end' ? -12 : place.anchor === 'start' ? 12 : 0)}
                    y={place.y + 24}
                    textAnchor={place.anchor}
                    fill={color}
                    fontSize="10.5"
                    fontFamily="monospace"
                  >
                    {named[0].panel.entity}
                  </text>
                )}
              </g>
            )
          })}
        </svg>

        <div className="map-legend">
          <div className="lg-title">At interval {t} · {clockAt(t, intervalSeconds)}</div>
          <div className="row">
            <span className="lg-dot" style={{ background: C.red }} /> element named by the engine
          </div>
          <div className="row">
            <span className="lg-dot" style={{ background: C.amber }} /> shape forming, not yet named
          </div>
          <div className="row">
            <span className="lg-dot" style={{ background: C.green }} /> at baseline
          </div>
        </div>
      </div>

      <aside className="mside">
        <div className="mhead">
          <h3>Regions in this run</h3>
          <span className="mono" style={{ color: 'var(--faint)', fontSize: 11 }}>
            {regions.length}
          </span>
        </div>

        {regions.map((region) => {
          const status = statusOf(region.name)
          const named = alertsIn(region.name).filter(
            (alert) => alertStateAt(alert, t) === 'named',
          )
          return (
            <button
              key={region.province_code}
              type="button"
              className={`region-row${selected === region.name ? ' sel' : ''}`}
              onClick={() => setSelected(selected === region.name ? null : region.name)}
            >
              <span className="rd" style={{ background: colorOf(status) }} />
              <span>
                <span className="rn">{region.name}</span>
                <span className="prov" style={{ display: 'block' }}>
                  province {region.province_code} · {region.central_office_names.length} central
                  office{region.central_office_names.length === 1 ? '' : 's'}
                </span>
              </span>
              <span className="rc">
                {named.length > 0 ? `${named.length} alert${named.length === 1 ? '' : 's'}` : '—'}
              </span>
            </button>
          )
        })}

        {selectedRegion && (
          <div className="drill">
            <h4>{selectedRegion.name}</h4>
            <p className="dsub">
              Province <span className="mono">{selectedRegion.province_code}</span> — the leading
              pair of the MIGA central-office identifier, reproduced in every node id below.
            </p>

            <div className="dstat">
              <div className="c">
                <div className="k">Verdicts here</div>
                <div className="v">
                  {alertsIn(selectedRegion.name).filter(
                    (alert) => alertStateAt(alert, t) === 'named',
                  ).length}
                </div>
              </div>
              <div className="c">
                <div className="k">Network weight</div>
                <div className="v">{selectedRegion.weight.toFixed(1)}</div>
              </div>
            </div>

            {/* The central offices this region was actually configured with. */}
            {selectedRegion.central_office_names.map((office) => {
              const here = alertsIn(selectedRegion.name).filter(
                (alert) => alertStateAt(alert, t) === 'named',
              )
              return (
                <div key={office} className="tree-central">
                  <div className="tc-head">
                    <span
                      className="cd"
                      style={{ background: here.length > 0 ? C.red : C.green }}
                    />
                    <span>
                      <span className="miga">{selectedRegion.province_code}·{office}</span>
                      <span className="cn" style={{ display: 'block' }}>
                        central office
                      </span>
                    </span>
                    {here.length > 0 && <span className="fbadge">fault</span>}
                  </div>
                </div>
              )
            })}

            {alertsIn(selectedRegion.name)
              .filter((alert) => alertStateAt(alert, t) === 'named')
              .map((alert) => (
                <div key={alert.useCase} className="mini-alert">
                  <span
                    className="md"
                    style={{ background: alert.severity === 'crit' ? C.red : C.amber }}
                  />
                  <div style={{ minWidth: 0 }}>
                    <div className="mt">{layerLabel(alert.panel.layer)}</div>
                    <div className="me">
                      {alert.panel.entity} · {pct(alert.panel.report.diagnosis?.confidence ?? 0)}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="open"
                    onClick={() => onOpenAlert(alert.useCase)}
                  >
                    Open
                  </button>
                </div>
              ))}

            {alertsIn(selectedRegion.name).length === 0 && (
              <p className="sub" style={{ color: 'var(--faint)', fontSize: 11.5 }}>
                <Icon name="check" className="tick ok" style={{ width: 13, height: 13 }} /> Nothing
                was ever named here. This region stayed at baseline for the whole run.
              </p>
            )}
          </div>
        )}
      </aside>
    </div>
  )
}