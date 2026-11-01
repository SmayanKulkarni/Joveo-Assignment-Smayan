import { createContext, useContext, useEffect, useRef } from "react"
import type { RefObject } from "react"
import { gsap } from "gsap"
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin"
import { MotionPathPlugin } from "gsap/MotionPathPlugin"
import { useGSAP } from "@gsap/react"

gsap.registerPlugin(useGSAP, DrawSVGPlugin, MotionPathPlugin)

export const DUR = { fast: 0.15, base: 0.25, slow: 0.5 }
export const EASE = { out: "power2.out", pop: "back.out(3)", linear: "none", settle: "elastic.out(1.2,0.3)" }

// False until a Run's replay has caught up, so a reload or reopened Run plays no one-shot.
export const AnimateContext = createContext(false)
export const useAnimate = () => useContext(AnimateContext)

// Reduced motion simply registers no tweens, and React has already rendered every final state.
export function useMotion(fn: () => void, deps: unknown[], scope: RefObject<Element | null>) {
  useGSAP(
    () => {
      gsap.matchMedia().add("(prefers-reduced-motion: no-preference)", fn)
    },
    { dependencies: deps, scope, revertOnUpdate: true },
  )
}

// The value this component rendered with last time: undefined on mount, so an entry reads differently from a re-render.
export function usePrevious<T>(value: T): T | undefined {
  const last = useRef<T>(undefined)
  const before = last.current
  useEffect(() => {
    last.current = value
  })
  return before
}

export { gsap }
