export default function EmptyResultState() {
  return (
    <div className="rounded-2xl border border-dashed border-gray-200 bg-white px-8 py-14 text-center">
      <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-50 border border-gray-100">
        <svg className="h-8 w-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
      </div>
      <h3 className="text-base font-bold text-gray-800">
        No Recommendation Generated Yet
      </h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-gray-500">
        Fill in the order details above — refinery, product, and volume — then click
        <span className="font-semibold text-gray-700"> Generate Recommendation</span>.
      </p>
      <div className="mx-auto mt-7 grid max-w-lg grid-cols-1 gap-3 sm:grid-cols-3 text-left">
        {[
          { icon: "📦", title: "Stock Check", desc: "See how much is already available in refinery storage" },
          { icon: "🔗", title: "Trace Route", desc: "Discover which mills & estates can cover the gap" },
          { icon: "📅", title: "ETA Estimate", desc: "Get a realistic lead time and completion date" },
        ].map((item) => (
          <div key={item.title} className="rounded-xl border border-gray-100 bg-gray-50 p-4">
            <div className="text-xl mb-2">{item.icon}</div>
            <p className="text-xs font-bold text-gray-700">{item.title}</p>
            <p className="text-xs text-gray-400 mt-1 leading-relaxed">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
