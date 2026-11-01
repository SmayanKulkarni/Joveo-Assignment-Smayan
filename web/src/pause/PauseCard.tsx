import { useRef } from "react"
import type { Pause } from "../api/types"
import { DUR, EASE, gsap, useAnimate, useMotion } from "../motion"
import { ClarifyForm } from "./ClarifyForm"
import { LowDataForm } from "./LowDataForm"
import { PlanReviewForm } from "./PlanReviewForm"
import type { Send } from "./submit"

function Form({ pause, send }: { pause: Pause; send: Send }) {
  switch (pause.kind) {
    case "clarify":
      return <ClarifyForm questions={pause.payload.questions} send={send} />
    case "plan_review":
      return <PlanReviewForm plan={pause.payload.plan} assumptions={pause.payload.assumptions} callsLeft={pause.payload.calls_left} send={send} />
    case "low_data_review":
      return <LowDataForm payload={pause.payload} send={send} />
  }
}

// The card slides in, then a border ring pulses twice to say it is waiting for you.
export function PauseCard({ pause, send }: { pause: Pause; send: Send }) {
  const box = useRef<HTMLDivElement>(null)
  const animate = useAnimate()
  useMotion(
    () => {
      if (!animate) return
      gsap.from(box.current, { y: 8, opacity: 0, duration: DUR.base, ease: EASE.out })
      gsap.fromTo(".pulse", { opacity: 0.9 }, { opacity: 0, duration: 0.6, ease: EASE.out, repeat: 1, delay: DUR.base })
    },
    [],
    box,
  )
  return (
    <div ref={box} className="pause-box">
      <Form pause={pause} send={send} />
      <i className="pulse" aria-hidden />
    </div>
  )
}
