import ThemeToggle from './ThemeToggle'
import StepIndicator from './StepIndicator'

export default function WizardLayout({ steps, currentStep, children }) {
  return (
    <div className="min-h-svh bg-slate-50 dark:bg-slate-950">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div>
            <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              🇮🇳 NRI Investment &amp; Tax Planner
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Multi-country tax residency planning for Indian savings &amp; investments
            </p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <div className="mb-8">
          <StepIndicator steps={steps} currentStep={currentStep} />
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 dark:border-slate-800 dark:bg-slate-900">
          {children}
        </div>

        <p className="mt-6 text-center text-xs text-slate-400 dark:text-slate-500">
          Educational planning output only — not tax, legal or investment advice.
        </p>
      </main>
    </div>
  )
}
