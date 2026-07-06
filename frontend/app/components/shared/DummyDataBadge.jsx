/**
 * DummyDataBadge
 * Small label to indicate that the section displays modelled/demo data,
 * not real operational data. Place in the top-right of any card header
 * that sources from mock/hardcoded data.
 */
export default function DummyDataBadge({ tooltip }) {
  const title =
    tooltip ||
    "This section uses modelled or demo data, not real operational data."

  return (
    <span
      title={title}
      aria-label={title}
      className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700 select-none cursor-help"
    >
      <svg
        className="w-2.5 h-2.5 shrink-0"
        viewBox="0 0 12 12"
        fill="none"
        aria-hidden="true"
      >
        <circle cx="6" cy="6" r="5.5" stroke="#d97706" strokeWidth="1" />
        <text
          x="6"
          y="8.5"
          textAnchor="middle"
          fontSize="7"
          fontWeight="700"
          fill="#d97706"
        >
          i
        </text>
      </svg>
      Demo Data
    </span>
  )
}