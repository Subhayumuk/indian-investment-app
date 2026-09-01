import { formatInr } from '../utils/format'

function Card({ title, icon, children }) {
  return (
    <section className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
        <span aria-hidden>{icon}</span>
        {title}
      </h3>
      {children}
    </section>
  )
}

function BulletList({ items }) {
  if (!items?.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Nothing to show.</p>
  }
  return (
    <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
      {items.map((item, index) => (
        <li key={index} className="flex gap-2">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

const ALLOCATION_LABELS = {
  equity_pct: 'Equity',
  debt_pct: 'Debt',
  real_estate_pct: 'Real Estate',
  gold_pct: 'Gold',
  cash_pct: 'Cash',
}

function AllocationBars({ allocation }) {
  if (!allocation) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No allocation available.</p>
  }
  const rows = Object.entries(ALLOCATION_LABELS)
    .map(([key, label]) => ({ label, pct: allocation[key] ?? 0 }))
    .filter((row) => row.pct > 0)

  if (!rows.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No allocation available.</p>
  }

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div key={row.label}>
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-slate-800 dark:text-slate-200">{row.label}</span>
            <span className="text-slate-500 dark:text-slate-400">{row.pct}%</span>
          </div>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div className="h-full rounded-full bg-indigo-500" style={{ width: `${row.pct}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function InstrumentList({ instruments }) {
  if (!instruments?.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No instruments recommended.</p>
  }
  return (
    <div className="space-y-4">
      {instruments.map((item, index) => (
        <div key={index} className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800/60">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-medium text-slate-800 dark:text-slate-200">{item.name}</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {item.category && (
                  <span className="inline-block rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                    {item.category}
                  </span>
                )}
                {item.risk_level_label && (
                  <span className="inline-block rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                    {item.risk_level_label} risk
                  </span>
                )}
              </div>
            </div>
            <div className="shrink-0 text-right">
              <p className="font-semibold text-slate-800 dark:text-slate-200">{item.suggested_allocation_pct}%</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{formatInr(item.suggested_amount_inr)}</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            3-yr: {item.historical_return_3yr} · 5-yr: {item.historical_return_5yr} · ISIN: {item.isin}
          </p>
          <p className="mt-1 text-slate-600 dark:text-slate-300">{item.why_nri_suitable}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Invest via: {item.platform_to_invest}</p>
          {item.residence_tax_note && (
            <div className="mt-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200">
              🧾 {item.residence_tax_note}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

const SCORE_BANDS = [
  { max: 40, label: 'Poor', text: 'text-rose-700 dark:text-rose-300', bg: 'bg-rose-50 dark:bg-rose-500/10' },
  { max: 65, label: 'Fair', text: 'text-amber-700 dark:text-amber-300', bg: 'bg-amber-50 dark:bg-amber-500/10' },
  { max: 85, label: 'Good', text: 'text-emerald-700 dark:text-emerald-300', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
  { max: 100, label: 'Excellent', text: 'text-indigo-700 dark:text-indigo-300', bg: 'bg-indigo-50 dark:bg-indigo-500/10' },
]
function bandFor(score) {
  return SCORE_BANDS.find((b) => score <= b.max) ?? SCORE_BANDS[SCORE_BANDS.length - 1]
}

const COMPARISON_LABELS = {
  bank_cash_pct: 'Bank / Cash',
  mutual_funds_pct: 'Mutual Funds',
  stocks_pct: 'Stocks',
  property_pct: 'Property',
  gold_pct: 'Gold',
}

function ComparisonBars({ current, recommended }) {
  const rows = Object.entries(COMPARISON_LABELS).map(([key, label]) => ({
    label,
    current: current?.[key] ?? 0,
    recommended: recommended?.[key] ?? 0,
  }))
  return (
    <div className="space-y-4">
      {rows.map((row) => (
        <div key={row.label}>
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-slate-800 dark:text-slate-200">{row.label}</span>
            <span className="text-slate-500 dark:text-slate-400">
              {row.current}% now → {row.recommended}% target
            </span>
          </div>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div className="h-full rounded-full bg-slate-400" style={{ width: `${row.current}%` }} />
          </div>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div className="h-full rounded-full bg-indigo-500" style={{ width: `${row.recommended}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function PortfolioHealthCard({ health }) {
  if (!health) return null
  const band = bandFor(health.overall_score)
  return (
    <section className={`rounded-xl border border-slate-200 p-4 dark:border-slate-800 ${band.bg}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Portfolio Health</h3>
        <span className={`text-2xl font-bold ${band.text}`}>
          {health.overall_score}/100 · {health.score_label}
        </span>
      </div>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Total Corpus Analysed: {formatInr(health.total_corpus_inr)}
      </p>
      <div className="mt-4">
        <ComparisonBars current={health.asset_breakdown} recommended={health.recommended_allocation} />
      </div>
      {health.health_flags?.length > 0 && (
        <ul className="mt-4 space-y-1.5 text-sm text-slate-700 dark:text-slate-300">
          {health.health_flags.map((flag, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />
              <span>{flag}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default function StepResults({ result, onStartOver }) {
  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Your Plan</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{result?.profile_summary}</p>
          {result?.risk_profile && (
            <p className="mt-1 text-xs uppercase tracking-wide text-slate-400 dark:text-slate-500">
              Risk profile: {result.risk_profile}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onStartOver}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Start Over
        </button>
      </div>

      <div className="mt-6">
        <PortfolioHealthCard health={result?.portfolio_health} />
      </div>

      <div className="mt-6 rounded-xl bg-indigo-50 p-4 dark:bg-indigo-500/10">
        <p className="text-xs font-medium uppercase tracking-wide text-indigo-600 dark:text-indigo-300">
          Investable amount (INR)
        </p>
        <p className="mt-1 text-lg font-semibold text-indigo-900 dark:text-indigo-200">
          {formatInr(result?.investable_amount_inr)}
        </p>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Suggested Allocation" icon="📊">
          <AllocationBars allocation={result?.allocation} />
        </Card>

        <Card title="Recommended Instruments" icon="💡">
          <InstrumentList instruments={result?.instruments} />
        </Card>

        <Card title="Key Insights" icon="🧠">
          <BulletList items={result?.key_insights} />
        </Card>

        <Card title="Action Steps" icon="✅">
          <BulletList items={result?.action_steps} />
        </Card>
      </div>

      {result?.disclaimers?.length > 0 && (
        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          <p className="mb-2 font-semibold">Disclaimers</p>
          <ul className="list-disc space-y-1 pl-4">
            {result.disclaimers.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {result?.user_id && (
        <p className="mt-4 text-right text-xs text-slate-400 dark:text-slate-500">Session: {result.user_id}</p>
      )}
    </div>
  )
}
