"use client"

import { usePathname } from "next/navigation"

const NAV_LINKS = [
  { href: "/", label: "Recommendation" },
  { href: "/drilldown", label: "Drill-Down" },
  { href: "/gap-analysis", label: "Gap Analysis" },
  { href: "/sloc", label: "SLOC Config" },
]

export default function Navbar() {
  const pathname = usePathname()

  return (
    <nav className="bg-white border-b border-gray-100 px-14 py-4 flex items-center gap-10 sticky top-0 z-50">
      <div className="flex items-center shrink-0">
        <img
          src="/logo.png"
          alt="Logo"
          className="h-11 w-auto object-contain"
        />
      </div>

      <div className="flex items-center gap-2">
        {NAV_LINKS.map(({ href, label }) => {
          const isActive = pathname === href || (href !== "/" && pathname?.startsWith(href))

          return (
            <a
              key={href}
              href={href}
              className={`relative text-[15px] font-medium leading-6 px-3 py-2 rounded-md transition-all duration-200 ${
                isActive
                  ? "text-[#101828] font-semibold"
                  : "text-[#98a2b3] hover:bg-gray-50 hover:text-[#101828]"
              }`}
            >
              {label}
              {isActive && (
                <span className="absolute bottom-0 left-3 right-3 h-0.5 rounded-full bg-rose-500" />
              )}
            </a>
          )
        })}
      </div>
    </nav>
  )
}
