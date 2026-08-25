import { API_BASE_URL, extractErrorMessage } from './planner'

export async function parseCas(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/parse-cas`, {
    method: 'POST',
    body: formData,
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, response.status))
  }

  return data
}
