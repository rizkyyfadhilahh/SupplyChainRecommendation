import { Suspense } from "react"
import DrilldownDashboard from "../components/DrilldownDashboard"

export default function DrilldownPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen text-gray-400">Loading...</div>}>
      <DrilldownDashboard />
    </Suspense>
  )
}
