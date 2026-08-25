import { API_BASE_URL, extractErrorMessage } from './planner'

const FALLBACK_PRICE_INR_PER_GRAM = 7500

export async function fetchGoldPrice() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/gold-price`)
    const data = await response.json()

    if (!response.ok) {
      throw new Error(extractErrorMessage(data, response.status))
    }

    return data
  } catch {
    // Network failure or backend down — mirror the backend's own fallback
    // so the gold section still shows a usable estimate.
    return {
      price_per_gram_inr: FALLBACK_PRICE_INR_PER_GRAM,
      source: 'fallback',
      timestamp: new Date().toISOString(),
    }
  }
}
