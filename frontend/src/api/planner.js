export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

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
