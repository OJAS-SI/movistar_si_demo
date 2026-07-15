/**
 * Where the regions sit on the map.
 *
 * Coordinates are presentation, not domain: the engine has no opinion about latitude,
 * so the map's geometry lives here rather than being asked of the API. Everything else
 * on the map tab - which regions exist, their central offices, what went wrong in them
 * - comes from the run's own config and verdicts.
 *
 * Regions are keyed by province_code (28 = Madrid, 08 = Barcelona ...), which is what
 * the API sends and what Telefonica's 7-digit MIGA central-office identifiers lead
 * with. Keying on the code rather than the display name means a region whose name is
 * spelled differently ("A Coruna" / "A Coruña") still lands in the right place.
 */

/**
 * The Iberian peninsula. This outline covers all of Iberia, so Portugal is drawn back
 * over it (see PORTUGAL_PATH) to carve itself out - paint them in that order or Spain
 * swallows its neighbour and the silhouette stops reading as Spain.
 */
export const SPAIN_PATH =
  'M148 168 L250 142 L360 138 L470 146 L600 164 L688 176 Q742 190 736 226 L718 286 ' +
  'L672 340 L632 388 L594 430 L558 494 L512 552 L462 596 L410 628 L360 652 ' +
  'Q338 662 316 652 L276 636 L236 604 Q150 566 140 520 L134 420 L138 300 L146 214 Z'

/** Portugal: drawn over Spain, darker and dashed, because nothing here is monitored. */
export const PORTUGAL_PATH =
  'M150 300 L140 420 L142 520 Q150 566 236 604 L252 560 L240 410 L214 300 Z'

/** Framed on the peninsula, as the twin console framed it. */
export const MAP_VIEWBOX = '0 40 820 640'

export interface Place {
  x: number
  y: number
  /** Which side to hang the label on, so labels do not collide with the coastline. */
  anchor: 'start' | 'end' | 'middle'
}

const PLACES: Record<string, Place> = {
  '28': { x: 410, y: 364, anchor: 'middle' }, // Madrid
  '08': { x: 704, y: 298, anchor: 'end' }, // Barcelona
  '46': { x: 576, y: 429, anchor: 'start' }, // Valencia
  '41': { x: 296, y: 571, anchor: 'end' }, // Sevilla
  '48': { x: 449, y: 170, anchor: 'middle' }, // Bilbao
  '15': { x: 175, y: 164, anchor: 'start' }, // A Coruna
  '29': { x: 374, y: 617, anchor: 'end' }, // Malaga
  '07': { x: 742, y: 430, anchor: 'start' }, // Palma
}

/** Anything the map has no coordinate for is laid out along the bottom, not dropped. */
const FALLBACK: Place = { x: 400, y: 670, anchor: 'middle' }

export function placeOf(provinceCode: string): Place {
  return PLACES[provinceCode] ?? FALLBACK
}