/**
 * Reusable Badge component for status indicators and labels
 * Supports multiple color schemes and sizes
 */

const colorSchemes = {
  green: "bg-green-50 border-green-200 text-green-700",
  red: "bg-red-50 border-red-200 text-red-700",
  yellow: "bg-yellow-50 border-yellow-200 text-yellow-700",
  orange: "bg-orange-50 border-orange-200 text-orange-700",
  blue: "bg-blue-50 border-blue-200 text-blue-700",
  purple: "bg-purple-50 border-purple-200 text-purple-700",
  gray: "bg-gray-100 border-gray-200 text-gray-600",
  emerald: "bg-emerald-50 border-emerald-200 text-emerald-700",
  cyan: "bg-cyan-50 border-cyan-200 text-cyan-700",
  pink: "bg-pink-50 border-pink-200 text-pink-700",
}

const sizes = {
  xs: "text-[9px] px-1.5 py-0.5",
  sm: "text-[10px] px-2 py-0.5",
  md: "text-[11px] px-2.5 py-0.5",
  lg: "text-xs px-3 py-1",
}

export default function Badge({ 
  children, 
  color = "gray", 
  size = "md",
  className = "",
  icon,
  dot = false
}) {
  const colorClass = colorSchemes[color] || colorSchemes.gray
  const sizeClass = sizes[size] || sizes.md
  
  return (
    <span 
      className={`inline-flex items-center gap-1 border rounded-full font-bold whitespace-nowrap ${colorClass} ${sizeClass} ${className}`}
      role="status"
      aria-label={typeof children === 'string' ? children : undefined}
    >
      {dot && (
        <span 
          className="w-1.5 h-1.5 rounded-full bg-current"
          aria-hidden="true"
        />
      )}
      {icon && <span aria-hidden="true">{icon}</span>}
      {children}
    </span>
  )
}

/**
 * Status Badge with predefined states
 */
export function StatusBadge({ status, size = "md" }) {
  const statusConfig = {
    OPTIMAL: { color: "green", icon: "✓", label: "Optimal" },
    ACCEPTABLE: { color: "yellow", icon: "~", label: "Acceptable" },
    RISKY: { color: "red", icon: "⚠", label: "Risky" },
    CRITICAL: { color: "red", icon: "🚨", label: "Critical" },
    WARNING: { color: "orange", icon: "⚠️", label: "Warning" },
    NORMAL: { color: "green", icon: "✓", label: "Normal" },
    SAFE: { color: "green", icon: "✓", label: "Safe" },
    FULFILLED: { color: "green", icon: "✅", label: "Fulfilled" },
    MINOR: { color: "yellow", icon: "⚠", label: "Minor" },
    MODERATE: { color: "orange", icon: "⚠️", label: "Moderate" },
  }
  
  const config = statusConfig[status] || { color: "gray", icon: "?", label: status }
  
  return (
    <Badge color={config.color} size={size}>
      <span aria-hidden="true">{config.icon}</span>
      {config.label}
    </Badge>
  )
}

/**
 * Trend Badge with direction indicator
 */
export function TrendBadge({ direction, value, size = "md" }) {
  const isPositive = direction === "improving" || direction === "down"
  const color = isPositive ? "green" : "red"
  const arrow = isPositive ? "↘" : "↗"
  
  return (
    <Badge color={color} size={size} dot>
      <span aria-hidden="true">{arrow}</span>
      {value !== undefined && `${Math.abs(value)}%`}
    </Badge>
  )
}