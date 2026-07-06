"use client"

import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"
import SLOCConfigManager from "../components/SLOCConfigManager"

const NAV_LINKS = [
  { href: "/", label: "Recommendation" },
  { href: "/drilldown", label: "Drill-Down" },
  { href: "/sloc", label: "SLOC Config" },
]

export default function SLOCPage() {
  const pathname = usePathname()
  const [options, setOptions] = useState({
    refineries: [],
    buyers: [],
    products: [],
  })

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch("/api/backend/api/options")
      .then((res) => res.json())
      .then((data) => setOptions(data))
      .catch(() =>
        setError("Gagal terhubung ke server. Pastikan FastAPI sudah berjalan di port 8000.")
      )
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">


      <main className="w-full max-w-[98vw] mx-auto px-3 md:px-4 py-8 flex flex-col gap-6">

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 flex items-center gap-2">
            <span>⚠️</span>
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center font-semibold text-sm text-gray-400">
            Loading SLOC configuration...
          </div>
        ) : (
          <SLOCConfigManager options={options} />
        )}
      </main>
    </div>
  )
}