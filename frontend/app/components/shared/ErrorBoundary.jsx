"use client"

import { Component } from 'react'

/**
 * ErrorBoundary — catches rendering errors in child components.
 * Prevents a single broken widget from crashing the entire page.
 *
 * Usage:
 *   <ErrorBoundary label="SupplyGraph">
 *     <SupplyGraph ... />
 *   </ErrorBoundary>
 */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    const label = this.props.label || 'Unknown'
    console.error(`[ErrorBoundary:${label}]`, error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleRetry)
      }

      return (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <div className="flex items-start gap-3">
            <span className="text-xl shrink-0">⚠️</span>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-bold text-red-900 mb-1">
                {this.props.label
                  ? `Error in ${this.props.label}`
                  : 'Something went wrong'}
              </h3>
              <p className="text-xs text-red-700 break-words">
                {this.state.error?.message || 'An unexpected rendering error occurred.'}
              </p>
              <button
                onClick={this.handleRetry}
                className="mt-3 rounded-lg bg-red-600 text-white px-3 py-1.5 text-xs font-bold hover:bg-red-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary