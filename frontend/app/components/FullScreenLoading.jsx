export default function FullScreenLoading() {
  const loadingSteps = [
    "Checking stock",
    "Tracing suppliers",
    "Calculating allocation",
    "Estimating schedule",
  ]

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-white">
      <div className="w-full max-w-4xl px-6">
        <div className="rounded-3xl border border-gray-100 bg-white px-8 py-10 text-center shadow-sm">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-rose-50">
            <div className="relative h-11 w-11 animate-[spin_1.2s_linear_infinite]">
              <span className="absolute left-1/2 top-1 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-rose-500" />
              <span className="absolute left-1 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-rose-500" />
              <span className="absolute right-1 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-rose-500" />
              <span className="absolute bottom-1 left-1/2 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-rose-500" />
            </div>
          </div>

          <h2 className="text-lg font-bold text-gray-900">
            Generating supply chain recommendation
          </h2>

          <p className="mx-auto mt-2 max-w-2xl text-sm leading-relaxed text-gray-500">
            The system is checking stock availability, tracing historical suppliers,
            calculating allocation, and estimating the delivery schedule.
          </p>

          <div className="mx-auto mt-7 grid max-w-3xl grid-cols-1 gap-3 md:grid-cols-4">
            {loadingSteps.map((step, index) => (
              <div
                key={step}
                className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-left"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-rose-500 text-xs font-bold text-white">
                    {index + 1}
                  </span>

                  <p className="text-xs font-bold text-gray-700">
                    {step}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="mx-auto mt-7 h-1.5 max-w-xl overflow-hidden rounded-full bg-gray-100">
            <div className="h-full w-1/2 animate-[loadingBar_1.5s_ease-in-out_infinite] rounded-full bg-rose-300" />
          </div>

          <p className="mt-4 text-xs text-gray-400">
            Complex recommendation routes may take longer to process.
          </p>
        </div>

        <style jsx>{`
          @keyframes loadingBar {
            0% {
              transform: translateX(-100%);
            }
            50% {
              transform: translateX(70%);
            }
            100% {
              transform: translateX(220%);
            }
          }
        `}</style>
      </div>
    </div>
  )
}
