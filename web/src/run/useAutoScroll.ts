import { useEffect, useLayoutEffect, useRef, useState } from "react"

const NEAR_PX = 80

// Keeps the end of the stream in view while it is within 80 px of the viewport; scrolling up lets go.
export function useAutoScroll(follow: boolean, changed: unknown) {
  const end = useRef<HTMLDivElement>(null)
  const stuck = useRef(true)
  const [away, setAway] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        stuck.current = entry.isIntersecting
        setAway(!entry.isIntersecting)
      },
      { rootMargin: `0px 0px ${NEAR_PX}px 0px` },
    )
    observer.observe(end.current!)
    return () => observer.disconnect()
  }, [])

  // One write per flush: state changes once per frame. The observer hasn't heard of the growth yet, so stuck is still the answer from before it.
  useLayoutEffect(() => {
    if (follow && stuck.current) end.current?.scrollIntoView({ block: "end" })
  }, [follow, changed])

  const jump = () => end.current?.scrollIntoView({ block: "end", behavior: "smooth" })
  return { end, away, stuck, jump }
}
