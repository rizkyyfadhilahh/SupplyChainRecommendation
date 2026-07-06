export default function SuccessPopup({ show }) {
  if (!show) return null

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-gray-900/25 backdrop-blur-[1px]">
      <div className="success-popup w-[360px] overflow-hidden rounded-3xl bg-white shadow-2xl border border-pink-100">
        <div className="relative bg-gradient-to-br from-pink-50 via-rose-50 to-white px-6 pt-8 pb-6 text-center">
          <div className="absolute left-10 top-8 h-2 w-2 rounded-full bg-pink-300" />
          <div className="absolute right-12 top-10 h-1.5 w-1.5 rounded-full bg-rose-300" />
          <div className="absolute left-20 bottom-7 h-1.5 w-1.5 rounded-full bg-pink-200" />
          <div className="absolute right-20 bottom-8 h-2 w-2 rounded-full bg-rose-200" />

          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-pink-500 text-white shadow-lg shadow-pink-200">
            <svg
              className="h-10 w-10"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2.8"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </div>

        <div className="px-8 py-8 text-center">
          <p className="text-2xl font-semibold leading-snug text-gray-900">
            Your Recommendation
            <br />
            generated successfully.
          </p>
        </div>
      </div>
    </div>
  )
}
