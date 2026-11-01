import { useEffect, useState } from "react"
import { getMeta } from "./client"
import type { Meta } from "./types"

let cached: Promise<Meta> | null = null

// /meta never changes while the server runs, so one fetch serves every component.
export function useMeta(): Meta | null {
  const [meta, setMeta] = useState<Meta | null>(null)
  useEffect(() => {
    cached ??= getMeta().catch((e) => {
      cached = null // let the next mount try again
      throw e
    })
    cached.then(setMeta, () => {})
  }, [])
  return meta
}
