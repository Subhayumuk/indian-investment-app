import SelectField from '../components/form/SelectField'
import NumberField from '../components/form/NumberField'
import ToggleField from '../components/form/ToggleField'
import StepFooter from '../components/StepFooter'
import { COUNTRIES, INDIAN_RESIDENTIAL_STATUSES } from '../constants/formOptions'

export default function Step1Residency({ form, setField, onNext }) {
  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Tax Residency</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Tell us where you're tax resident today, and your status under Indian tax law.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
        <SelectField
          label="Country of tax residency"
          value={form.taxResidencyCountry}
          onChange={(value) => setField('taxResidencyCountry', value)}
          options={COUNTRIES.map((c) => ({ value: c.value, label: c.label }))}
          required
        />

        <NumberField
          label={`Exchange rate: 1 ${form.taxResidencyCurrency} = ? INR`}
          value={form.exchangeRateToInr}
          onChange={(value) => setField('exchangeRateToInr', value)}
          step="0.01"
          help="Adjust to today's actual rate if you know it."
        />

        <SelectField
          label="Indian residential status"
          value={form.indianResidentialStatus}
          onChange={(value) => setField('indianResidentialStatus', value)}
          options={INDIAN_RESIDENTIAL_STATUSES}
        />

        <NumberField
          label="Age"
          value={form.age}
          onChange={(value) => setField('age', value)}
          step="1"
          min="18"
          max="80"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <ToggleField
          label={`Tax resident of ${form.taxResidencyCountry}`}
          checked={form.isTaxResidentInCountry}
          onChange={(value) => setField('isTaxResidentInCountry', value)}
        />
        <ToggleField
          label="Has PAN (Permanent Account Number)"
          checked={form.hasPan}
          onChange={(value) => setField('hasPan', value)}
        />
        <ToggleField
          label="Has Aadhaar"
          checked={form.hasAadhaar}
          onChange={(value) => setField('hasAadhaar', value)}
        />
        <ToggleField
          label="Files Indian income tax return (ITR)"
          checked={form.filesIndiaItr}
          onChange={(value) => setField('filesIndiaItr', value)}
        />
        <ToggleField
          label={`Declares Indian income in ${form.taxResidencyCountry}`}
          checked={form.declaresIndiaIncomeInResidenceCountry}
          onChange={(value) => setField('declaresIndiaIncomeInResidenceCountry', value)}
        />
      </div>

      <StepFooter onBack={() => {}} backDisabled onNext={onNext} />
    </div>
  )
}
