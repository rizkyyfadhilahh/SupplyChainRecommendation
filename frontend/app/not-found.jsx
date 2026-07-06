import Link from "next/link"

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-10 max-w-lg w-full text-center">

        {/* Illustration */}
        <div className="w-20 h-20 rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center text-4xl mx-auto mb-6">
          🗺️
        </div>

        {/* Status code */}
        <p className="text-[11px] font-bold uppercase tracking-widest text-rose-400 mb-2">
          404 — Page Not Found
        </p>

        {/* Heading */}
        <h1 className="text-2xl font-black text-gray-900 mb-3">
          We lost this route
        </h1>

        {/* Description */}
        <p className="text-sm text-gray-500 leading-relaxed mb-8">
          The page you are looking for does not exist or has been moved.
          Try navigating back to one of the pages below.
        </p>

        {/* Navigation links */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {[
            { href: "/",             icon: "📋", label: "Recommendation" },
            { href: "/drilldown",    icon: "🔍", label: "Drill-Down"      },
            { href: "/gap-analysis", icon: "📊", label: "Gap Analysis"    },
            { href: "/sloc",         icon: "🏭", label: "SLOC Config"     },
          ].map(({ href, icon, label }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-2 rounded-xl border border-gray-100 bg-gray-50 hover:border-rose-200 hover:bg-rose-50 px-4 py-3 text-sm font-semibold text-gray-700 transition-all duration-150"
            >
              <span aria-hidden="true">{icon}</span>
              {label}
            </Link>
          ))}
        </div>

        {/* Back link */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-xl bg-gray-900 hover:bg-gray-800 text-white px-6 py-2.5 text-sm font-bold transition-colors"
        >
          ← Back to Home
        </Link>
      </div>
    </div>
  )
}