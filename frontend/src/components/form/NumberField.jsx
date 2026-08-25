export default function NumberField({ label, value, onChange, placeholder, help, step = 'any', min, prefix, required }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
        {label}
        {required && <span className="ml-0.5 text-rose-500">*</span>}
      </span>
      <div className="relative">
        {prefix && (
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-slate-400">
            {prefix}
          </span>
        )}
        <input
          type="number"
          inputMode="decimal"
          step={step}
          min={min}
          value={value ?? ''}
          placeholder={placeholder}
          onChange={(event) => {
            const raw = event.target.value
            onChange(raw === '' ? null : Number(raw))
          }}
          className={`w-full rounded-lg border border-slate-300 bg-white py-2 pr-3 text-sm text-slate-900 shadow-sm transition focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:border-indigo-400 ${prefix ? 'pl-14' : 'pl-3'}`}
        />
      </div>
      {help && <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">{help}</span>}
    </label>
  )
}
