"use client"

import { useEffect, useState } from "react"
import SLOCConfigManager from "../components/SLOCConfigManager"

export default function SLOCPage() {
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
      <nav className="bg-white border-b border-gray-100 px-14 py-4 flex items-center gap-10 sticky top-0 z-10">
        <div className="flex items-center shrink-0">
          <img
            src="/logo.png"
            alt="Logo"
            className="h-11 w-auto object-contain"
          />
        </div>

        <div className="flex items-center gap-2">
          <a
            href="/"
            className="text-[#98a2b3] text-[16px] not-italic font-medium leading-6 px-3 py-2 rounded-md transition-all duration-500 hover:bg-gray-50 hover:text-[#101828]"
          >
            Recommendation
          </a>

          <a
            href="/sloc"
            className="text-[#98a2b3] text-[16px] not-italic font-medium leading-6 px-3 py-2 rounded-md transition-all duration-500 hover:bg-gray-50 hover:text-[#101828]"
          >
            SLOC Configuration
          </a>
        </div>
      </nav>

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