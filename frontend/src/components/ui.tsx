import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { EventType, Outcome } from '../lib/api'
import { EVENT_TYPE_LABEL, outcomeLabel, outcomeTone, pct } from '../lib/format'

export function PageHeader({ title, subtitle, actions }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1.5 max-w-3xl text-sm text-muted sm:text-base">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function Card({ title, subtitle, actions, children, className = '', flush = false }: {
  title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; flush?: boolean
}) {
  return (
    <section className={`rounded-xl border border-line bg-surface ${className}`}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-2 border-b border-line px-4 py-3 sm:px-5">
          <div>
            {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className={flush ? '' : 'p-4 sm:p-5'}>{children}</div>
    </section>
  )
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: 'pos' | 'neg' | 'mixed' }) {
  const color = tone === 'pos' ? 'text-pos' : tone === 'neg' ? 'text-neg' : tone === 'mixed' ? 'text-mixed' : 'text-ink'
  return (
    <div className="rounded-xl border border-line bg-surface px-4 py-3.5">
      <div className="text-xs font-medium text-muted">{label}</div>
      <div className={`tabular mt-1 text-2xl font-semibold tracking-tight ${color}`}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
    </div>
  )
}

const TONE_CLASSES = {
  pos: 'bg-pos-soft text-pos',
  neg: 'bg-neg-soft text-neg',
  mixed: 'bg-mixed-soft text-mixed',
  neutral: 'bg-surface-2 text-muted',
  accent: 'bg-accent-soft text-accent',
}

export function Badge({ tone = 'neutral', children }: { tone?: keyof typeof TONE_CLASSES; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}>
      {children}
    </span>
  )
}

export function OutcomeBadge({ outcome }: { outcome: Outcome }) {
  return <Badge tone={outcomeTone(outcome)}>{outcomeLabel(outcome)}</Badge>
}

export function TypeBadge({ type }: { type: EventType }) {
  return <Badge tone={type === 'fda_decision' ? 'accent' : 'neutral'}>{EVENT_TYPE_LABEL[type]}</Badge>
}

/** A return coloured by sign. */
export function Ret({ value, digits = 1, className = '' }: { value: number | null | undefined; digits?: number; className?: string }) {
  const color = value === null || value === undefined ? 'text-muted' : value > 0 ? 'text-pos' : value < 0 ? 'text-neg' : 'text-ink'
  return <span className={`tabular font-medium ${color} ${className}`}>{pct(value, digits)}</span>
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-muted" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
      {label}
    </div>
  )
}

export function ErrorBox({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error)
  return (
    <div className="rounded-xl border border-neg/30 bg-neg-soft px-4 py-3 text-sm text-neg" role="alert">
      <strong className="font-semibold">Couldn't load this data.</strong> {message}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-8 text-center text-sm text-muted">{children}</div>
}

export function TextLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link to={to} className="font-medium text-accent hover:underline">
      {children}
    </Link>
  )
}

export function ExternalLink({ href, children }: { href: string | null; children: ReactNode }) {
  if (!href) return <>{children}</>
  return (
    <a href={href} target="_blank" rel="noreferrer" className="font-medium text-accent hover:underline">
      {children} <span aria-hidden>↗</span>
    </a>
  )
}

export function Select<T extends string>({ label, value, onChange, options }: {
  label: string; value: T; onChange: (v: T) => void; options: { value: T; label: string }[]
}) {
  return (
    <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-muted">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="h-9 rounded-lg border border-line bg-surface px-2.5 text-sm text-ink outline-none focus:border-accent"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  )
}

export function Button({ children, onClick, variant = 'primary', disabled, type = 'button' }: {
  children: ReactNode; onClick?: () => void; variant?: 'primary' | 'secondary'; disabled?: boolean; type?: 'button' | 'submit'
}) {
  const style = variant === 'primary'
    ? 'bg-accent text-white dark:text-[#06201d] hover:opacity-90'
    : 'border border-line bg-surface text-ink hover:bg-surface-2'
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex h-9 items-center gap-1.5 rounded-lg px-3.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${style}`}
    >
      {children}
    </button>
  )
}

/** Table shell: scrolls sideways on small screens instead of stretching the page. */
export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-max border-collapse text-sm">{children}</table>
    </div>
  )
}

export function Th({ children, right = false }: { children?: ReactNode; right?: boolean }) {
  return (
    <th className={`border-b border-line bg-surface-2/60 px-4 py-2.5 text-xs font-semibold text-muted ${right ? 'text-right' : 'text-left'}`}>
      {children}
    </th>
  )
}

export function Td({ children, right = false, className = '' }: { children?: ReactNode; right?: boolean; className?: string }) {
  return (
    <td className={`border-b border-line px-4 py-2.5 align-middle text-ink ${right ? 'text-right tabular' : ''} ${className}`}>
      {children}
    </td>
  )
}
