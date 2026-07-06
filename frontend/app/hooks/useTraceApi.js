import { useState, useRef, useEffect } from "react"

export function useTraceApi() {
  const [options, setOptions] = useState({
    refineries: [],
    buyers: [],
    products: [],
  })

  const [orders, setOrders] = useState([])
  const [results, setResults] = useState([])
  const [activeResultIndex, setActiveResultIndex] = useState(0)
  const [activeOptionIndex, setActiveOptionIndex] = useState(0) 
  const [loading, setLoading] = useState(false)
  const [optLoading, setOptLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showSuccessPopup, setShowSuccessPopup] = useState(false)
  const [isInputCollapsed, setIsInputCollapsed] = useState(false)
  const [showTradeOffer, setShowTradeOffer] = useState(false)

  const popupTimerRef = useRef(null)

  useEffect(() => {
    fetch(`/api/backend/api/options`)
    .then((res) => res.json())
    .then((data) => setOptions(data))
    .catch(() =>
      setError("Gagal terhubung ke server. Pastikan FastAPI sudah berjalan di port 8000.")
    )
    .finally(() => setOptLoading(false))

    return () => {
      if (popupTimerRef.current) {
        clearTimeout(popupTimerRef.current)
      }
    }
  }, [])

  const showCompletedPopup = () => {
    setShowSuccessPopup(true)

    if (popupTimerRef.current) {
      clearTimeout(popupTimerRef.current)
    }

    popupTimerRef.current = setTimeout(() => {
      setShowSuccessPopup(false)
    }, 550)
  }

  const handleAddOrder = (order) => {
    setOrders((prev) => [...prev, order])
    setResults([])
    setShowSuccessPopup(false)
    setIsInputCollapsed(false)
    setActiveResultIndex(0)
    setActiveOptionIndex(0)
  }

  const handleRemoveOrder = (index) => {
    setOrders((prev) => prev.filter((_, i) => i !== index))
    setResults([])
    setShowSuccessPopup(false)
    setIsInputCollapsed(false)
    setActiveResultIndex(0)
    setActiveOptionIndex(0)
  }

  const handleGenerate = async () => {
    if (!orders.length) return

    setLoading(true)
    setError(null)
    setResults([])
    setShowSuccessPopup(false)

    const controller = new AbortController()

    const timeoutId = setTimeout(() => {
      controller.abort()
    }, 300000)

    try {
      const res = await fetch(`/api/backend/api/trace`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ orders }),
        signal: controller.signal,
      })

      const text = await res.text()

      let data
      try {
        data = JSON.parse(text)
      } catch (parseError) {
        throw new Error(text || "Backend returned a non-JSON response.")
      }

      if (!res.ok) {
        throw new Error(
          data?.message ||
            data?.detail ||
            "Terjadi kesalahan saat tracing."
        )
      }

      if (data.job_id) {
        while (true) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          const statusRes = await fetch(`/api/backend/api/status/${data.job_id}`, { signal: controller.signal });
          const statusData = await statusRes.json();
          
          if (!statusRes.ok) throw new Error(statusData.detail || "Polling failed");
          
          if (statusData.status === "COMPLETED") {
             data = statusData.result;
             break;
          } else if (statusData.status === "FAILED") {
             throw new Error(statusData.error || "Trace job failed");
          } else if (statusData.status === "UNKNOWN") {
             throw new Error("Job not found");
          }
        }
      }

      const generatedOrders = data.results || data.orders || []

      setResults(generatedOrders)
      setActiveResultIndex(0)
      setActiveOptionIndex(0)
      setIsInputCollapsed(true)
      showCompletedPopup()
    } catch (err) {
      if (err.name === "AbortError") {
        setError("Recommendation generation took too long and was cancelled after 120 seconds.")
      } else {
        setError(err.message || "Terjadi kesalahan saat tracing.")
      }
    } finally {
      clearTimeout(timeoutId)
      setLoading(false)
    }
  }

  const handleChangeActiveResult = (index) => {
    setActiveResultIndex(index)
    setActiveOptionIndex(0) 
  }

  return {
    options,
    orders,
    results,
    activeResultIndex,
    activeOptionIndex,
    loading,
    optLoading,
    error,
    showSuccessPopup,
    isInputCollapsed,
    showTradeOffer,
    setActiveOptionIndex,
    setShowTradeOffer,
    setIsInputCollapsed,
    handleAddOrder,
    handleRemoveOrder,
    handleGenerate,
    handleChangeActiveResult
  }
}
