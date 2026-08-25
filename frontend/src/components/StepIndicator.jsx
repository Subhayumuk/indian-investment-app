export default function StepIndicator({ steps, currentStep }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-3">
      {steps.map((step, index) => {
        const stepNumber = index + 1
        const isComplete = stepNumber < currentStep
        const isCurrent = stepNumber === currentStep

        return (
          <li key={step} className="flex items-center gap-2">
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition ${
                isCurrent
                  ? 'bg-indigo-600 text-white'
                  : isComplete
                    ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300'
                    : 'bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
              }`}
            >
              {isComplete ? '✓' : stepNumber}
            </span>
            <span
              className={`hidden text-sm sm:inline ${
                isCurrent
                  ? 'font-semibold text-slate-900 dark:text-slate-100'
                  : 'text-slate-500 dark:text-slate-400'
              }`}
            >
              {step}
            </span>
            {stepNumber < steps.length && (
              <span className="mx-1 hidden h-px w-6 bg-slate-300 sm:block dark:bg-slate-700" />
            )}
          </li>
        )
      })}
    </ol>
  )
}
