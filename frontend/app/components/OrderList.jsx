"use client"

export default function OrderList({ orders, onRemove, onGenerate, loading }) {
  if (orders.length === 0) return null

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-gray-100 bg-white px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-base font-bold text-gray-900">
            <span className="h-2 w-2 rounded-full bg-rose-500"></span>
            Order Queue
          </h2>
          <p className="text-sm font-medium text-slate-500 mt-1 ml-4">
            {orders.length} order{orders.length > 1 ? "s" : ""} pending processing
          </p>
        </div>
        <button
          onClick={onGenerate}
          disabled={loading}
          className="bg-red-700 hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium px-6 py-2.5 rounded-xl transition flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 w-4 h-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Processing...
            </>
          ) : (
            <>
              Generate Recommendation
            </>
          )}
        </button>
      </div>

      <div className="p-4 flex flex-col gap-2 bg-slate-50/30">
        {orders.map((order, i) => (
          <div
            key={i}
            className="group flex flex-col sm:flex-row sm:items-center justify-between bg-white rounded-xl px-5 py-4 border border-slate-100 shadow-sm hover:shadow-md hover:border-blue-200 transition-all gap-4 sm:gap-0 relative overflow-hidden"
          >
            {/* Aksen Biru tipis di sebelah kiri tiap kartu */}
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500/0 group-hover:bg-blue-500 transition-colors"></div>

            <div className="flex items-center gap-5 sm:gap-8 flex-1 pl-2">
              {/* Nomor Order */}
              <div className="flex flex-col items-center justify-center bg-blue-50 h-10 w-10 rounded-lg border border-blue-100 shrink-0">
                <span className="text-[10px] font-bold text-blue-400 leading-none mb-0.5">Order</span>
                <span className="text-sm font-extrabold text-blue-700 leading-none">#{i + 1}</span>
              </div>

              {/* Data Order dengan Layout Grid sejajar */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-x-6 gap-y-2 w-full items-center">
                
                <div className="flex flex-col">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-0.5">Refinery</span>
                  <span className="text-sm font-bold text-slate-800 truncate" title={order.facility}>{order.facility}</span>
                </div>

                <div className="flex flex-col">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-0.5">Product</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-800">{order.product}</span>
                    {order.spec === "EUDR" && (
                      <span className="text-[9px] font-extrabold px-1.5 py-0.5 bg-green-100 text-green-700 rounded ring-1 ring-inset ring-green-200">EUDR</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-0.5">Demand</span>
                  <span className="text-sm font-bold text-slate-800">{Number(order.quantity).toLocaleString()} <span className="text-xs text-slate-400 font-medium">Kg</span></span>
                </div>

                <div className="flex flex-col">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-0.5">
                    Buyer
                  </span>

                  {order.buyer ? (
                    <span
                      className="w-fit max-w-[120px] truncate rounded-md border border-purple-100 bg-purple-50 px-2 py-0.5 text-[10px] font-bold text-purple-700"
                      title={order.buyer}
                    >
                      {order.buyer}
                    </span>
                  ) : (
                    <span className="text-xs font-medium text-slate-300">-</span>
                  )}
                </div>

                <div className="flex flex-col">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-0.5">
                    Target Days
                  </span>

                  {order.target_total_days ? (
                    <span className="w-fit rounded-md border border-orange-100 bg-orange-50 px-2 py-0.5 text-[10px] font-bold text-orange-700">
                      {order.target_total_days}d Target
                    </span>
                  ) : (
                    <span className="text-xs font-medium text-slate-300">-</span>
                  )}
                </div>

              </div>
            </div>

            {/* Tombol Hapus */}
            <button
              onClick={() => onRemove(i)}
              className="absolute right-4 top-1/2 -translate-y-1/2 sm:static sm:translate-y-0 h-8 w-8 flex items-center justify-center rounded-full text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
              title="Remove Order"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}