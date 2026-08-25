import SelectField from '../components/form/SelectField'
import NumberField from '../components/form/NumberField'
import ToggleField from '../components/form/ToggleField'
import TextField from '../components/form/TextField'
import StepFooter from '../components/StepFooter'
import { RISK_PROFILES } from '../constants/formOptions'

export default function Step3Goals({ form, setField, onNext, onBack }) {
  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Financial Goals</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Your risk appetite, time horizon and liquidity needs shape the investment allocation.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
        <SelectField
          label="Risk profile"
          value={form.riskProfile}
          onChange={(v) => setField('riskProfile', v)}
          options={RISK_PROFILES}
        />
        <NumberField
          label="Investment horizon (years)"
          value={form.investmentHorizonYears}
          onChange={(v) => setField('investmentHorizonYears', v)}
          step="1"
          min="0"
        />
        <NumberField
          label={`Monthly expenses (${form.taxResidencyCurrency})`}
          prefix={form.taxResidencyCurrency}
          value={form.monthlyExpensesLocal}
          onChange={(v) => setField('monthlyExpensesLocal', v)}
          help="Used to size your emergency/liquid reserve."
        />
        <NumberField
          label="Emergency fund, months of expenses"
          value={form.emergencyMonths}
          onChange={(v) => setField('emergencyMonths', v)}
          step="1"
          min="0"
        />
      </div>

      <h3 className="mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Repatriation
      </h3>
      <div className="mt-3 grid grid-cols-1 gap-5 sm:grid-cols-2 sm:items-end">
        <ToggleField
          label="Planning to repatriate funds out of India"
          checked={form.wantsRepatriation}
          onChange={(v) => setField('wantsRepatriation', v)}
        />
        {form.wantsRepatriation && (
          <NumberField
            label="Approximate amount to repatriate"
            prefix="INR"
            value={form.repatriationAmountInr}
            onChange={(v) => setField('repatriationAmountInr', v)}
          />
        )}
      </div>

      <div className="mt-6">
        <TextField
          label="Anything else we should know?"
          value={form.notes}
          onChange={(v) => setField('notes', v)}
          placeholder="Optional notes: goals, concerns, upcoming life events, etc."
        />
      </div>

      <StepFooter onBack={onBack} onNext={onNext} />
    </div>
  )
}
