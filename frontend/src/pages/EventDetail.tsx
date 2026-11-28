import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { ReactionChart } from '../components/charts'
import { Badge, Card, Empty, ErrorBox, ExternalLink, Loading, OutcomeBadge, PageHeader, Stat, TextLink, TypeBadge } from '../components/ui'
import { api } from '../lib/api'
import {
  clinicalTrialsUrl, day, edgarFilingUrl, EVENT_TYPE_LABEL, marketTime, num, pct, phaseLabel, statusLabel,
} from '../lib/format'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[8.5rem_1fr] gap-3 border-b border-line py-2 text-sm last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="min-w-0 break-words text-ink">{children}</dd>
    </div>
  )
}

export default function EventDetail() {
  const id = Number(useParams().id)
  const { data, error, isPending } = useQuery({ queryKey: ['event', id], queryFn: () => api.event(id) })

  if (isPending) return <Loading />
  if (error) return <ErrorBox error={error} />

  const { event: e, trial, fda_action: fda, filing, price_window } = data
  const tone = (x: number | null) => (x === null ? undefined : x >= 0 ? 'pos' : 'neg') as 'pos' | 'neg' | undefined
  const headline = e.event_type === 'fda_decision'
    ? `FDA ${e.outcome === 'approved' ? 'approves' : 'rejects'} ${e.fda_drug ?? 'drug'}`
    : `${phaseLabel(e.phase)} readout: ${e.outcome}`

  return (
    <>
      <div className="mb-3 text-sm">
        <TextLink to="/events">← All events</TextLink>
      </div>
      <PageHeader
        title={<>{e.company_name} <span className="text-muted">· {headline}</span></>}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <TypeBadge type={e.event_type} />
            <OutcomeBadge outcome={e.outcome} />
            <span>News {marketTime(e.event_timestamp)} · traded on {day(e.trading_day)}</span>
          </span>
        }
        actions={<TextLink to={`/companies/${e.company_id}`}>Company profile →</TextLink>}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label={`${e.ticker ?? 'Stock'} return, day 1`} value={pct(e.stock_return_1d)} tone={tone(e.stock_return_1d)} />
        <Stat label="XBI return, day 1" value={pct(e.xbi_return_1d)} hint="the biotech sector that day" />
        <Stat label="Abnormal return, day 1" value={pct(e.abnormal_return_1d)} tone={tone(e.abnormal_return_1d)} hint="stock − XBI" />
        <Stat label="Abnormal return, 5 days" value={pct(e.abnormal_return_5d)} tone={tone(e.abnormal_return_5d)} hint="through day +4" />
      </div>

      <Card
        className="mt-6"
        title={`${e.ticker ?? 'Stock'} vs XBI around the ${EVENT_TYPE_LABEL[e.event_type].toLowerCase()}`}
        subtitle="Both rebased to 100 at the close before the news (day −1). The shaded area is after the news."
      >
        {price_window.length ? <ReactionChart data={price_window} ticker={e.ticker ?? 'Stock'} /> : <Empty>No price data around this date.</Empty>}
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {trial && (
          <Card title="Clinical trial" subtitle="What the readout was about">
            <dl>
              <Row label="NCT number"><ExternalLink href={clinicalTrialsUrl(trial.nct_number)}><span className="font-mono">{trial.nct_number}</span></ExternalLink></Row>
              <Row label="Phase">{phaseLabel(trial.phase)}</Row>
              <Row label="Status">{statusLabel(trial.status)}</Row>
              <Row label="Enrollment">{num(trial.enrollment)} participants</Row>
              <Row label="Conditions">
                <span className="flex flex-wrap gap-1.5">{trial.conditions.map((c) => <Badge key={c.condition_id}>{c.condition_name}</Badge>)}</span>
              </Row>
              <Row label="Drugs">{trial.drugs.map((d) => d.brand_name ? `${d.brand_name} (${d.active_ingredient})` : d.active_ingredient).join(', ')}</Row>
              <Row label="Dates">{day(trial.start_date)} → {day(trial.completion_date)}</Row>
            </dl>
          </Card>
        )}
        {fda && (
          <Card title="FDA action" subtitle="The application that was decided">
            <dl>
              <Row label="Application">{fda.application_number}</Row>
              <Row label="Drug">{fda.brand_name ? `${fda.brand_name} (${fda.active_ingredient})` : fda.active_ingredient}</Row>
              <Row label="Submission">{fda.submission_type === 'ORIG' ? 'Original application' : fda.submission_type}</Row>
              <Row label="Decision">{statusLabel(fda.status)}</Row>
              <Row label="Action date">{day(fda.action_date)}</Row>
            </dl>
          </Card>
        )}
        <Card title="Evidence" subtitle="Where this event comes from">
          <dl>
            {filing ? (
              <>
                <Row label="SEC filing">
                  <ExternalLink href={edgarFilingUrl(e.cik, filing.accession_number)}>
                    {filing.form_type} · <span className="font-mono text-xs">{filing.accession_number}</span>
                  </ExternalLink>
                </Row>
                <Row label="Filed">{day(filing.filing_date)}</Row>
                <Row label="Accepted by SEC">{marketTime(filing.acceptance_timestamp)}</Row>
              </>
            ) : (
              <Row label="SEC filing">None linked</Row>
            )}
            {e.source_url && <Row label="Source"><ExternalLink href={e.source_url}>{new URL(e.source_url).hostname}</ExternalLink></Row>}
            {fda && <Row label="openFDA">The FDA action record itself counts as evidence</Row>}
          </dl>
        </Card>
      </div>
    </>
  )
}
