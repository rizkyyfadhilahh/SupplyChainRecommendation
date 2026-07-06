const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"
const BACKEND_API_KEY = process.env.BACKEND_API_KEY

// Strict allowlist of proxied backend paths.
// Any path not in this set returns 404 at the proxy layer,
// providing defense-in-depth independent of the backend auth guard.
const ALLOWED_PATHS = new Set([
  "health",
  "api/options",
  "api/buyers",
  "api/gap-analysis",
  "api/gap-fulfillment",
  "api/sloc-master",
  "api/sloc-config",
  "api/stock-refresh",
  "api/trace",
  "api/drilldown/buyers",
  "api/drilldown/product-context",
  "api/drilldown/resolve-gap",
  "api/drilldown/capacity-heatmap",
])

// Server-side request timeout (ms). Guards the proxy-to-backend leg
// independently of the client-side AbortController in the browser.
const PROXY_TIMEOUT_MS = 30_000

export async function GET(request, { params }) {
  try {
    const path = params.path.join("/")
    const isAllowed = ALLOWED_PATHS.has(path) || path.startsWith("api/status/")
    
    if (!isAllowed) {
      return Response.json({ detail: "Not Found" }, { status: 404 })
    }

    const { searchParams } = new URL(request.url)
    const query = searchParams.toString()
    const url = `${BACKEND_URL}/${path}${query ? "?" + query : ""}`

    const res = await fetch(url, {
      headers: { "X-API-Key": BACKEND_API_KEY },
      signal: AbortSignal.timeout(PROXY_TIMEOUT_MS),
    })
    
    // Stream response directly to avoid memory/size limits on large JSONs
    return new Response(res.body, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "application/json",
      },
    })
  } catch (err) {
    return Response.json({ detail: err.message || "Proxy GET error" }, { status: 500 })
  }
}

export async function POST(request, { params }) {
  try {
    const path = params.path.join("/")

    if (!ALLOWED_PATHS.has(path)) {
      return Response.json({ detail: "Not Found" }, { status: 404 })
    }

    const body = await request.text()
    const url = `${BACKEND_URL}/${path}`

    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": BACKEND_API_KEY,
      },
      body,
      signal: AbortSignal.timeout(PROXY_TIMEOUT_MS),
    })
    
    // Stream response directly
    return new Response(res.body, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "application/json",
      },
    })
  } catch (err) {
    return Response.json({ detail: err.message || "Proxy POST error" }, { status: 500 })
  }
}
