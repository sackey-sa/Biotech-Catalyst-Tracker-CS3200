import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PriceHistoryChart } from '../components/charts'
import EventsTable from '../components/EventsTable'
import {
  Badge, Card, Empty, ErrorBox, ExternalLink, Loading, OutcomeBadge, PageHeader, Stat, Table, Td, TextLink, Th,
} from '../components/ui'
import { api } from '../lib/api'
import { clinicalTrialsUrl, day, edgarFilingUrl, marketTime, money, num, pct, phaseLabel, statusLabel } from '../lib/format'

const RANGES = [
  { key: '6m', label: '6M', months: 6 },
  { key: '1y', label: '1Y', months: 12 },
  { key: 'all', label: 'All', months: 0 },
] as const

export default function CompanyDetail() {
  const id = Number(useParams().id)
  const navigate = useNavigate()
  const [range, setRange] = useState<(typeof RANGES)[number]['key']>('all')

  const company = useQuery({ queryKey: ['company', id], queryFn: () => api.company(id) })
  const prices = useQuery({ queryKey: ['prices', id], queryFn: () => api.companyPrices(id) })

  if (company.isPending) return <Loading />
  if (company.error) return <ErrorBox error={company.error} />

  const { company: c, aliases, trials, fda_actions, filings, events } = company.data
  const all = prices.data ?? []
  const months = RANGES.find((r) => r.key === range)!.months
  let cutoff = ''
  if (months && all.length) {
    const d = new Date(`${all[all.length - 1].trade_date}T00:00:00Z`)
    d.setUTCMonth(d.getUTCMonth() - months)
    cutoff = d.toISOString().slice(0, 10)
  }
  const shown = cutoff ? all.filter((p) => p.trade_date >= cutoff) : all
  const last = all[all.length - 1]
  const firstShown = shown[0]
  const periodReturn = last && firstShown ? last.close / firstShown.close - 1 : null
  const withReturns = events.filter((e) => e.abnormal_return_1d !== null)
  const avg = withReturns.length ? withReturns.reduce((s, e) => s + e.abnormal_return_1d!, 0) / withReturns.length : null

  return (
    <>
      <div className="mb-3 text-sm"><TextLink to="/companies">← All companies</TextLink></div>
      <PageHeader
        title={<>{c.name} {c.ticker && <span className="font-mono text-xl text-muted">{c.ticker}</span>}</>}
        subtitle={
          <span className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1">CIK {c.cik}</span>
            {aliases.map((a) => <Badge key={a.alias_name}>{a.alias_name} <span className="ml-1 opacity-60">{a.source}</span></Badge>)}
          </span>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Last close" value={money(last?.close)} hint={last ? day(last.trade_date) : undefined} />
        <Stat label="Clinical trials" value={trials.length} hint={`${trials.filter((t) => t.status === 'RECRUITING').length} recruiting`} />
        <Stat label="FDA actions" value={fda_actions.length} hint={`${fda_actions.filter((f) => f.status === 'AP').length} approved`} />
        <Stat label="Avg day-1 vs XBI" value={pct(avg)} tone={avg === null ? undefined : avg >= 0 ? 'pos' : 'neg'} hint={`${events.length} events`} />
      </div>

      <Card
        className="mt-6"
        title="Share price and catalysts"
        subtitle={`Dots are events (green good, red bad, amber mixed); click one to open it. ${periodReturn !== null ? `${pct(periodReturn)} over this period.` : ''}`}
        actions={
          <div className="flex rounded-lg border border-line p-0.5">
            {RANGES.map((r) => (
              <button key={r.key} type="button" onClick={() => setRange(r.key)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium ${range === r.key ? 'bg-accent-soft text-accent' : 'text-muted hover:text-ink'}`}>
                {r.label}
              </button>
            ))}
          </div>
        }
      >
        {prices.isPending ? <Loading /> : prices.error ? <ErrorBox error={prices.error} />
          : shown.length ? <PriceHistoryChart prices={shown} events={events} ticker={c.ticker ?? 'Stock'} onEventClick={(eid) => navigate(`/events/${eid}`)} />
          : <Empty>No price history for this company.</Empty>}
      </Card>

      <Card className="mt-6" title="Catalyst events" flush>
        <EventsTable events={[...events].reverse()} showCompany={false} />
      </Card>

      <Card className="mt-6" title="Clinical pipeline" subtitle="Trials sponsored by this company" flush>
        {trials.length ? (
          <Table>
            <thead><tr><Th>Trial</Th><Th>Phase</Th><Th>Status</Th><Th>Conditions</Th><Th>Drugs</Th><Th right>Enrollment</Th><Th>Start</Th></tr></thead>
            <tbody>
              {trials.map((t) => (
                <tr key={t.nct_number}>
                  <Td><ExternalLink href={clinicalTrialsUrl(t.nct_number)}><span className="font-mono text-xs">{t.nct_number}</span></ExternalLink></Td>
                  <Td>{phaseLabel(t.phase)}</Td>
                  <Td>{statusLabel(t.status)}</Td>
                  <Td>{t.conditions ?? '—'}</Td>
                  <Td>{t.drugs ?? '—'}</Td>
                  <Td right>{num(t.enrollment)}</Td>
                  <Td className="whitespace-nowrap">{day(t.start_date)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : <Empty>No trials.</Empty>}
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="FDA actions" flush>
          {fda_actions.length ? (
            <Table>
              <thead><tr><Th>Application</Th><Th>Drug</Th><Th>Decision</Th><Th>Date</Th></tr></thead>
              <tbody>
                {fda_actions.map((f) => {
                  const ev = events.find((e) => e.fda_action_id === f.fda_action_id)
                  return (
                    <tr key={f.fda_action_id}>
                      <Td className="whitespace-nowrap">{f.application_number}</Td>
                      <Td>{f.brand_name ?? f.active_ingredient}</Td>
                      <Td>{ev ? <OutcomeBadge outcome={ev.outcome} /> : statusLabel(f.status)}</Td>
                      <Td className="whitespace-nowrap">{ev ? <TextLink to={`/events/${ev.event_id}`}>{day(f.action_date)}</TextLink> : day(f.action_date)}</Td>
                    </tr>
                  )
                })}
              </tbody>
            </Table>
          ) : <Empty>No FDA actions.</Empty>}
        </Card>
        <Card title="SEC filings" flush>
          {filings.length ? (
            <Table>
              <thead><tr><Th>Form</Th><Th>Accession number</Th><Th>Filed</Th><Th>Accepted</Th></tr></thead>
              <tbody>
                {filings.map((f) => (
                  <tr key={f.accession_number}>
                    <Td>{f.form_type}</Td>
                    <Td><ExternalLink href={edgarFilingUrl(c.cik, f.accession_number)}><span className="font-mono text-xs">{f.accession_number}</span></ExternalLink></Td>
                    <Td className="whitespace-nowrap">{day(f.filing_date)}</Td>
                    <Td className="whitespace-nowrap text-muted">{f.acceptance_timestamp ? marketTime(f.acceptance_timestamp) : '—'}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : <Empty>No filings.</Empty>}
        </Card>
      </div>
    </>
  )
}
