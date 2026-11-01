import { useRef } from "react"
import { DUR, EASE, gsap, useAnimate, useMotion, usePrevious } from "../motion"

// A bar that fills by scaleX, so growing it never touches layout.
export function Bar({ value, max, label, className = "", dur = DUR.base }: { value: number; max: number; label: string; className?: string; dur?: number }) {
  const fill = useRef<HTMLElement>(null)
  const animate = useAnimate()
  const ratio = max > 0 ? Math.min(value / max, 1) : 0
  const before = usePrevious(ratio)

  useMotion(
    () => {
      if (animate && before !== undefined && before !== ratio) gsap.fromTo(fill.current, { scaleX: before }, { scaleX: ratio, duration: dur, ease: EASE.out })
    },
    [ratio],
    fill,
  )
  return (
    <span className={`bar ${className}`} role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
      <i ref={fill} style={{ transform: `scaleX(${ratio})` }} />
    </span>
  )
}
