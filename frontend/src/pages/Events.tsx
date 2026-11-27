import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import EventsTable from '../components/EventsTable'
import { Button, Card, ErrorBox, Loading, PageHeader, Select, Stat } from '../components/ui'
import { api } from '../lib/api'
import { OUTCOMES, outcomeLabel, pct } from '../lib/format'

const FILTERS = ['event_type', 'outcome', 'company_id', 'q', 'date_from', 'date_to', 'sort', 'order'] as const

export default function Events() {
  // Filters live in the URL so a filtered view can be bookmarked or linked from the dashboard.
  const [params, setParams] = useSearchParams()
  const get = (k: (typeof FILTERS)[number]) => params.get(k) ?? ''
  const set = (k: (typeof FILTERS)[number], v: string) => {
    const next = new URLSearchParams(params)
    if (v) next.set(k, v); else next.delete(k)
    setParams(next, { replace: true })
  }
  const filters = Object.fromEntries(FILTERS.map((k) => [k, get(k) || undefined]))

  const companies = useQuery({ queryKey: ['companies'], queryFn: api.companies })
  const events = useQuery({
    queryKey: ['events', filters],
    queryFn: () => api.events(filters),
    placeholderData: keepPreviousData,
  })

  const list = events.data ?? []
  const withReturns = list.filter((e) => e.abnormal_return_1d !== null)
  const avg = withReturns.length ? withReturns.reduce((s, e) => s + e.abnormal_return_1d!, 0) / withReturns.length : null
  const up = withReturns.filter((e) => e.abnormal_return_1d! > 0).length

  return (
    <>
      <PageHeader
        title="Catalyst events"
        subtitle="Every FDA decision and trial readout, with how the stock moved against XBI. Click a row for the full price reaction."
      />

      <Card className="mb-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <label className="col-span-2 flex flex-col gap-1 text-xs font-medium text-muted md:col-span-1 lg:col-span-2">
            Search company or ticker
            <input
              value={get('q')}
              onChange={(e) => set('q', e.target.value)}
              placeholder="e.g. Halcyon or HLCN"
              className="h-9 rounded-lg border border-line bg-surface px-2.5 text-sm text-ink outline-none placeholder:text-muted/70 focus:border-accent"
            />
          </label>
          <Select label="Catalyst" value={get('event_type')} onChange={(v) => set('event_type', v)} options={[
            { value: '', label: 'All catalysts' },
            { value: 'fda_decision', label: 'FDA decisions' },
            { value: 'trial_readout', label: 'Trial readouts' },
          ]} />
          <Select label="Outcome" value={get('outcome')} onChange={(v) => set('outcome', v)} options={[
            { value: '', label: 'All outcomes' },
            ...OUTCOMES.map((o) => ({ value: o, label: outcomeLabel(o) })),
          ]} />
          <Select label="Company" value={get('company_id')} onChange={(v) => set('company_id', v)} options={[
            { value: '', label: 'All companies' },
            ...(companies.data ?? []).map((c) => ({ value: String(c.company_id), label: c.name })),
          ]} />
          <Select label="Sort by" value={`${get('sort') || 'date'}:${get('order') || 'desc'}`}
            onChange={(v) => {
              const [sort, order] = v.split(':')
              const next = new URLSearchParams(params)
              next.set('sort', sort); next.set('order', order)
              setParams(next, { replace: true })
            }}
            options={[
              { value: 'date:desc', label: 'Newest first' },
              { value: 'date:asc', label: 'Oldest first' },
              { value: 'abnormal_1d:desc', label: 'Best day-1 vs XBI' },
              { value: 'abnormal_1d:asc', label: 'Worst day-1 vs XBI' },
              { value: 'abnormal_5d:desc', label: 'Best 5-day vs XBI' },
              { value: 'abnormal_5d:asc', label: 'Worst 5-day vs XBI' },
            ]} />
        </div>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs font-medium text-muted">
            From
            <input type="date" value={get('date_from')} onChange={(e) => set('date_from', e.target.value)}
              className="h-9 rounded-lg border border-line bg-surface px-2.5 text-sm text-ink outline-none focus:border-accent" />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium text-muted">
            To
            <input type="date" value={get('date_to')} onChange={(e) => set('date_to', e.target.value)}
              className="h-9 rounded-lg border border-line bg-surface px-2.5 text-sm text-ink outline-none focus:border-accent" />
          </label>
          {[...params.keys()].length > 0 && (
            <Button variant="secondary" onClick={() => setParams(new URLSearchParams(), { replace: true })}>Clear filters</Button>
          )}
        </div>
      </Card>

      <div className="mb-4 grid grid-cols-3 gap-3">
        <Stat label="Matching events" value={list.length} />
        <Stat label="Avg day-1 vs XBI" value={pct(avg)} tone={avg === null ? undefined : avg >= 0 ? 'pos' : 'neg'} />
        <Stat label="Beat XBI on day 1" value={withReturns.length ? `${up} of ${withReturns.length}` : '—'} />
      </div>

      <Card flush>
        {events.isPending ? <div className="px-5"><Loading /></div>
          : events.error ? <div className="p-4"><ErrorBox error={events.error} /></div>
          : <EventsTable events={list} />}
      </Card>
    </>
  )
}
