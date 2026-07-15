/**
 * Turning the API's values into the words and colours the console shows.
 *
 * The rule this file follows: display what the API measured, and derive nothing that
 * could be mistaken for a measurement. Where a number is missing the answer is a dash,
 * never a zero and never a guess - the engine is allowed to have no opinion, and the
 * console has to be able to say so.
 */

import type { Layer, Shape, UseCase } from '../api/types'

/** The palette, in hex, because SVG attributes cannot take CSS custom properties. */
export const C = {
  red: '#F0554E',
  amber: '#F2A73B',
  green: '#2FD08A',
  cyan: '#19B3F0',
  line: '#254a6b',
  lineSoft: '#1E3B57',
  muted: '#89A6C2',
  faint: '#5C7893',
  ink: '#08131F',
  panel: '#10233A',
  sea: '#0b1f33',
  off: '#20405e',
} as const

/**
 * Interval index as a wall clock, anchored at midnight.
 *
 * The domain samples on a fixed cadence from midnight (that is why prime time starts at
 * interval 240 of a 288-interval day, i.e. 20:00), so the clock is the interval times
 * the cadence, wrapped at a day.
 */
export function clockAt(interval: number, intervalSeconds: number): string {
  const secondsOfDay = ((interval * intervalSeconds) % 86400 + 86400) % 86400
  const hh = Math.floor(secondsOfDay / 3600)
  const mm = Math.floor((secondsOfDay % 3600) / 60)
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
}

/** A ratio (0..1) as a percentage. Null means the engine reported nothing. */
export function pct(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function num(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return '—'
  return value.toFixed(digits)
}

/** Minutes of lead time, phrased the way an operator would say it. */
export function leadTime(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) return '—'
  if (minutes < 60) return `${Math.round(minutes)} min`
  const hours = minutes / 60
  return `${hours.toFixed(hours < 10 ? 1 : 0)} h`
}

export const LAYER_LABEL: Record<Layer, string> = {
  home: 'Home / Wi-Fi',
  access: 'Access / aggregation',
  core: 'Core / transport',
  content: 'Content / CDN',
}

export const LAYER_COLOR: Record<Layer, string> = {
  home: C.amber,
  access: C.red,
  core: C.cyan,
  content: '#a78bfa',
}

export function layerLabel(layer: Layer | null): string {
  return layer ? LAYER_LABEL[layer] : 'Unresolved'
}

export const SHAPE_LABEL: Record<Shape, string> = {
  single: 'Single (isolated home)',
  cluster: 'Cluster (behind one node)',
  path: 'Path (along a route)',
  source: 'Source (one origin, many homes)',
  none: 'No shape',
}

/** The one-line reason each use case is in the demo at all. */
export const USE_CASE_LABEL: Record<UseCase, string> = {
  uc1_network_node: 'Network node degrading',
  uc2_individual: 'Household declining',
  uc3_invisible: 'Invisible fault',
  decoy: 'Decoy',
  healthy: 'Healthy',
}

export type Severity = 'crit' | 'warn' | 'info'

/**
 * Severity from the engine's own health band. The band is a sentence the domain wrote
 * ("critical for the affected element", "degraded for the household", "watch"), so we
 * read it rather than re-deriving severity from confidence and inventing a threshold.
 */
export function severityOf(healthBand: string): Severity {
  const band = healthBand.toLowerCase()
  if (band.startsWith('critical')) return 'crit'
  if (band.startsWith('degraded')) return 'warn'
  return 'info'
}

export function severityColor(severity: Severity): string {
  return severity === 'crit' ? C.red : severity === 'warn' ? C.amber : C.cyan
}

/** The pill class for a health band, matching the twin's three bands. */
export function bandClass(healthBand: string): string {
  const severity = severityOf(healthBand)
  return severity === 'crit' ? 'band-crit' : severity === 'warn' ? 'band-deg' : 'band-ok'
}

/**
 * Ground-truth fault ids carry their use case in the id: F-UC1-OLT, D-GLITCH. That is
 * the injector's naming, and it is what lets the timeline mark a real fault's onset
 * differently from a decoy's - the whole point of the ribbon.
 */
export function isDecoy(faultId: string): boolean {
  return faultId.startsWith('D-')
}

// Named `faultUseCase` rather than `useCaseOf...`: a leading "use" makes every React
// lint rule treat the function as a hook and refuse to let plain code call it.
export function faultUseCase(faultId: string): UseCase | null {
  if (faultId.startsWith('D-')) return 'decoy'
  if (faultId.startsWith('F-UC1')) return 'uc1_network_node'
  if (faultId.startsWith('F-UC2')) return 'uc2_individual'
  if (faultId.startsWith('F-UC3')) return 'uc3_invisible'
  return null
}