import type { Pause } from "../api/types"
import { ClarifyForm } from "./ClarifyForm"
import { LowDataForm } from "./LowDataForm"
import { PlanReviewForm } from "./PlanReviewForm"
import type { Send } from "./submit"

export function PauseCard({ pause, send }: { pause: Pause; send: Send }) {
  switch (pause.kind) {
    case "clarify":
      return <ClarifyForm questions={pause.payload.questions} send={send} />
    case "plan_review":
      return <PlanReviewForm plan={pause.payload.plan} assumptions={pause.payload.assumptions} send={send} />
    case "low_data_review":
      return <LowDataForm payload={pause.payload} send={send} />
  }
}
