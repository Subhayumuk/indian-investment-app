// In dev (`npm run dev`), the frontend runs on its own Vite port (5173) and
// must reach the backend directly on 127.0.0.1:8000. In a production build
// (`npm run build`), the backend serves this same build from one origin
// (see app/main.py), so requests should be relative — an absolute
// 127.0.0.1 URL baked into the build would point at *the visitor's own
// machine*, not the server, once deployed.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

export function extractErrorMessage(data, status) {
  // FastAPI HTTPException -> {"detail": "message"}
  // FastAPI validation error -> {"detail": [{"loc": [...], "msg": "...", ...}, ...]}
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((err) => (err.loc ? `${err.loc.join('.')}: ${err.msg}` : err.msg))
      .join('; ')
  }
  return `Backend error (${status})`
}

export async function runPlanner(payload) {
  const response = await fetch(`${API_BASE_URL}/api/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, response.status))
  }

  return data
}
