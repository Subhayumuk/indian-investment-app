import { useMemo, useState } from 'react'
import { currencyForCountry, defaultRateForCountry } from '../constants/formOptions'
import { runPlanner } from '../api/planner'

const INITIAL_STATE = {
  // Step 1: Tax Residency
  taxResidencyCountry: 'Denmark',
  taxResidencyCurrency: 'DKK',
  exchangeRateToInr: 11.5,
  indianResidentialStatus: 'non_resident',   // ← was 'NRI'
  age: 35,
  hasPan: true,
  filesIndiaItr: false,
  declaresIndiaIncomeInResidenceCountry: false,

  // Step 2: Indian Assets
  bankAccounts: [{ id: 1, bankName: '', accountType: 'NRO', balanceInr: '' }],
  mutualFunds: [], // rows: { id, fundName, folio, currentValueInr }
  stocks: [], // rows: { id, stockName, currentValueInr }
  properties: [], // rows: { id, description, valueInr }
  goldGrams: '',
  goldValueInr: '',
  goldInputMode: 'inr', // 'grams' | 'inr'
  otherSavings: [], // rows: { id, type, valueInr }
  insuranceSumAssuredInr: '',

  // Step 3: Financial Goals
  riskProfile: 'moderate',
  investmentHorizonYears: 7,
  monthlyExpensesLocal: null,
  monthlyIncomeLocal: null,
  emergencyMonths: 6,
  wantsRepatriation: false,
  repatriationAmountInr: null,
  notes: '',
}

const TOTAL_STEPS = 5 // 4 form steps + results

// Maps the UI's INDIAN_RESIDENTIAL_STATUSES option values to the
// IndianResidentialStatus enum values the backend actually accepts
// (resident / rnor / non_resident / unknown).
const RESIDENTIAL_STATUS_TO_BACKEND = {
  NRI: 'non_resident',
  RNOR: 'rnor',
  Resident: 'resident',
  Unknown: 'unknown',
}

function toBackendResidentialStatus(value) {
  return RESIDENTIAL_STATUS_TO_BACKEND[value] ?? value?.toLowerCase() ?? 'unknown'
}

// Maps the Step2Assets bank account type options to the backend AccountType
// enum (NRE/NRO/FCNR/resident_savings/RFC) — "Current" has no NRI-specific
// backend concept, so it maps to resident_savings same as "Savings".
const ACCOUNT_TYPE_TO_BACKEND = {
  NRO: 'NRO',
  NRE: 'NRE',
  FCNR: 'FCNR',
  Savings: 'resident_savings',
  Current: 'resident_savings',
}

