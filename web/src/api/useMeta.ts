import { useEffect, useState, useSyncExternalStore } from "react"
import { getMeta } from "./client"
import type { Meta } from "./types"

const RETRY_MS = 5000
const TRIES = 24 // two minutes: a sleeping free host takes about one to wake

type Wake = "ok" | "waking" | "failed"

let cached: Promise<Meta> | null = null
let wake: Wake = "ok"
const listeners = new Set<() => void>()

function setWake(next: Wake) {
  wake = next
  listeners.forEach((listener) => listener())
}

async function loadMeta(): Promise<Meta> {
  for (let tries = TRIES; ; tries--) {
    try {
      const meta = await getMeta()
      setWake("ok")
      return meta
    } catch (e) {
      if (tries <= 1) {
        setWake("failed")
        throw e
      }
      setWake("waking")
      await new Promise((resolve) => setTimeout(resolve, RETRY_MS))
    }
  }
}

// /meta never changes while the server runs, so one fetch serves every component.
export function useMeta(): Meta | null {
  const [meta, setMeta] = useState<Meta | null>(null)
  useEffect(() => {
    cached ??= loadMeta().catch((e) => {
      cached = null // let the next mount try again
      throw e
    })
    cached.then(setMeta, () => {})
  }, [])
  return meta
}

export function useWake(): Wake {
  useMeta() // starts the load on every page, including the Composer, which needs no Meta itself
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => void listeners.delete(listener)
    },
    () => wake,
  )
}
