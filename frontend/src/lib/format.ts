import type { EventType, Outcome } from './api'

/** 0.1234 -> "+12.3%" */
export function pct(x: number | null | undefined, digits = 1): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '—'
  const v = x * 100
  return `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(digits)}%`
}

export function money(x: number | null | undefined): string {
  if (x === null || x === undefined) return '—'
  return `$${x.toFixed(2)}`
}

export function num(x: number | null | undefined): string {
  if (x === null || x === undefined) return '—'
  return x.toLocaleString('en-US')
}

/** "2025-02-14" -> "Feb 14, 2025" (parsed as a calendar date, no timezone shift) */
export function day(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  })
}

/** Timestamps are stored in UTC; show them in New York time, where the market trades. */
export function marketTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
    timeZone: 'America/New_York', timeZoneName: 'short',
  })
}

export const EVENT_TYPE_LABEL: Record<EventType, string> = {
  fda_decision: 'FDA decision',
  trial_readout: 'Trial readout',
}

export const OUTCOMES: Outcome[] = ['approved', 'positive', 'mixed', 'negative', 'rejected']

export function outcomeLabel(o: Outcome): string {
  return o.charAt(0).toUpperCase() + o.slice(1)
}

export function outcomeTone(o: Outcome | null | undefined): 'pos' | 'neg' | 'mixed' {
  if (o === 'approved' || o === 'positive') return 'pos'
  if (o === 'rejected' || o === 'negative') return 'neg'
  return 'mixed'
}

/** CSS colour for charts */
export function outcomeColor(o: Outcome | null | undefined): string {
  return `var(--${outcomeTone(o)})`
}

/** "PHASE1/PHASE2" -> "Phase 1/2" */
export function phaseLabel(p: string | null | undefined): string {
  if (!p) return '—'
  if (p === 'NA') return 'N/A'
  return 'Phase ' + p.replace(/EARLY_PHASE1/g, 'Early 1').replace(/PHASE/g, '').replace(/\s+/g, '')
}

/** "ACTIVE_NOT_RECRUITING" -> "Active, not recruiting" */
export function statusLabel(s: string | null | undefined): string {
  if (!s) return '—'
  const special: Record<string, string> = { ACTIVE_NOT_RECRUITING: 'Active, not recruiting', AP: 'Approved', CRL: 'Complete response letter', TA: 'Tentative approval' }
  if (special[s]) return special[s]
  const words = s.toLowerCase().replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

// Demo rows use reserved-looking identifiers (see backend/seed_demo.py); don't link those to real sites.
export const isDemoCik = (cik: string | null | undefined) => !!cik && cik.startsWith('999999')
export const isDemoNct = (nct: string | null | undefined) => !!nct && nct.startsWith('NCT99')

export function clinicalTrialsUrl(nct: string): string | null {
  return isDemoNct(nct) ? null : `https://clinicaltrials.gov/study/${nct}`
}

export function edgarFilingUrl(cik: string, accession: string): string | null {
  if (isDemoCik(cik)) return null
  return `https://www.sec.gov/Archives/edgar/data/${Number(cik)}/${accession.replace(/-/g, '')}/`
}
