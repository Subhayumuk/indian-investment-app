import { useState } from 'react'
import { formatInr } from '../utils/format'
import { runHoldingsReview } from '../api/holdingsReview'

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

const VERDICT_STYLES = {
  aligned: {
    label: 'Aligned with benchmark',
    text: 'text-emerald-700 dark:text-emerald-300',
    bg: 'bg-emerald-50 dark:bg-emerald-500/10',
    border: 'border-emerald-200 dark:border-emerald-900',
  },
  worth_reviewing: {
    label: 'Worth reviewing',
    text: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-50 dark:bg-amber-500/10',
    border: 'border-amber-200 dark:border-amber-900',
  },
  underperforming_category: {
    label: 'Underperforming category',
    text: 'text-rose-700 dark:text-rose-300',
    bg: 'bg-rose-50 dark:bg-rose-500/10',
    border: 'border-rose-200 dark:border-rose-900',
  },
  overconcentrated: {
    label: 'Large share of your portfolio',
    text: 'text-orange-700 dark:text-orange-300',
    bg: 'bg-orange-50 dark:bg-orange-500/10',
    border: 'border-orange-200 dark:border-orange-900',
  },
  data_unavailable: {
    label: "Couldn't verify",
    text: 'text-slate-600 dark:text-slate-400',
    bg: 'bg-slate-100 dark:bg-slate-800',
    border: 'border-slate-200 dark:border-slate-700',
  },
}

function VerdictBadge({ verdict }) {
  const style = VERDICT_STYLES[verdict] ?? VERDICT_STYLES.data_unavailable
  return (
    <span
      className={`inline-block shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium ${style.text} ${style.bg} ${style.border}`}
    >
      {style.label}
    </span>
  )
}

function FundAnalysisCard({ analysis }) {
  const md = analysis.market_data ?? {}
  const hasReturnData = analysis.return_gap_pct !== null && analysis.return_gap_pct !== undefined

  return (
    <div className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800/60">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium text-slate-800 dark:text-slate-200">{analysis.fund_name}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            {formatInr(analysis.current_value_inr)} · ISIN: {analysis.isin || 'not matched'}
          </p>
        </div>
        <VerdictBadge verdict={analysis.verdict} />
      </div>

      {hasReturnData && (
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          3-yr return: {md.trailing_return_3yr_pct}% · category benchmark: {analysis.benchmark_return_pct}% ·{' '}
          {analysis.return_gap_pct >= 0 ? '+' : ''}
          {analysis.return_gap_pct}pp vs. benchmark
        </p>
      )}

      {analysis.residence_tax_note && (
        <div className="mt-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200">
          🧾 {analysis.residence_tax_note}
        </div>
      )}

      {analysis.switch_considerations?.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">If you're weighing a switch:</p>
          <ul className="mt-1 space-y-1 text-xs text-slate-600 dark:text-slate-300">
            {analysis.switch_considerations.map((item, index) => (
              <li key={index} className="flex gap-1.5">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-slate-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {analysis.warnings?.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-slate-500 dark:text-slate-400">
          {analysis.warnings.map((item, index) => (
            <li key={index}>⚠ {item}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function HoldingsReviewSection({ payload }) {
  const [status, setStatus] = useState('idle') // idle | loading | loaded | error
  const [review, setReview] = useState(null)
  const [error, setError] = useState(null)

  const hasFunds = (payload?.financial?.mutual_funds ?? []).length > 0
  if (!hasFunds) return null

  const handleAnalyze = async () => {
    setStatus('loading')
    setError(null)
    try {
      const data = await runHoldingsReview(payload)
      setReview(data)
      setStatus('loaded')
    } catch (err) {
      setError(err.message || 'Something went wrong while analyzing your holdings.')
      setStatus('error')
    }
  }

  return (
    <section className="mt-6 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">🔍 Analyze My Existing Holdings</h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Optional, one-time comparison using public AMFI/mfapi.in data. Nothing is stored.
          </p>
        </div>
        {status !== 'loaded' && (
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={status === 'loading'}
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {status === 'loading' ? 'Analyzing…' : 'Analyze My Holdings'}
          </button>
        )}
      </div>

      {status === 'error' && <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">{error}</p>}

      {status === 'loaded' && review && (
        <div className="mt-4 space-y-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Compared against
            </p>
            <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{review.peer_benchmark?.cohort_description}</p>
            <div className="mt-3">
              <ComparisonBars
                current={review.peer_benchmark?.your_allocation}
                recommended={review.peer_benchmark?.recommended_allocation}
              />
            </div>
          </div>

          {review.unmatched_fund_count > 0 && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {review.unmatched_fund_count} of {review.fund_analyses.length} fund(s) couldn't be matched to AMFI's
              records and are marked "Couldn't verify" below.
            </p>
          )}

          <div className="space-y-3">
            {review.fund_analyses.map((analysis, index) => (
              <FundAnalysisCard key={analysis.isin || index} analysis={analysis} />
            ))}
          </div>

          {review.disclaimers?.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              <p className="mb-2 font-semibold">About this analysis</p>
              <ul className="list-disc space-y-1 pl-4">
                {review.disclaimers.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

export default function StepResults({ result, payload, onStartOver }) {
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

      <HoldingsReviewSection payload={payload} />

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
