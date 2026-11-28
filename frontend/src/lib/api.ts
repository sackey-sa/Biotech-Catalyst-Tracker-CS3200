// Types mirror the JSON from the FastAPI backend (backend/routers/*.py).
// Returns are fractions: 0.12 means +12%.

export type EventType = 'fda_decision' | 'trial_readout'
export type Outcome = 'approved' | 'rejected' | 'positive' | 'negative' | 'mixed'

export interface EventRow {
  event_id: number
  event_type: EventType
  outcome: Outcome
  event_timestamp: string
  trading_day: string
  nct_number: string | null
  fda_action_id: number | null
  accession_number: string | null
  source_url: string | null
  company_id: number
  company_name: string
  cik: string
  ticker: string | null
  phase: string | null
  fda_drug: string | null
  stock_return_1d: number | null
  xbi_return_1d: number | null
  abnormal_return_1d: number | null
  stock_return_5d: number | null
  abnormal_return_5d: number | null
}

export interface OutcomeSummary {
  event_type: EventType
  outcome: Outcome
  events: number
  avg_abnormal_1d: number | null
  avg_abnormal_5d: number | null
}

export interface Stats {
  counts: Record<string, number>
  demo_data: boolean
  by_outcome: OutcomeSummary[]
  recent_events: EventRow[]
  price_range: { first: string | null; last: string | null }
}

export interface Drug {
  drug_id: number
  brand_name: string | null
  active_ingredient: string
}

export interface Trial {
  nct_number: string
  company_id: number
  phase: string | null
  status: string
  enrollment: number | null
  start_date: string | null
  completion_date: string | null
}

export interface FdaAction {
  fda_action_id: number
  application_number: string
  company_id: number
  drug_id: number
  submission_type: string
  status: string
  action_date: string
  brand_name: string | null
  active_ingredient: string
}

export interface Filing {
  accession_number: string
  company_id: number
  form_type: string
  filing_date: string
  acceptance_timestamp: string | null
}

export interface WindowPoint {
  rel_day: number
  trade_date: string
  stock_close: number
  xbi_close: number | null
  stock_indexed: number
  xbi_indexed: number | null
}

export interface EventDetail {
  event: EventRow
  trial: (Trial & { conditions: { condition_id: number; condition_name: string }[]; drugs: Drug[] }) | null
  fda_action: FdaAction | null
  filing: Filing | null
  price_window: WindowPoint[]
}

export interface CompanyRow {
  company_id: number
  name: string
  cik: string
  ticker: string | null
  trials: number
  fda_actions: number
  events: number
  avg_abnormal_1d: number | null
  last_close: number | null
}

export interface CompanyTrial extends Trial {
  conditions: string | null
  drugs: string | null
}

export interface CompanyDetail {
  company: { company_id: number; name: string; cik: string; security_id: number | null; ticker: string | null }
  aliases: { alias_name: string; source: string }[]
  trials: CompanyTrial[]
  fda_actions: FdaAction[]
  filings: Filing[]
  events: EventRow[]
}

export interface PricePoint {
  trade_date: string
  close: number
  volume: number
  xbi_close: number | null
}

export interface TrialRow {
  nct_number: string
  phase: string | null
  status: string
  enrollment: number | null
  start_date: string | null
  completion_date: string | null
  company_id: number
  company_name: string
  ticker: string | null
  conditions: string | null
  drugs: string | null
  readout_event_id: number | null
  readout_outcome: Outcome | null
}

export interface TrialFacets {
  phases: { value: string; n: number }[]
  statuses: { value: string; n: number }[]
  conditions: { value: number; label: string; n: number }[]
  by_phase_status: { phase: string | null; status: string; n: number }[]
}

export interface ShowcaseQuery {
  slug: string
  number: number // "-- QUERY N" in sql/03_queries.sql
  graded: boolean // "-- graded: yes"
  file: string
  title: string
  question: string
  notes: string[]
  sql: string
}

export interface QueryResult {
  slug: string
  columns: string[]
  rows: (string | number | null)[][]
  row_count: number
  elapsed_ms: number
}

type Params = Record<string, string | number | undefined | null>

async function request<T>(method: 'GET' | 'POST', path: string, params?: Params): Promise<T> {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== null && v !== '') search.set(k, String(v))
  }
  const qs = search.toString()
  const res = await fetch(`/api${path}${qs ? `?${qs}` : ''}`, { method })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* not JSON, e.g. the proxy could not reach the API */
    }
    throw new Error(res.status === 500 || res.status === 502 || res.status === 504
      ? `The API is not responding (${res.status}). Is the backend running on port 8000?`
      : `${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  stats: () => request<Stats>('GET', '/stats'),
  events: (params: Params) => request<EventRow[]>('GET', '/events', params),
  event: (id: number) => request<EventDetail>('GET', `/events/${id}`),
  companies: () => request<CompanyRow[]>('GET', '/companies'),
  company: (id: number) => request<CompanyDetail>('GET', `/companies/${id}`),
  companyPrices: (id: number, params?: Params) => request<PricePoint[]>('GET', `/companies/${id}/prices`, params),
  trials: (params: Params) => request<TrialRow[]>('GET', '/trials', params),
  trialFacets: () => request<TrialFacets>('GET', '/trials/facets'),
  queries: () => request<ShowcaseQuery[]>('GET', '/queries'),
  runQuery: (slug: string) => request<QueryResult>('POST', `/queries/${slug}/run`),
}
