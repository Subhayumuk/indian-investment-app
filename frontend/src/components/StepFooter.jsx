export default function StepFooter({ onBack, onNext, nextLabel = 'Continue', backDisabled, nextDisabled, isBusy }) {
  return (
    <div className="mt-8 flex items-center justify-between border-t border-slate-200 pt-6 dark:border-slate-800">
      <button
        type="button"
        onClick={onBack}
        disabled={backDisabled}
        className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 disabled:pointer-events-none disabled:opacity-0 dark:text-slate-300 dark:hover:bg-slate-800"
      >
        ← Back
      </button>
      <button
        type="button"
        onClick={onNext}
        disabled={nextDisabled || isBusy}
        className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isBusy ? 'Working…' : nextLabel}
      </button>
    </div>
  )
}
