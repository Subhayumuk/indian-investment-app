import { API_BASE_URL, extractErrorMessage } from './planner'

export async function runHoldingsReview(payload) {
  const response = await fetch(`${API_BASE_URL}/api/holdings-review`, {
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
