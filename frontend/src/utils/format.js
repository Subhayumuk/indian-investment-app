export function formatInr(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return 'INR 0'
  return `INR ${num.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

export function formatLocal(value, currency) {
  const num = Number(value)
  if (!Number.isFinite(num)) return `${currency ?? ''} 0`
  return `${currency ?? ''} ${num.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

export function formatPercent(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0%'
  return `${num}%`
}

export function sumField(arr, key) {
  return (arr ?? []).reduce((sum, row) => sum + (Number(row[key]) || 0), 0)
}
