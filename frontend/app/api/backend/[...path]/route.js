const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"
const BACKEND_API_KEY = process.env.BACKEND_API_KEY

console.log("DEBUG BACKEND_URL:", BACKEND_URL)
console.log("DEBUG BACKEND_API_KEY:", BACKEND_API_KEY)

export async function GET(request, { params }) {
  const path = params.path.join("/")
  const { searchParams } = new URL(request.url)
  const query = searchParams.toString()
  const url = `${BACKEND_URL}/${path}${query ? "?" + query : ""}`

  console.log("DEBUG proxying GET to:", url)

  const res = await fetch(url, {
    headers: { "X-API-Key": BACKEND_API_KEY },
  })
  const data = await res.json()
  return Response.json(data, { status: res.status })
}

export async function POST(request, { params }) {
  const path = params.path.join("/")
  const body = await request.text()
  const url = `${BACKEND_URL}/${path}`

  console.log("DEBUG proxying POST to:", url)

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": BACKEND_API_KEY,
    },
    body,
  })
  const data = await res.json()
  return Response.json(data, { status: res.status })
}