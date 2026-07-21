/**
 * The only place the frontend talks to si_api.
 *
 * Every call goes through `request`, so an error from the server surfaces the same way
 * everywhere: the API returns `{detail: "..."}` on 404 and 409, and that sentence is
 * written for a human, so we show it rather than inventing our own.
 *
 * In development Vite proxies /api to uvicorn (see vite.config.ts). In production the
 * API serves the built app itself, so the same relative paths work unchanged.
 */

import type { Lang } from '../lib/i18n'
import type {
  ConsoleOut,
  HealthOut,
  RunOut,
  RunRequest,
  ScorecardOut,
  TopologyOut,
} from './types'

const BASE = '/api'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'content-type': 'application/json', ...init?.headers },
    })
  } catch {
    // fetch only rejects when the request never completed: the API is not up.
    throw new ApiError(0, 'Cannot reach the API. Is uvicorn running on port 8000?')
  }

  if (!response.ok) {
    throw new ApiError(response.status, await detailOf(response))
  }
  return (await response.json()) as T
}

/** The server's own explanation, when it gave one. */
async function detailOf(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail)) return body.detail.map((e: never) => JSON.stringify(e)).join('; ')
  } catch {
    /* not JSON; fall through to the status line */
  }
  return `${response.status} ${response.statusText}`
}

/**
 * The language every read carries.
 *
 * The engine's sentences are rendered server-side, so the client cannot translate them
 * after the fact - it has to ask in the right language. This is module state rather
 * than a parameter on twenty call sites because the language is a property of the
 * session, not of any one request, and the WebSocket needs it too.
 */
let currentLang: Lang = 'en'

export function setApiLang(lang: Lang): void {
  currentLang = lang
}

export function apiLang(): Lang {
  return currentLang
}

/** Append `lang` without caring whether the path already has a query string. */
function withLang(path: string): string {
  return `${path}${path.includes('?') ? '&' : '?'}lang=${currentLang}`
}

export const api = {
  health: () => request<HealthOut>('/health'),

  /**
   * Start a run.
   *
   * `waitSeconds` blocks the response until the run finishes (a tiny run lands in well
   * under a second, so the caller can simply ask for the answer). `execute` decides who
   * computes it: true (default) runs the batch in the background; false registers the run
   * without computing, so the live stream computes it once and the client renders
   * immediately, watching faults appear rather than waiting for a full-scale run.
   */
  createRun: (body: RunRequest, { waitSeconds = 60, execute = true }: {
    waitSeconds?: number
    execute?: boolean
  } = {}) =>
    request<RunOut>(`/runs?wait_seconds=${waitSeconds}&execute=${execute}`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  listRuns: () => request<RunOut[]>('/runs'),

  getRun: (runId: string) => request<RunOut>(`/runs/${runId}`),

  /** The whole story of the run in one payload. This is what the console renders. */
  getConsole: (runId: string) => request<ConsoleOut>(withLang(`/runs/${runId}/console`)),

  getScorecard: (runId: string) => request<ScorecardOut>(withLang(`/runs/${runId}/scorecard`)),

  getTopology: (runId: string, limit = 2000) =>
    request<TopologyOut>(withLang(`/runs/${runId}/topology?limit=${limit}`)),

  /** The original single-file HTML console, still served by the API. */
  consoleHtmlUrl: (runId: string) => `${BASE}/runs/${runId}/console.html`,
}