/**
 * The forming shape, drawn on the graph.
 *
 * This is the picture that carries the argument: the engine does not read an error code,
 * it reads *structure*. So the schematic draws the actual affected homes from the
 * verdict, hanging off the actual element the engine named, and lights them up as the
 * shape fills in across the intervals before the call.
 *
 * The four shapes are the four in the domain, and each one implicates a different layer:
 *
 *   cluster  homes behind one parent   -> the access node is at fault
 *   single   one home, healthy peers   -> the fault is inside that home
 *   path     nodes along a route       -> the core / transport path
 *   source   one origin, many unrelated homes -> the content source
 *
 * Nothing here is invented: the count of lit homes is the count in the verdict.
 */

import type { FaultPanelOut } from '../../api/types'
import { C } from '../../lib/format'

const WIDTH = 520
const HEIGHT = 230

interface ShapeGraphProps {
  panel: FaultPanelOut
  /** 0..1 - how far the shape had formed by the interval on screen. */
  progress: number
  /** True once the engine has named the element. */
  named: boolean
}

export function ShapeGraph({ panel, progress, named }: ShapeGraphProps) {
  const affected = panel.affected.length
  // Once the element is named the whole shape is lit; before that it fills in.
  const fraction = named ? 1 : Math.max(0, Math.min(1, progress))
  const lit = Math.round(affected * fraction)

  return (
    <>
      <svg className="shape-svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img"
           aria-label={`${panel.shape} shape on ${panel.entity}`}>
        {panel.shape === 'single' ? (
          <SingleShape panel={panel} lit={lit} />
        ) : panel.shape === 'path' ? (
          <PathShape panel={panel} fraction={fraction} />
        ) : panel.shape === 'source' ? (
          <SourceShape panel={panel} lit={lit} affected={affected} />
        ) : (
          <ClusterShape panel={panel} lit={lit} affected={affected} />
        )}
      </svg>

      <div className="legend">
        <span>
          <i className="lg-dot" style={{ background: C.red }} /> impaired home
        </span>
        <span>
          <i className="lg-dot" style={{ background: C.amber }} /> just starting to drift
        </span>
        <span>
          <i className="lg-dot" style={{ background: C.off }} /> healthy peer
        </span>
        <span>
          <i className="lg-dot" style={{ background: C.cyan }} /> the named element
        </span>
      </div>
    </>
  )
}

/** A home dot. The newest homes to light up are amber - the shape is still spreading. */
function Home({ x, y, on, fresh, i }: { x: number; y: number; on: boolean; fresh: boolean; i: number }) {
  return (
    <circle cx={x} cy={y} r={on ? 5 : 3} fill={on ? (fresh ? C.amber : C.red) : C.off}>
      {on && (
        <animate
          attributeName="opacity"
          values="1;.5;1"
          dur={`${1.5 + (i % 5) * 0.2}s`}
          repeatCount="indefinite"
        />
      )}
    </circle>
  )
}

function Element({ x, y, label }: { x: number; y: number; label: string }) {
  const width = Math.max(56, label.length * 6.4)
  return (
    <>
      <rect
        x={x - width / 2}
        y={y - 10}
        width={width}
        height={20}
        rx={5}
        fill="#0c2b40"
        stroke={C.cyan}
        strokeWidth={1.3}
      />
      <text
        x={x}
        y={y + 4}
        textAnchor="middle"
        fill="#bfe6ff"
        fontSize={10}
        fontFamily="monospace"
      >
        {label}
      </text>
    </>
  )
}

/** Homes behind one access node: the cluster. */
function ClusterShape({ panel, lit, affected }: { panel: FaultPanelOut; lit: number; affected: number }) {
  // Draw the affected homes plus a few healthy peers, so "clustered" is visibly a claim
  // about *which* homes, not just how many.
  const total = Math.max(affected + 6, 12)
  const cx = WIDTH / 2
  const rows = [150, 185, 212]
  const spread = 420

  return (
    <>
      <text x={cx} y={18} textAnchor="middle" fill={C.muted} fontSize={9}>
        central office
      </text>
      <circle cx={cx} cy={30} r={9} fill="none" stroke={C.cyan} strokeWidth={2} />
      <circle cx={cx} cy={30} r={15} fill="none" stroke={C.cyan} strokeWidth={1} opacity={0.4} />
      <line x1={cx} y1={39} x2={cx} y2={68} stroke="#254a6b" strokeWidth={1.5} />

      <Element x={cx} y={78} label={panel.entity} />

      {Array.from({ length: total }, (_, i) => {
        const offset = i / (total - 1) - 0.5
        const x = cx + offset * spread + (i % 2 ? 6 : -6)
        const y = rows[i % 3]
        const on = i < lit
        const fresh = on && i >= lit - 3
        return (
          <g key={i}>
            <line
              x1={cx}
              y1={88}
              x2={x}
              y2={y}
              stroke={on ? '#4a2530' : '#152e46'}
              strokeWidth={1}
            />
            <Home x={x} y={y} on={on} fresh={fresh} i={i} />
          </g>
        )
      })}
    </>
  )
}