// Builds the nested UserProfile JSON body that /api/recommend expects.
function buildPayload(form) {
  const exchangeRate = form.exchangeRateToInr > 0 ? form.exchangeRateToInr : 11.5

  // Convert local-currency amounts to INR
  const monthlyExpensesInr = form.monthlyExpensesLocal
    ? Math.round(form.monthlyExpensesLocal * exchangeRate)
    : 0

  const monthlyIncomeInr = form.monthlyIncomeLocal
    ? Math.round(form.monthlyIncomeLocal * exchangeRate)
    : 150000 // fallback default

  // Monthly savings estimate
  const monthlySavingsInr = Math.max(0, monthlyIncomeInr - monthlyExpensesInr)

  // Account types held — derived from the new bank accounts list (the old
  // NRE/NRO/FCNR toggles no longer exist once Step2Assets replaced Step2).
  const accountTypes = [
    ...new Set(
      (form.bankAccounts ?? [])
        .map((a) => ACCOUNT_TYPE_TO_BACKEND[a.accountType])
        .filter(Boolean)
    ),
  ]

  return {
    session_id: `session-${Date.now()}`,

    personal: {
      age: form.age,
      marital_status: 'single',         // TODO: add to UI
      dependents: 0,
      employment_status: 'salaried',    // TODO: add to UI
      income_stability: 'stable',       // ← must be string
      citizenship: 'indian',
      oci_pio_status: false,
    },

    financial: {
      monthly_income_inr: monthlyIncomeInr,
      monthly_income_foreign: form.monthlyIncomeLocal ?? 0,
      foreign_currency: form.taxResidencyCurrency,
      monthly_expenses_inr: monthlyExpensesInr,
      monthly_expenses_foreign: form.monthlyExpensesLocal ?? 0,
      emergency_fund_months: form.emergencyMonths ?? 6,
      existing_debt_inr: 0,
      monthly_emi_inr: 0,
      insurance_coverage: (parseFloat(form.insuranceSumAssuredInr) || 0) > 0,
      insurance_sum_assured_inr: parseFloat(form.insuranceSumAssuredInr) || 0,
      existing_investments_inr: 0,
      bank_accounts: (form.bankAccounts ?? []).map((a) => ({
        bank_name: a.bankName,
        account_type: a.accountType,
        balance_inr: parseFloat(a.balanceInr) || 0,
      })),
      mutual_funds: (form.mutualFunds ?? []).map((f) => ({
        fund_name: f.fundName,
        isin: f.isin || '',
        current_value_inr: parseFloat(f.currentValueInr) || 0,
      })),
      stocks: (form.stocks ?? []).map((s) => ({
        stock_name: s.stockName,
        isin: s.isin || '',
        current_value_inr: parseFloat(s.currentValueInr) || 0,
      })),
      properties: (form.properties ?? []).map((p) => ({
        description: p.description,
        value_inr: parseFloat(p.valueInr) || 0,
      })),
      gold_grams: parseFloat(form.goldGrams) || 0,
      gold_value_inr: parseFloat(form.goldValueInr) || 0,
      other_savings: (form.otherSavings ?? []).map((o) => ({
        type: o.type,
        value_inr: parseFloat(o.valueInr) || 0,
      })),
    },

    residency: {
      country_of_stay: form.taxResidencyCountry.toLowerCase(),
      tax_residency_country: form.taxResidencyCountry.toLowerCase(),
      days_in_india_current_fy: 0,
      days_in_india_last_4_fy: 0,
      indian_residential_status: toBackendResidentialStatus(form.indianResidentialStatus),
      has_indian_bank_accounts: accountTypes.length > 0,
      account_types_held: accountTypes,
      repatriation_required: form.wantsRepatriation ?? false,
      plans_to_return_to_india: false,
      has_pan: form.hasPan ?? false,
      has_kyc: form.hasPan ?? false,
      files_india_itr: form.filesIndiaItr ?? false,
      declares_india_income_in_residence_country: form.declaresIndiaIncomeInResidenceCountry ?? false,
    },

    investment: {
      risk_tolerance: form.riskProfile,
      investment_horizon_years: form.investmentHorizonYears ?? 7,
      liquidity_need: 'medium',         // TODO: add to UI
      primary_goal: 'wealth_creation',  // TODO: add to UI
      monthly_investable_inr: monthlySavingsInr,
      // Step2Assets captures the corpus exhaustively via financial.* above;
      // forcing 0 here avoids double-counting against the backend's
      // total_corpus_inr = sum(financial.*) + lump_sum_investable_inr formula.
      lump_sum_investable_inr: 0,
      preferred_currency: form.taxResidencyCurrency,
      existing_india_investments: [],
    },
  }
}

export function useWizardForm() {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState(INITIAL_STATE)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const setField = (name, value) => {
    setForm((current) => {
      const next = { ...current, [name]: value }

      if (name === 'taxResidencyCountry') {
        next.taxResidencyCurrency = currencyForCountry(value)
        next.exchangeRateToInr = defaultRateForCountry(value)
      }

      return next
    })
  }

  const goNext = () => setStep((current) => Math.min(current + 1, TOTAL_STEPS))
  const goBack = () => setStep((current) => Math.max(current - 1, 1))
  const goToStep = (target) => setStep(Math.min(Math.max(target, 1), TOTAL_STEPS))

  const submit = async () => {
    setIsSubmitting(true)
    setError(null)

    try {
      const payload = buildPayload(form)
      const data = await runPlanner(payload)
      setResult(data)
      setStep(5)
    } catch (err) {
      setError(err.message || 'Something went wrong while running the planner.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const payloadPreview = useMemo(() => buildPayload(form), [form])

  return {
    step,
    form,
    setField,
    goNext,
    goBack,
    goToStep,
    submit,
    result,
    error,
    isSubmitting,
    payloadPreview,
    totalSteps: TOTAL_STEPS,
  }
}