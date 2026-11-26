import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { OutcomeBars } from '../components/charts'
import EventsTable from '../components/EventsTable'
import { Card, Empty, ErrorBox, Loading, PageHeader, Stat } from '../components/ui'
import { api } from '../lib/api'
import { day, num, pct } from '../lib/format'

export default function Dashboard() {
  const navigate = useNavigate()
  const { data, error, isPending } = useQuery({ queryKey: ['stats'], queryFn: api.stats })

  if (isPending) return <Loading />
  if (error) return <ErrorBox error={error} />

  const { counts, by_outcome, recent_events, price_range } = data
  const find = (o: string) => by_outcome.find((r) => r.outcome === o)
  const approved = find('approved')
  const negative = find('negative')

  return (
    <>
      <PageHeader
        title="How do biotech stocks react to FDA decisions and trial results?"
        subtitle={
          <>
            Every catalyst is matched to the company's stock and compared with the XBI biotech index, so a
            sector-wide move isn't mistaken for news. <span className="text-ink">Abnormal return</span> = stock
            return − XBI return, from the close before the news.
          </>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Catalyst events" value={num(counts.events)} hint={`${num(counts.fda_actions)} FDA actions · ${num(counts.trials)} trials`} />
        <Stat label="Companies tracked" value={num(counts.companies)} hint={`${num(counts.filings)} SEC filings`} />
        <Stat
          label="Avg day-1 move, FDA approval"
          value={pct(approved?.avg_abnormal_1d)}
          tone={approved?.avg_abnormal_1d && approved.avg_abnormal_1d < 0 ? 'neg' : 'pos'}
          hint={approved ? `vs XBI · ${approved.events} approvals` : 'no approvals yet'}
        />
        <Stat
          label="Avg day-1 move, failed trial"
          value={pct(negative?.avg_abnormal_1d)}
          tone="neg"
          hint={negative ? `vs XBI · ${negative.events} readouts` : 'no negative readouts yet'}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <Card
          className="lg:col-span-3"
          title="Average day-1 reaction vs XBI, by outcome"
          subtitle="Click a bar to see those events"
        >
          {by_outcome.length
            ? <OutcomeBars data={by_outcome} onSelect={(r) => navigate(`/events?event_type=${r.event_type}&outcome=${r.outcome}`)} />
            : <Empty>No events with price data yet.</Empty>}
        </Card>

        <Card className="lg:col-span-2" title="What's in the database">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            {[
              ['Companies', counts.companies], ['Securities', counts.securities],
              ['Daily prices', counts.prices], ['Drugs', counts.drugs],
              ['Conditions', counts.conditions], ['Clinical trials', counts.trials],
              ['FDA actions', counts.fda_actions], ['SEC filings', counts.filings],
            ].map(([label, n]) => (
              <div key={label as string} className="flex items-baseline justify-between gap-2 border-b border-line pb-2">
                <dt className="text-muted">{label}</dt>
                <dd className="tabular font-medium">{num(n as number)}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-xs text-muted">
            Prices from {day(price_range.first)} to {day(price_range.last)}.{' '}
            <Link to="/queries" className="font-medium text-accent hover:underline">See the SQL behind the analysis →</Link>
          </p>
        </Card>
      </div>

      <Card
        className="mt-6"
        title="Latest catalysts"
        actions={<Link to="/events" className="text-sm font-medium text-accent hover:underline">All events →</Link>}
        flush
      >
        <EventsTable events={recent_events} compact />
      </Card>
    </>
  )
}