/** One home alone, its peers on the same node untouched. */
function SingleShape({ panel, lit }: { panel: FaultPanelOut; lit: number }) {
  const cx = WIDTH / 2
  const peers = 8
  const spread = 380
  const y = 175
  const on = lit > 0

  return (
    <>
      <text x={cx} y={18} textAnchor="middle" fill={C.muted} fontSize={9}>
        access node — peers healthy
      </text>
      <circle cx={cx} cy={30} r={9} fill="none" stroke={C.cyan} strokeWidth={2} />
      <line x1={cx} y1={39} x2={cx} y2={68} stroke="#254a6b" strokeWidth={1.5} />
      <Element x={cx} y={78} label={panel.entity} />

      {Array.from({ length: peers }, (_, i) => {
        const offset = i / (peers - 1) - 0.5
        const x = cx + offset * spread
        const isTarget = i === Math.floor(peers / 2)
        return (
          <g key={i}>
            <line
              x1={cx}
              y1={88}
              x2={x}
              y2={y}
              stroke={isTarget && on ? '#4a2530' : '#152e46'}
              strokeWidth={1}
            />
            {isTarget ? (
              <>
                {on && (
                  <circle cx={x} cy={y} r={13} fill="none" stroke={C.red} strokeWidth={1} opacity={0.6}>
                    <animate attributeName="r" values="9;16;9" dur="2.4s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values=".7;0;.7" dur="2.4s" repeatCount="indefinite" />
                  </circle>
                )}
                <circle cx={x} cy={y} r={on ? 7 : 4} fill={on ? C.red : C.off} />
              </>
            ) : (
              <circle cx={x} cy={y} r={4} fill={C.green} opacity={0.8} />
            )}
          </g>
        )
      })}

      <text x={cx} y={212} textAnchor="middle" fill={C.faint} fontSize={9.5}>
        every peer on this node stays at baseline — so the cause is inside the home
      </text>
    </>
  )
}

/** Impairment strung along a route: the core. The shape spreads hop by hop. */
function PathShape({ panel, fraction }: { panel: FaultPanelOut; fraction: number }) {
  const hops = 6
  const y0 = 190
  const y1 = 60
  const x0 = 60
  const x1 = WIDTH - 60
  const lit = Math.round(hops * fraction)

  return (
    <>
      <text x={WIDTH / 2} y={18} textAnchor="middle" fill={C.muted} fontSize={9}>
        core / transport route
      </text>
      <line x1={x0} y1={y0} x2={x1} y2={y1} stroke="#254a6b" strokeWidth={1.5} />

      {Array.from({ length: hops }, (_, i) => {
        const f = i / (hops - 1)
        const on = i < lit
        return (
          <Home
            key={i}
            x={x0 + (x1 - x0) * f}
            y={y0 + (y1 - y0) * f}
            on={on}
            fresh={on && i >= lit - 1}
            i={i}
          />
        )
      })}

      <Element x={WIDTH / 2} y={HEIGHT - 26} label={panel.entity} />
    </>
  )
}

/** One origin, many unrelated homes: the content source. */
function SourceShape({ panel, lit, affected }: { panel: FaultPanelOut; lit: number; affected: number }) {
  const cx = WIDTH / 2
  const total = Math.max(affected + 4, 10)
  const y = 180
  const spread = 440

  return (
    <>
      <text x={cx} y={18} textAnchor="middle" fill={C.muted} fontSize={9}>
        content source — homes share no network parent
      </text>
      <Element x={cx} y={44} label={panel.entity} />

      {Array.from({ length: total }, (_, i) => {
        const offset = i / (total - 1) - 0.5
        const x = cx + offset * spread
        const on = i < lit
        return (
          <g key={i}>
            <line
              x1={cx}
              y1={56}
              x2={x}
              y2={y}
              stroke={on ? '#4a2530' : '#152e46'}
              strokeWidth={1}
              strokeDasharray="3 3"
            />
            <Home x={x} y={y} on={on} fresh={on && i >= lit - 3} i={i} />
          </g>
        )
      })}
    </>
  )
}