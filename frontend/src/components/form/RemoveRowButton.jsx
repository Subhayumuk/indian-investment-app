export default function RemoveRowButton({ onClick, label = 'Remove' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="shrink-0 rounded-lg border border-slate-300 px-2.5 py-2 text-sm text-slate-500 transition hover:border-rose-300 hover:text-rose-600 dark:border-slate-700 dark:text-slate-400 dark:hover:border-rose-800 dark:hover:text-rose-400"
    >
      ×
    </button>
  )
}
