/**
 * The live stream, as a WebSocket.
 *
 * The server replays a run one interval at a time. We ask it to replay as fast as it
 * can compute (interval_ms=0) and buffer every frame, rather than pacing playback over
 * the socket. That separation matters: the socket carries *what happened*, and the
 * transport bar decides *when the operator sees it*. Scrubbing, pausing and changing
 * speed then cost nothing and cannot desynchronise from the engine, because the frames
 * are already in hand.
 */

import type { StreamFrameOut, StreamMessage } from './types'

export interface StreamHandlers {
  onFrame: (frame: StreamFrameOut) => void
  onEnd: (totalIntervals: number) => void
  onError: (detail: string) => void
}

/** The socket URL, on whatever host is serving the page. */
function streamUrl(runId: string, intervalMs: number): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/runs/${runId}/stream?interval_ms=${intervalMs}`
}

/**
 * Open the stream. Returns a close function; call it on unmount, which is also what
 * makes React's StrictMode double-mount harmless.
 */
export function openStream(
  runId: string,
  handlers: StreamHandlers,
  intervalMs = 0,
): () => void {
  const socket = new WebSocket(streamUrl(runId, intervalMs))
  let closedByUs = false

  socket.onmessage = (event) => {
    const message = JSON.parse(event.data as string) as StreamMessage
    switch (message.type) {
      case 'frame':
        handlers.onFrame(message)
        break
      case 'end':
        handlers.onEnd(message.total_intervals)
        break
      case 'error':
        handlers.onError(message.detail)
        break
    }
  }

  socket.onerror = () => {
    if (!closedByUs) handlers.onError('The live stream connection failed.')
  }

  return () => {
    closedByUs = true
    // Only close a socket that has finished opening; closing during CONNECTING throws.
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close()
    }
  }
}