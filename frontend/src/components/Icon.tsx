/**
 * The icon set, carried over from the twin console.
 *
 * Icons are inline SVG paths rather than an icon package: the whole demo is meant to
 * run with no external assets, and this keeps that true for the React build too.
 */

import type { CSSProperties } from 'react'
import { C } from '../lib/format'
import type { Shape } from '../api/types'

export type IconName =
  | 'graph'
  | 'grid'
  | 'map'
  | 'wrench'
  | 'ticket'
  | 'bell'
  | 'share'
  | 'phone'
  | 'stop'
  | 'tv'
  | 'user'
  | 'repeat'
  | 'play'
  | 'pause'
  | 'shield'
  | 'check'
  | 'alert'
  | 'eye'
  | 'receipt'
  | 'target'
  | 'network'

const PATHS: Record<IconName, string> = {
  graph: '<path d="M3 3v18h18"/><path d="M7 14l3-3 3 3 4-5"/>',
  grid:
    '<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/>' +
    '<rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>',
  map: '<path d="M9 3 3 6v15l6-3 6 3 6-3V3l-6 3-6-3Z"/><path d="M9 3v15M15 6v15"/>',
  wrench:
    '<path d="M14.7 6.3a4 4 0 0 1-5.4 5.4L4 17v3h3l5.3-5.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.5-.7-.7-2.5z"/>',
  ticket:
    '<path d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4z"/><path d="M13 6v12"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0"/>',
  share:
    '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>',
  phone:
    '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.6A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .8 2.9a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.2-1.3a2 2 0 0 1 2.1-.5c.9.4 1.9.7 2.9.8a2 2 0 0 1 1.7 2z"/>',
  stop: '<circle cx="12" cy="12" r="9"/><path d="M8 8l8 8"/>',
  tv: '<rect x="2" y="7" width="20" height="13" rx="2"/><path d="M8 3l4 4 4-4"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  repeat:
    '<path d="M17 2l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14M7 22l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
  play: '<path d="M7 4l12 8-12 8z" fill="currentColor" stroke="none"/>',
  pause:
    '<rect x="6" y="4" width="4" height="16" fill="currentColor" stroke="none"/><rect x="14" y="4" width="4" height="16" fill="currentColor" stroke="none"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="M9 12l2 2 4-4"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  alert:
    '<path d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
  eye: '<circle cx="12" cy="12" r="3"/><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/>',
  receipt:
    '<path d="M6 2h12v20l-3-2-3 2-3-2-3 2Z"/><path d="M9 7h6M9 11h6M9 15h3"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
  network:
    '<circle cx="5" cy="12" r="2"/><circle cx="12" cy="5" r="2"/><circle cx="12" cy="19" r="2"/><circle cx="19" cy="12" r="2"/><path d="M6.8 11 10.5 6.2M13.5 6.2 17.2 11M17.2 13 13.5 17.8M10.5 17.8 6.8 13"/>',
}

interface IconProps {
  name: IconName
  className?: string
  strokeWidth?: number
  style?: CSSProperties
}

export function Icon({ name, className, strokeWidth = 2, style }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: PATHS[name] }}
    />
  )
}

/**
 * The shape glyph: a miniature of the structure the engine read off the graph. A
 * cluster hangs off one parent, a single home stands alone among healthy peers, a path
 * runs along a route, a source fans out to unrelated homes. These are the four shapes
 * in the domain, so there is a glyph for each.
 */
const SHAPE_GLYPHS: Record<Shape, string> = {
  cluster:
    `<circle cx="12" cy="6" r="2.4" fill="${C.cyan}"/><circle cx="6" cy="16" r="1.8" fill="${C.red}"/>` +
    `<circle cx="12" cy="17" r="1.8" fill="${C.red}"/><circle cx="18" cy="16" r="1.8" fill="${C.red}"/>` +
    `<path d="M12 8.4 6.5 14M12 8.4 17.5 14M12 8.4v6.6" stroke="#3a5f80" stroke-width="1.3"/>`,
  single:
    `<circle cx="6" cy="16" r="1.8" fill="${C.green}"/><circle cx="18" cy="16" r="1.8" fill="${C.green}"/>` +
    `<circle cx="12" cy="16" r="2.4" fill="${C.red}"/>` +
    `<circle cx="12" cy="16" r="4.4" fill="none" stroke="${C.red}" stroke-width="1"/>`,
  path:
    `<circle cx="5" cy="18" r="1.8" fill="${C.red}"/><circle cx="10" cy="13" r="1.8" fill="${C.red}"/>` +
    `<circle cx="15" cy="9" r="1.8" fill="${C.red}"/><circle cx="20" cy="5" r="1.8" fill="${C.red}"/>` +
    `<path d="M5 18 20 5" stroke="#3a5f80" stroke-width="1.3"/>`,
  source:
    `<circle cx="12" cy="5" r="2.6" fill="${C.cyan}"/><circle cx="5" cy="18" r="1.7" fill="${C.red}"/>` +
    `<circle cx="12" cy="19" r="1.7" fill="${C.red}"/><circle cx="19" cy="18" r="1.7" fill="${C.red}"/>` +
    `<path d="M12 7.6 5.5 16M12 7.6v9M12 7.6 18.5 16" stroke="#3a5f80" stroke-width="1.1" stroke-dasharray="2 2"/>`,
  none: `<circle cx="12" cy="12" r="6" fill="none" stroke="${C.faint}" stroke-width="1.5" stroke-dasharray="3 3"/>`,
}

export function ShapeGlyph({ shape }: { shape: Shape }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: SHAPE_GLYPHS[shape] }}
    />
  )
}