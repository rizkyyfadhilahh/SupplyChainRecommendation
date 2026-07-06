/**
 * Reusable Card component with consistent styling
 * Provides base container for all dashboard widgets
 */

export default function Card({ children, className = "", style, onClick }) {
  return (
    <div 
      className={`bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden ${className}`}
      style={style}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyPress={onClick ? (e) => e.key === 'Enter' && onClick(e) : undefined}
    >
      {children}
    </div>
  )
}

/**
 * Card Header component
 */
export function CardHeader({ title, subtitle, icon, badge, right, className = "" }) {
  return (
    <div className={`px-5 py-4 border-b border-gray-100 flex items-center justify-between gap-3 ${className}`}>
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {icon && <span className="text-xl shrink-0" role="img" aria-label="icon">{icon}</span>}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-bold text-gray-900">{title}</h3>
            {badge}
          </div>
          {subtitle && (
            <p className="text-xs text-gray-400 mt-0.5 truncate">{subtitle}</p>
          )}
        </div>
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  )
}

/**
 * Card Body component
 */
export function CardBody({ children, className = "" }) {
  return (
    <div className={`p-5 ${className}`}>
      {children}
    </div>
  )
}

/**
 * Card Footer component
 */
export function CardFooter({ children, className = "" }) {
  return (
    <div className={`px-5 py-4 border-t border-gray-100 bg-gray-50 ${className}`}>
      {children}
    </div>
  )
}