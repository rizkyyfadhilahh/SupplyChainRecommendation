export default function ResultPagination({ results, activeIndex, onChange }) {
  const total = results.length
  if (total <= 1) return null

  const goPrevious = () => onChange(Math.max(activeIndex - 1, 0))
  const goNext = () => onChange(Math.min(activeIndex + 1, total - 1))

  return (
    <div className="flex items-center gap-3">
      <span className="text-s text-gray-600 font-medium whitespace-nowrap">
        Showing Order {activeIndex + 1} from {total}
      </span>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={goPrevious}
          disabled={activeIndex === 0}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <button
          type="button"
          onClick={goNext}
          disabled={activeIndex === total - 1}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  )
}
