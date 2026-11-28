import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { PhaseStatusBars } from '../components/charts'
import {
  Button, Card, Empty, ErrorBox, ExternalLink, Loading, OutcomeBadge, PageHeader, Select, Table, Td, TextLink, Th,
} from '../components/ui'
import { api } from '../lib/api'
import { clinicalTrialsUrl, day, num, phaseLabel, statusLabel } from '../lib/format'

const FILTERS = ['phase', 'status', 'condition_id', 'q'] as const

export default function Trials() {
  const [params, setParams] = useSearchParams()
  const get = (k: (typeof FILTERS)[number]) => params.get(k) ?? ''
  const set = (k: (typeof FILTERS)[number], v: string) => {
    const next = new URLSearchParams(params)
    if (v) next.set(k, v); else next.delete(k)
    setParams(next, { replace: true })
  }
  const filters = Object.fromEntries(FILTERS.map((k) => [k, get(k) || undefined]))

  const facets = useQuery({ queryKey: ['trialFacets'], queryFn: api.trialFacets })
  const trials = useQuery({ queryKey: ['trials', filters], queryFn: () => api.trials(filters), placeholderData: keepPreviousData })

  return (
    <>
      <PageHeader title="Clinical trials" subtitle="Company-sponsored trials from ClinicalTrials.gov, with the diseases they study and the drugs they test." />

      <div className="mb-6 grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3" title="Trials by phase and status">
          {facets.isPending ? <Loading /> : facets.error ? <ErrorBox error={facets.error} /> : <PhaseStatusBars data={facets.data.by_phase_status} />}
        </Card>
        <Card className="lg:col-span-2" title="Most-studied conditions" flush>
          {facets.data && (
            <ul className="divide-y divide-line">
              {[...facets.data.conditions].sort((a, b) => b.n - a.n).slice(0, 7).map((c) => (
                <li key={c.value}>
                  <button type="button" onClick={() => set('condition_id', String(c.value))}
                    className="flex w-full items-center justify-between gap-3 px-5 py-2.5 text-left text-sm hover:bg-surface-2">
                    <span className="truncate">{c.label}</span>
                    <span className="tabular text-muted">{c.n}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card className="mb-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <label className="col-span-2 flex flex-col gap-1 text-xs font-medium text-muted">
            Search trial, company, condition or drug
            <input value={get('q')} onChange={(e) => set('q', e.target.value)} placeholder="e.g. lung, NCT99…, Corvane"
              className="h-9 rounded-lg border border-line bg-surface px-2.5 text-sm text-ink outline-none placeholder:text-muted/70 focus:border-accent" />
          </label>
          <Select label="Phase" value={get('phase')} onChange={(v) => set('phase', v)} options={[
            { value: '', label: 'All phases' },
            ...(facets.data?.phases ?? []).map((p) => ({ value: p.value, label: `${phaseLabel(p.value)} (${p.n})` })),
          ]} />
          <Select label="Status" value={get('status')} onChange={(v) => set('status', v)} options={[
            { value: '', label: 'All statuses' },
            ...(facets.data?.statuses ?? []).map((s) => ({ value: s.value, label: `${statusLabel(s.value)} (${s.n})` })),
          ]} />
          <Select label="Condition" value={get('condition_id')} onChange={(v) => set('condition_id', v)} options={[
            { value: '', label: 'All conditions' },
            ...(facets.data?.conditions ?? []).map((c) => ({ value: String(c.value), label: c.label })),
          ]} />
        </div>
        {[...params.keys()].length > 0 && (
          <div className="mt-3"><Button variant="secondary" onClick={() => setParams(new URLSearchParams(), { replace: true })}>Clear filters</Button></div>
        )}
      </Card>

      <Card flush title={trials.data ? `${trials.data.length} trials` : undefined}>
        {trials.isPending ? <div className="px-5"><Loading /></div> : trials.error ? <div className="p-4"><ErrorBox error={trials.error} /></div>
          : !trials.data.length ? <Empty>No trials match these filters.</Empty> : (
            <Table>
              <thead>
                <tr><Th>Trial</Th><Th>Sponsor</Th><Th>Phase</Th><Th>Status</Th><Th>Conditions</Th><Th>Drugs</Th><Th right>Enrollment</Th><Th>Start</Th><Th>Readout</Th></tr>
              </thead>
              <tbody>
                {trials.data.map((t) => (
                  <tr key={t.nct_number}>
                    <Td><ExternalLink href={clinicalTrialsUrl(t.nct_number)}><span className="font-mono text-xs">{t.nct_number}</span></ExternalLink></Td>
                    <Td><TextLink to={`/companies/${t.company_id}`}>{t.company_name}</TextLink></Td>
                    <Td className="whitespace-nowrap">{phaseLabel(t.phase)}</Td>
                    <Td>{statusLabel(t.status)}</Td>
                    <Td>{t.conditions ?? '—'}</Td>
                    <Td>{t.drugs ?? '—'}</Td>
                    <Td right>{num(t.enrollment)}</Td>
                    <Td className="whitespace-nowrap">{day(t.start_date)}</Td>
                    <Td>
                      {t.readout_event_id && t.readout_outcome
                        ? <Link to={`/events/${t.readout_event_id}`} title="Open the readout event"><OutcomeBadge outcome={t.readout_outcome} /></Link>
                        : <span className="text-muted">—</span>}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
      </Card>
    </>
  )
}
