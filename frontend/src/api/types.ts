/**
 * The API contract, in TypeScript.
 *
 * These types mirror backend/si_api/schemas.py one-for-one. That module is the single
 * statement of what crosses the wire; this file is its shadow on the client, and the
 * only place the frontend is allowed to describe the server's shapes. If a schema
 * changes there, it changes here, and nowhere else.
 *
 * Nothing in here describes the domain. The frontend never sees si_core.
 */

export type ScaleName = 'tiny' | 'full'
export type RunStatus = 'running' | 'complete' | 'failed'

/** Layers of the network, as the engine attributes them. */
export type Layer = 'home' | 'access' | 'core' | 'content'

/** The structural signature the engine reads off the graph. */
export type Shape = 'single' | 'cluster' | 'path' | 'source' | 'none'

export type UseCase =
  | 'uc1_network_node'
  | 'uc2_individual'
  | 'uc3_invisible'
  | 'decoy'
  | 'healthy'

/** "detection" | "abstention" | "all_clear" */
export type ReportKind = string

// ---------------------------------------------------------------------------
// Health and configuration
// ---------------------------------------------------------------------------

export interface HealthOut {
  status: 'ok'
  api_version: string
  core_version: string
  frozen_contract_version: string
}

export interface RegionOut {
  name: string
  province_code: string
  central_office_names: string[]
  weight: number
}

export interface ConfigOut {
  seed: number
  scale: ScaleName
  n_homes_target: number
  interval_seconds: number
  run_intervals: number
  regions: RegionOut[]
}

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export interface RunRequest {
  scale: ScaleName
  seed?: number | null
}

export interface RunOut {
  run_id: string
  scale: ScaleName
  seed: number
  status: RunStatus
  created_at: number
  config: ConfigOut
  runtime_seconds: number | null
  /** The internal self-test. Null until the run completes. */
  passed: boolean | null
  summary: string | null
  error: string | null
}

// ---------------------------------------------------------------------------
// Topology
// ---------------------------------------------------------------------------

export interface NodeOut {
  entity_id: string
  entity_type: string
  layer: string
  parent_id: string | null
  region: string
}

export interface TopologyOut {
  n_nodes: number
  n_homes: number
  n_access_nodes: number
  counts_by_type: Record<string, number>
  regions: string[]
  nodes: NodeOut[]
  truncated: boolean
}

// ---------------------------------------------------------------------------
// Diagnosis, evidence, receipt
// ---------------------------------------------------------------------------

export interface ProvenanceOut {
  interval_start: number
  interval_end: number
  entities_examined: string[]
  note: string
}

export interface EvidenceOut {
  claim: string
  supporting: string[]
  check: string
  provenance: ProvenanceOut
}

export interface TrajectoryOut {
  rising: boolean
  horizon_interval: number | null
  detail: string
}

export interface DiagnosisOut {
  timestamp: number
  detected: boolean
  abstained: boolean
  entity_id: string | null
  layer: Layer | null
  shape: Shape
  confidence: number
  recommended_action: string | null
  trajectory: TrajectoryOut | null
  evidence: EvidenceOut | null
}

/** The certified-decision receipt: claim, evidence, an independent check, provenance. */
export interface ReceiptOut {
  claim: string
  evidence_lines: string[]
  check: string
  provenance: string
  confidence: number
}

export interface ReportOut {
  timestamp: number
  kind: ReportKind
  headline: string
  /** Title form: the element and what is wrong, without the paragraph. */
  headline_short: string
  health_band: string
  /** Badge form of the band: "Critical", "Degraded", "Watch". */
  health_band_short: string
  receipt: ReceiptOut | null
  diagnosis: DiagnosisOut | null
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

/** Measured values only. No success threshold is fixed anywhere in this contract. */
export interface ScoreOut {
  use_case: UseCase | null
  n_faults: number
  n_detected: number
  mean_lead_time_intervals: number | null
  mean_lead_time_minutes: number | null
  localization_accuracy: number | null
  layer_attribution_accuracy: number | null
  box_swap_discrimination: number | null
  false_positive_rate: number | null
  action_correctness: number | null
  note: string
}

export interface ScorecardOut {
  per_use_case: ScoreOut[]
  false_positive_rate: number
  n_non_fault_intervals: number
  n_spurious_intervals: number
  n_decoys: number
  n_decoys_fired: number
  interval_seconds: number
  notes: string[]
  passed: boolean
  /** The rendered plain-text scorecard, for parity with the CLI. */
  text: string
}

// ---------------------------------------------------------------------------
// The operator console (the four-beat narrative)
// ---------------------------------------------------------------------------

export interface BeatOut {
  name: string
  text: string
}

export interface FaultPanelOut {
  use_case: UseCase
  title: string
  /** Ground-truth onset for THIS fault, or null. Never join onsets by use case. */
  onset_interval: number | null
  beats: BeatOut[]
  entity: string
  region: string
  layer: Layer | null
  shape: Shape
  affected: string[]
  report: ReportOut
  score: ScoreOut
}

/** The instruments that keep the demo honest. */
export interface HonestPanelOut {
  abstention: ReportOut | null
  n_decoys: number
  n_decoys_fired: number
  false_positive_rate: number
  n_non_fault_intervals: number
  n_spurious_intervals: number
}

export interface ConsoleOut {
  title: string
  subtitle: string
  config_summary: string
  fault_panels: FaultPanelOut[]
  honest: HonestPanelOut
  scorecard: ScorecardOut
}

// ---------------------------------------------------------------------------
// The live stream (WebSocket)
// ---------------------------------------------------------------------------

/** One interval, replayed: a magnitude summary and whatever the engine concluded. */
export interface StreamFrameOut {
  type: 'frame'
  timestamp: number
  total_intervals: number
  n_core_records: number
  mean_magnitude: number
  max_magnitude: number
  diagnoses: DiagnosisOut[]
  /**
   * Ground-truth fault ids whose onset is this interval. Shown so the UI can mark when
   * a fault began, versus when the engine caught it - the gap is the lead time.
   */
  fault_onsets: string[]
}

export interface StreamEndOut {
  type: 'end'
  total_intervals: number
}

export interface StreamErrorOut {
  type: 'error'
  detail: string
}

export type StreamMessage = StreamFrameOut | StreamEndOut | StreamErrorOut