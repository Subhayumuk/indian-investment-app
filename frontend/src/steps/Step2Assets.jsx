import { useEffect, useRef, useState } from 'react'
import TextField from '../components/form/TextField'
import NumberField from '../components/form/NumberField'
import SelectField from '../components/form/SelectField'
import RemoveRowButton from '../components/form/RemoveRowButton'
import StepFooter from '../components/StepFooter'
import { BANK_ACCOUNT_TYPES, OTHER_SAVINGS_TYPES } from '../constants/formOptions'
import { formatInr, sumField } from '../utils/format'
import { parseCas } from '../api/cas'
import { fetchGoldPrice } from '../api/gold'

function addRow(form, setField, key, blank) {
  setField(key, [...(form[key] ?? []), blank])
}
function updateRow(form, setField, key, id, field, value) {
  setField(key, (form[key] ?? []).map((row) => (row.id === id ? { ...row, [field]: value } : row)))
}
function removeRow(form, setField, key, id) {
  setField(key, (form[key] ?? []).filter((row) => row.id !== id))
}

function Section({ title, subtitle, children }) {
  return (
    <section className="mt-6 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{title}</h3>
      {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  )
}

function Subtotal({ label, amount }) {
  return (
    <p className="text-sm text-slate-600 dark:text-slate-300">
      {label}: <span className="font-medium text-slate-800 dark:text-slate-200">{formatInr(amount)}</span>
    </p>
  )
}

function AddButton({ onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:border-indigo-400 hover:text-indigo-600 dark:border-slate-700 dark:text-slate-300 dark:hover:border-indigo-500 dark:hover:text-indigo-400"
    >
      {children}
    </button>
  )
}

export default function Step2Assets({ form, setField, onNext, onBack }) {
  const nextId = useRef(1000)
  const genId = () => (nextId.current += 1)

  const [casUploading, setCasUploading] = useState(false)
  const [casMessage, setCasMessage] = useState(null)

  const [goldPricePerGram, setGoldPricePerGram] = useState(7500)
  const [goldPriceSource, setGoldPriceSource] = useState('fallback')

  useEffect(() => {
    let cancelled = false
    fetchGoldPrice().then((data) => {
      if (cancelled) return
      setGoldPricePerGram(data.price_per_gram_inr)
      setGoldPriceSource(data.source)
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (form.goldInputMode === 'grams') {
      const estimated = (Number(form.goldGrams) || 0) * goldPricePerGram
      setField('goldValueInr', estimated)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.goldGrams, form.goldInputMode, goldPricePerGram])

  async function handleCasUpload(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    setCasUploading(true)
    setCasMessage(null)
    try {
      const data = await parseCas(file)
      if (data.parse_status === 'failed') {
        setCasMessage(data.parse_notes || 'Could not parse this statement — please add holdings manually.')
        return
      }
      if (data.mutual_funds?.length) {
        setField('mutualFunds', [
          ...form.mutualFunds,
          ...data.mutual_funds.map((m) => ({
            id: genId(),
            fundName: m.fund_name,
            folio: m.folio,
            isin: m.isin,
            currentValueInr: m.current_value_inr,
          })),
        ])
      }
      if (data.stocks?.length) {
        setField('stocks', [
          ...form.stocks,
          ...data.stocks.map((s) => ({
            id: genId(),
            stockName: s.stock_name,
            isin: s.isin,
            currentValueInr: s.current_value_inr,
          })),
        ])
      }
      if (data.total_life_insurance_sum_assured_inr) {
        setField(
          'insuranceSumAssuredInr',
          (parseFloat(form.insuranceSumAssuredInr) || 0) + data.total_life_insurance_sum_assured_inr
        )
      }
      setCasMessage(data.parse_notes || null)
    } catch (err) {
      setCasMessage(err.message || 'Upload failed.')
    } finally {
      setCasUploading(false)
    }
  }

  const bankTotal = sumField(form.bankAccounts, 'balanceInr')
  const mfTotal = sumField(form.mutualFunds, 'currentValueInr')
  const stocksTotal = sumField(form.stocks, 'currentValueInr')
  const propertyTotal = sumField(form.properties, 'valueInr')
  const goldValue = Number(form.goldValueInr) || 0
  const otherTotal = sumField(form.otherSavings, 'valueInr')
  const grandTotal = bankTotal + mfTotal + stocksTotal + propertyTotal + goldValue + otherTotal

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Indian Assets</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Everything you currently hold in India — bank accounts, mutual funds, stocks, property, gold and other
        savings. This drives your investable corpus and portfolio health score.
      </p>

      <Section title="Bank Accounts">
        {form.bankAccounts.map((row) => (
          <div key={row.id} className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_160px_1fr_auto] sm:items-end">
            <TextField
              label="Bank name"
              value={row.bankName}
              onChange={(v) => updateRow(form, setField, 'bankAccounts', row.id, 'bankName', v)}
              placeholder="e.g. SBI, HDFC, ICICI"
            />
            <SelectField
              label="Account type"
              value={row.accountType}
              onChange={(v) => updateRow(form, setField, 'bankAccounts', row.id, 'accountType', v)}
              options={BANK_ACCOUNT_TYPES}
            />
            <NumberField
              label="Balance"
              prefix="INR"
              value={row.balanceInr}
              onChange={(v) => updateRow(form, setField, 'bankAccounts', row.id, 'balanceInr', v)}
            />
            <RemoveRowButton onClick={() => removeRow(form, setField, 'bankAccounts', row.id)} />
          </div>
        ))}
        <AddButton onClick={() => addRow(form, setField, 'bankAccounts', { id: genId(), bankName: '', accountType: 'NRO', balanceInr: '' })}>
          + Add Bank Account
        </AddButton>
        <Subtotal label="Total bank balance" amount={bankTotal} />
      </Section>

      <Section
        title="Mutual Funds & Stocks (NSDL CAS)"
        subtitle="Upload your NSDL Consolidated Account Statement (CAS) PDF to automatically import your mutual fund and stock holdings. Or enter totals manually below."
      >
        <div className="flex items-center gap-3">
          <label className="cursor-pointer rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
            Upload CAS PDF
            <input type="file" accept="application/pdf,.pdf" className="hidden" onChange={handleCasUpload} />
          </label>
          {casUploading && <span className="text-sm text-slate-500 dark:text-slate-400">Parsing statement…</span>}
        </div>
        {casMessage && (
          <p className="text-sm text-amber-700 dark:text-amber-300">{casMessage}</p>
        )}

        <div className="mt-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Mutual Funds</p>
          {form.mutualFunds.map((row) => (
            <div key={row.id} className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-[1fr_160px_1fr_auto] sm:items-end">
              <TextField
                label="Fund name"
                value={row.fundName}
                onChange={(v) => updateRow(form, setField, 'mutualFunds', row.id, 'fundName', v)}
              />
              <TextField
                label="Folio No."
                value={row.folio}
                onChange={(v) => updateRow(form, setField, 'mutualFunds', row.id, 'folio', v)}
                placeholder="Optional"
              />
              <NumberField
                label="Current value"
                prefix="INR"
                value={row.currentValueInr}
                onChange={(v) => updateRow(form, setField, 'mutualFunds', row.id, 'currentValueInr', v)}
              />
              <RemoveRowButton onClick={() => removeRow(form, setField, 'mutualFunds', row.id)} />
            </div>
          ))}
          <div className="mt-2">
            <AddButton onClick={() => addRow(form, setField, 'mutualFunds', { id: genId(), fundName: '', folio: '', currentValueInr: '' })}>
              + Add Fund Manually
            </AddButton>
          </div>
          <div className="mt-2">
            <Subtotal label="Total MF value" amount={mfTotal} />
          </div>
        </div>

        <div className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Stocks</p>
          {form.stocks.map((row) => (
            <div key={row.id} className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
              <TextField
                label="Stock name"
                value={row.stockName}
                onChange={(v) => updateRow(form, setField, 'stocks', row.id, 'stockName', v)}
              />
              <NumberField
                label="Current value"
                prefix="INR"
                value={row.currentValueInr}
                onChange={(v) => updateRow(form, setField, 'stocks', row.id, 'currentValueInr', v)}
              />
              <RemoveRowButton onClick={() => removeRow(form, setField, 'stocks', row.id)} />
            </div>
          ))}
          <div className="mt-2">
            <AddButton onClick={() => addRow(form, setField, 'stocks', { id: genId(), stockName: '', currentValueInr: '' })}>
              + Add Stock Manually
            </AddButton>
          </div>
          <div className="mt-2">
            <Subtotal label="Total stocks value" amount={stocksTotal} />
          </div>
        </div>
      </Section>

      <Section
        title="Life Insurance"
        subtitle="Auto-filled from your CAS upload above if it includes an e-Insurance Account (eIA) summary, or enter your total sum assured manually."
      >
        <div className="max-w-xs">
          <NumberField
            label="Total sum assured"
            prefix="INR"
            value={form.insuranceSumAssuredInr}
            onChange={(v) => setField('insuranceSumAssuredInr', v)}
          />
        </div>
      </Section>

      <Section title="Property">
        {form.properties.map((row) => (
          <div key={row.id} className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <TextField
              label="Description"
              value={row.description}
              onChange={(v) => updateRow(form, setField, 'properties', row.id, 'description', v)}
              placeholder="e.g. 2BHK Flat in Mumbai"
            />
            <NumberField
              label="Estimated value"
              prefix="INR"
              value={row.valueInr}
              onChange={(v) => updateRow(form, setField, 'properties', row.id, 'valueInr', v)}
            />
            <RemoveRowButton onClick={() => removeRow(form, setField, 'properties', row.id)} />
          </div>
        ))}
        <AddButton onClick={() => addRow(form, setField, 'properties', { id: genId(), description: '', valueInr: '' })}>
          + Add Property
        </AddButton>
        <Subtotal label="Total property value" amount={propertyTotal} />
      </Section>

      <Section title="Gold">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setField('goldInputMode', 'grams')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              form.goldInputMode === 'grams'
                ? 'bg-indigo-600 text-white'
                : 'border border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'
            }`}
          >
            Enter in grams
          </button>
          <button
            type="button"
            onClick={() => setField('goldInputMode', 'inr')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              form.goldInputMode === 'inr'
                ? 'bg-indigo-600 text-white'
                : 'border border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'
            }`}
          >
            Enter in INR value
          </button>
        </div>

        {form.goldInputMode === 'grams' ? (
          <div className="max-w-xs">
            <NumberField
              label="Grams"
              value={form.goldGrams}
              onChange={(v) => setField('goldGrams', v)}
            />
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Current gold price: {formatInr(goldPricePerGram)}/gram ({goldPriceSource === 'live' ? 'live' : 'fallback rate'})
            </p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Estimated value: {formatInr(goldValue)}</p>
          </div>
        ) : (
          <div className="max-w-xs">
            <NumberField
              label="Total gold value"
              prefix="INR"
              value={form.goldValueInr}
              onChange={(v) => setField('goldValueInr', v)}
            />
          </div>
        )}
        <Subtotal label="Total gold value" amount={goldValue} />
      </Section>

      <Section title="Other Savings">
        {form.otherSavings.map((row) => (
          <div key={row.id} className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <SelectField
              label="Type"
              value={row.type}
              onChange={(v) => updateRow(form, setField, 'otherSavings', row.id, 'type', v)}
              options={OTHER_SAVINGS_TYPES}
            />
            <NumberField
              label="Value"
              prefix="INR"
              value={row.valueInr}
              onChange={(v) => updateRow(form, setField, 'otherSavings', row.id, 'valueInr', v)}
            />
            <RemoveRowButton onClick={() => removeRow(form, setField, 'otherSavings', row.id)} />
          </div>
        ))}
        <AddButton onClick={() => addRow(form, setField, 'otherSavings', { id: genId(), type: 'PPF', valueInr: '' })}>
          + Add Other Saving
        </AddButton>
        <Subtotal label="Total other savings" amount={otherTotal} />
      </Section>

      <div className="mt-6 rounded-xl bg-indigo-50 p-4 text-center dark:bg-indigo-500/10">
        <p className="text-xs font-medium uppercase tracking-wide text-indigo-600 dark:text-indigo-300">
          💰 Total Indian Corpus
        </p>
        <p className="mt-1 text-2xl font-bold text-indigo-900 dark:text-indigo-200">{formatInr(grandTotal)}</p>
      </div>

      <StepFooter onBack={onBack} onNext={onNext} />
    </div>
  )
}
