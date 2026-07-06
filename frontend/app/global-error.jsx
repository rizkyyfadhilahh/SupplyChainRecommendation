"use client"

export default function GlobalError({ error, reset }) {
  return (
    <html>
      <body>
        <div style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px",
          fontFamily: "system-ui, -apple-system, sans-serif",
          backgroundColor: "#f9fafb"
        }}>
          <div style={{
            background: "white",
            borderRadius: "16px",
            border: "1px solid #e5e7eb",
            padding: "32px",
            maxWidth: "400px",
            width: "100%",
            textAlign: "center",
            boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
          }}>
            <div style={{ fontSize: "48px", marginBottom: "16px" }}>🚨</div>
            <h2 style={{ fontSize: "18px", fontWeight: "700", color: "#111827", marginBottom: "8px" }}>
              Critical Error
            </h2>
            <p style={{ fontSize: "14px", color: "#6b7280", marginBottom: "24px" }}>
              {error?.message || "A critical error occurred. Please refresh the page."}
            </p>
            <button
              onClick={() => reset()}
              style={{
                backgroundColor: "#111827",
                color: "white",
                border: "none",
                borderRadius: "12px",
                padding: "10px 24px",
                fontSize: "14px",
                fontWeight: "700",
                cursor: "pointer"
              }}
            >
              Refresh Page
            </button>
          </div>
        </div>
      </body>
    </html>
  )
}