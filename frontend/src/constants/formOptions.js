// Countries mirror the backend's DTAA_COUNTRIES reference list in
// agent/agent_logic.py. Exchange rates are illustrative starting points —
// users can override them with the actual rate for their filing date.
export const COUNTRIES = [
  { value: 'Denmark', label: 'Denmark', currency: 'DKK', defaultRate: 11.5 },
  { value: 'USA', label: 'United States', currency: 'USD', defaultRate: 83.5 },
  { value: 'UK', label: 'United Kingdom', currency: 'GBP', defaultRate: 106 },
  { value: 'UAE', label: 'United Arab Emirates', currency: 'AED', defaultRate: 22.7 },
  { value: 'Singapore', label: 'Singapore', currency: 'SGD', defaultRate: 62 },
  { value: 'Canada', label: 'Canada', currency: 'CAD', defaultRate: 61 },
  { value: 'Australia', label: 'Australia', currency: 'AUD', defaultRate: 55 },
  { value: 'Germany', label: 'Germany', currency: 'EUR', defaultRate: 90 },
  { value: 'Netherlands', label: 'Netherlands', currency: 'EUR', defaultRate: 90 },
  { value: 'Sweden', label: 'Sweden', currency: 'SEK', defaultRate: 7.9 },
  { value: 'Norway', label: 'Norway', currency: 'NOK', defaultRate: 7.8 },
  { value: 'New Zealand', label: 'New Zealand', currency: 'NZD', defaultRate: 50 },
  { value: 'Switzerland', label: 'Switzerland', currency: 'CHF', defaultRate: 94 },
  { value: 'France', label: 'France', currency: 'EUR', defaultRate: 90 },
  { value: 'Japan', label: 'Japan', currency: 'JPY', defaultRate: 0.56 },
]

export function currencyForCountry(country) {
  return COUNTRIES.find((c) => c.value === country)?.currency ?? 'USD'
}

export function defaultRateForCountry(country) {
  return COUNTRIES.find((c) => c.value === country)?.defaultRate ?? 1
}

export const INDIAN_RESIDENTIAL_STATUSES = [
  { value: 'NRI', label: 'NRI (Non-Resident Indian)' },
  { value: 'RNOR', label: 'RNOR (Resident but Not Ordinarily Resident)' },
  { value: 'Resident', label: 'Resident' },
  { value: 'Unknown', label: 'Not sure' },
]

export const RISK_PROFILES = [
  { value: 'conservative', label: 'Conservative' },
  { value: 'moderate', label: 'Moderate' },
  { value: 'aggressive', label: 'Aggressive' },
]

export const WIZARD_STEPS = [
  'Tax Residency',
  'Indian Assets',
  'Financial Goals',
  'Review',
  'Results',
]

export const BANK_ACCOUNT_TYPES = [
  { value: 'NRO', label: 'NRO' },
  { value: 'NRE', label: 'NRE' },
  { value: 'FCNR', label: 'FCNR' },
  { value: 'Savings', label: 'Savings' },
  { value: 'Current', label: 'Current' },
]

export const OTHER_SAVINGS_TYPES = [
  { value: 'PPF', label: 'PPF' },
  { value: 'NPS', label: 'NPS' },
  { value: 'EPF', label: 'EPF' },
  { value: 'NSC', label: 'NSC' },
  { value: 'FD', label: 'Fixed Deposit' },
  { value: 'RD', label: 'Recurring Deposit' },
  { value: 'Other', label: 'Other' },
]
