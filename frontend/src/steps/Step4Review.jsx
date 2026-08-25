import StepFooter from '../components/StepFooter'
import { formatInr, formatLocal, sumField } from '../utils/format'

function ReviewRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-2 text-sm last:border-0 dark:border-slate-800">
      <span className="text-slate-500 dark:text-slate-400">{label}</span>
      <span className="font-medium text-slate-800 dark:text-slate-200">{value}</span>
    </div>
  )
}

function ReviewSection({ title, children }) {
  return (
    <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <h3 className="mb-1 text-sm font-semibold text-slate-700 dark:text-slate-300">{title}</h3>
      {children}
    </div>
  )
}

const yesNo = (value) => (value ? 'Yes' : 'No')

export default function Step4Review({ form, onSubmit, onBack, isSubmitting, error }) {
  const bankTotal = sumField(form.bankAccounts, 'balanceInr')
  const mfTotal = sumField(form.mutualFunds, 'currentValueInr')
  const stocksTotal = sumField(form.stocks, 'currentValueInr')
  const propertyTotal = sumField(form.properties, 'valueInr')
  const goldValue = Number(form.goldValueInr) || 0
  const otherTotal = sumField(form.otherSavings, 'valueInr')
  const totalCorpus = bankTotal + mfTotal + stocksTotal + propertyTotal + goldValue + otherTotal

  const accountsSummary = form.bankAccounts?.length
    ? `${form.bankAccounts.length} account${form.bankAccounts.length > 1 ? 's' : ''} (${formatInr(bankTotal)})`
    : 'None added'

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Review &amp; Submit</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Double-check your details, then run the planner to see your investment plan and tax implications.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ReviewSection title="Tax Residency">
          <ReviewRow label="Country" value={form.taxResidencyCountry} />
          <ReviewRow label="Currency" value={form.taxResidencyCurrency} />
          <ReviewRow label="Exchange rate to INR" value={`1 ${form.taxResidencyCurrency} = ${form.exchangeRateToInr} INR`} />
          <ReviewRow label="Indian residential status" value={form.indianResidentialStatus} />
          <ReviewRow label="Has PAN" value={yesNo(form.hasPan)} />
        </ReviewSection>

        <ReviewSection title="Indian Assets">
          <ReviewRow label="Bank accounts" value={accountsSummary} />
          <ReviewRow
            label="Mutual funds"
            value={form.mutualFunds?.length ? `${form.mutualFunds.length} fund(s), ${formatInr(mfTotal)}` : 'None added'}
          />
          <ReviewRow
            label="Stocks"
            value={form.stocks?.length ? `${form.stocks.length} holding(s), ${formatInr(stocksTotal)}` : 'None added'}
          />
          <ReviewRow
            label="Properties"
            value={
              form.properties?.length
                ? `${form.properties.length} propert${form.properties.length > 1 ? 'ies' : 'y'}, ${formatInr(propertyTotal)}`
                : 'None added'
            }
          />
          <ReviewRow label="Gold" value={formatInr(goldValue)} />
          <ReviewRow
            label="Other savings"
            value={form.otherSavings?.length ? `${form.otherSavings.length} item(s), ${formatInr(otherTotal)}` : 'None added'}
          />
          <ReviewRow label="Total corpus" value={formatInr(totalCorpus)} />
        </ReviewSection>

        <ReviewSection title="Financial Goals">
          <ReviewRow label="Risk profile" value={form.riskProfile} />
          <ReviewRow label="Horizon" value={`${form.investmentHorizonYears} years`} />
          <ReviewRow label="Monthly expenses" value={formatLocal(form.monthlyExpensesLocal ?? 0, form.taxResidencyCurrency)} />
          <ReviewRow label="Emergency fund" value={`${form.emergencyMonths} months`} />
        </ReviewSection>

        <ReviewSection title="Repatriation">
          <ReviewRow label="Planning to repatriate" value={yesNo(form.wantsRepatriation)} />
          {form.wantsRepatriation && (
            <ReviewRow label="Amount" value={formatInr(form.repatriationAmountInr ?? 0)} />
          )}
        </ReviewSection>
      </div>

      {error && (
        <div className="mt-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-300">
          {error}
        </div>
      )}

      <StepFooter onBack={onBack} onNext={onSubmit} nextLabel="Run Planner" isBusy={isSubmitting} />
    </div>
  )
}
