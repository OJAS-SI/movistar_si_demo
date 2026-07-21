/**
 * The alert queue, assembled from the run.
 *
 * An alert is one of the console's fault panels, placed on the timeline. Two intervals
 * matter and they are not the same one:
 *
 *   onset   when the fault actually began. Ground truth, from the stream.
 *   named   when the engine settled on the element. Its verdict, from the console.
 *
 * The distance between them is the lead time the scorecard reports, and holding both is
 * what lets the queue show an alert *forming* before it is *named* - the thing the demo
 * is actually about. We never collapse them into one number here.
 */

import type { ConsoleOut, FaultPanelOut, Layer, Shape, StreamFrameOut, UseCase } from '../api/types'
import type { Onset } from '../hooks/useReplay'
import { severityOf, type Severity } from './format'

/**
 * A fault as the live stream reveals it, before the full run has finished computing.
 *
 * This is deliberately thinner than an Alert: it carries only what a single streamed
 * diagnosis knows (the named element, its layer and shape, the engine's confidence, the
 * interval it was first named, and the live claim). The scorecard numbers - lead time,
 * localization, the settled receipt - arrive with the full console; until then, this is
 * the honest live picture, piped straight from detection.
 */
export interface LiveFault {
  entity: string
  layer: Layer | null
  shape: Shape
  confidence: number
  firstSeen: number
  action: string | null
  claim: string | null
  nAffected: number
}

/** Accumulate the faults the engine has named so far, from the buffered stream frames. */
export function liveFaults(frames: StreamFrameOut[]): LiveFault[] {
  const byEntity = new Map<string, LiveFault>()
  for (const frame of frames) {
    for (const d of frame.diagnoses) {
      if (!d.detected || !d.entity_id) continue
      const existing = byEntity.get(d.entity_id)
      const nAffected = d.evidence?.provenance.entities_examined.length ?? 0
      if (existing) {
        // Keep the first sighting, but let confidence and blast radius grow as the shape
        // fills in over the fault's life.
        existing.confidence = Math.max(existing.confidence, d.confidence)
        existing.nAffected = Math.max(existing.nAffected, nAffected)
      } else {
        byEntity.set(d.entity_id, {
          entity: d.entity_id,
          layer: d.layer,
          shape: d.shape,
          confidence: d.confidence,
          firstSeen: frame.timestamp,
          action: d.recommended_action,
          claim: d.evidence?.claim ?? null,
          nAffected,
        })
      }
    }
  }
  return [...byEntity.values()].sort((a, b) => a.firstSeen - b.firstSeen)
}

export type AlertState = 'quiet' | 'forming' | 'named'

export interface Alert {
  /**
   * Identity of this alert, and the ONLY thing that may be used to select, key or
   * compare one.
   *
   * It used to be `useCase`, which is not unique: a full run has 24 fault panels across
   * just 5 use cases - 13 of them uc1. That made every uc1 card share a React key and a
   * selection value, so clicking one selected the first uc1 panel, highlighted all 13,
   * and left some cards apparently dead. The entity a verdict names is unique per run.
   */
  id: string
  useCase: UseCase
  panel: FaultPanelOut
  severity: Severity
  /** The interval the engine named the element. */
  namedAt: number
  /** The interval the fault truly began, when the stream told us. */
  onsetAt: number | null
  /** Homes behind this verdict. */
  nAffected: number
}

export function buildAlerts(model: ConsoleOut, _onsets: Onset[]): Alert[] {
  // The onset comes from the panel, not from the stream's fault ids. Those ids carry no
  // entity, so the only way to join them here was by use case - which put the first uc1
  // fault's onset on all thirteen of them, and made twelve alerts claim to start hours
  // before they did.
  return model.fault_panels.map((panel, index) => ({
    id: `${index}:${panel.entity}`,
    useCase: panel.use_case,
    panel,
    severity: severityOf(panel.report.health_band),
    namedAt: panel.report.diagnosis?.timestamp ?? panel.report.timestamp,
    onsetAt: panel.onset_interval,
    nAffected: panel.affected.length,
  }))
}

export function alertStateAt(alert: Alert, t: number): AlertState {
  if (t >= alert.namedAt) return 'named'
  if (alert.onsetAt !== null && t >= alert.onsetAt) return 'forming'
  return 'quiet'
}

/**
 * How much of the fault the engine could see by interval t, as a fraction. Used only to
 * animate the schematic as the shape fills in - it is a drawing aid, not a measurement,
 * and nothing numeric is ever labelled with it.
 */
export function formationProgress(alert: Alert, t: number): number {
  const start = alert.onsetAt ?? alert.namedAt
  if (t <= start) return 0
  const span = Math.max(1, alert.namedAt - start)
  return Math.max(0, Math.min(1, (t - start) / span))
}

/** The alert an operator should be looking at right now: the newest one named. */
export function mostRecentlyNamed(alerts: Alert[], t: number): Alert | null {
  const named = alerts.filter((alert) => t >= alert.namedAt)
  if (named.length === 0) return null
  return named.reduce((latest, alert) => (alert.namedAt > latest.namedAt ? alert : latest))
}