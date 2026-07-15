/**
 * The replay: the run's intervals, buffered from the socket, then played back locally.
 *
 * Two things are deliberately separate here.
 *
 *   Buffering  the socket delivers every interval as fast as the engine can compute it.
 *              We keep them all. This is the honest record of what the engine saw and
 *              said, interval by interval.
 *
 *   Playback   a local clock walks an index over that buffer. Play, pause, scrub and
 *              speed are therefore instant and cannot drift away from the engine: they
 *              only move a cursor over frames already in hand.
 *
 * That is why the transport can scrub backwards through a fault - something a socket
 * paced at one frame per interval could never do.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { openStream } from '../api/stream'
import type { StreamFrameOut } from '../api/types'
import { isDecoy } from '../lib/format'

/** How long one interval lasts on screen at 1x. The demo is watched, not lived. */
const BASE_FRAME_MS = 220

export const SPEEDS = [1, 2, 4, 8] as const
export type Speed = (typeof SPEEDS)[number]

/** A ground-truth onset, ready for the timeline. */
export interface Onset {
  interval: number
  faultId: string
  decoy: boolean
}

export interface Replay {
  frames: StreamFrameOut[]
  /** Every interval has arrived. */
  complete: boolean
  /** 0..1, how much of the run has been computed so far. */
  progress: number
  error: string | null

  /** The interval the operator is looking at. */
  t: number
  setT: (t: number) => void
  playing: boolean
  togglePlay: () => void
  speed: Speed
  cycleSpeed: () => void
  reset: () => void

  totalIntervals: number
  frame: StreamFrameOut | null
  onsets: Onset[]
}

export function useReplay(runId: string | null, totalIntervals: number): Replay {
  const [frames, setFrames] = useState<StreamFrameOut[]>([])
  const [complete, setComplete] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [t, setT] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<Speed>(1)

  // ----- buffer the run off the socket -----

  useEffect(() => {
    if (!runId) return

    setFrames([])
    setComplete(false)
    setError(null)
    setT(0)
    setPlaying(false)

    // Frames arrive one message at a time; batching them into a single state update per
    // animation frame keeps a 576-interval run from re-rendering the tree 576 times.
    let pending: StreamFrameOut[] = []
    let scheduled = false

    const flush = () => {
      scheduled = false
      if (pending.length === 0) return
      const batch = pending
      pending = []
      setFrames((current) => [...current, ...batch])
    }

    const close = openStream(runId, {
      onFrame: (frame) => {
        pending.push(frame)
        if (!scheduled) {
          scheduled = true
          requestAnimationFrame(flush)
        }
      },
      onEnd: () => {
        flush()
        setComplete(true)
        // The run is buffered and ready, but it waits: the operator presses play to
        // start the story. Nothing moves on its own.
      },
      onError: (detail) => {
        flush()
        setError(detail)
      },
    })

    return () => {
      close()
    }
  }, [runId])

  // ----- walk the cursor over it -----

  const lastIndex = Math.max(0, frames.length - 1)
  const playingRef = useRef(playing)
  playingRef.current = playing

  useEffect(() => {
    if (!playing || frames.length === 0) return

    const id = window.setInterval(() => {
      setT((current) => {
        if (current >= frames.length - 1) {
          // Hold at the end rather than looping: the last interval is the punchline.
          setPlaying(false)
          return current
        }
        return current + 1
      })
    }, BASE_FRAME_MS / speed)

    return () => window.clearInterval(id)
  }, [playing, speed, frames.length])

  const togglePlay = useCallback(() => {
    setPlaying((current) => {
      if (current) return false
      // Pressing play at the very end replays from the start.
      setT((now) => (now >= lastIndex && lastIndex > 0 ? 0 : now))
      return true
    })
  }, [lastIndex])

  const cycleSpeed = useCallback(() => {
    setSpeed((current) => SPEEDS[(SPEEDS.indexOf(current) + 1) % SPEEDS.length])
  }, [])

  const reset = useCallback(() => {
    setPlaying(false)
    setT(0)
  }, [])

  const seek = useCallback(
    (next: number) => {
      setPlaying(false)
      setT(Math.max(0, Math.min(next, Math.max(0, frames.length - 1))))
    },
    [frames.length],
  )

  // ----- what the timeline needs -----

  const onsets = useMemo<Onset[]>(
    () =>
      frames.flatMap((frame) =>
        frame.fault_onsets.map((faultId) => ({
          interval: frame.timestamp,
          faultId,
          decoy: isDecoy(faultId),
        })),
      ),
    [frames],
  )

  const total = frames[0]?.total_intervals ?? totalIntervals
  const progress = total > 0 ? Math.min(1, frames.length / total) : 0

  return {
    frames,
    complete,
    progress,
    error,
    t,
    setT: seek,
    playing,
    togglePlay,
    speed,
    cycleSpeed,
    reset,
    totalIntervals: total,
    frame: frames[t] ?? null,
    onsets,
  }
}