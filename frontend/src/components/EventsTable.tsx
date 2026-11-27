import { useNavigate } from 'react-router-dom'
import type { EventRow } from '../lib/api'
import { day, phaseLabel } from '../lib/format'
import { Empty, OutcomeBadge, Ret, Table, Td, Th, TypeBadge } from './ui'

/** Event list; a click anywhere on a row opens the event. */
export default function EventsTable({ events, showCompany = true, compact = false }: {
  events: EventRow[]; showCompany?: boolean; compact?: boolean
}) {
  const navigate = useNavigate()
  if (!events.length) return <Empty>No events match these filters.</Empty>
  return (
    <Table>
      <thead>
        <tr>
          <Th>Trading day</Th>
          {showCompany && <Th>Company</Th>}
          <Th>Catalyst</Th>
          <Th>Outcome</Th>
          {!compact && <Th>Subject</Th>}
          <Th right>Stock, day 1</Th>
          <Th right>vs XBI, day 1</Th>
          {!compact && <Th right>vs XBI, 5 days</Th>}
        </tr>
      </thead>
      <tbody>
        {events.map((e) => (
          <tr
            key={e.event_id}
            onClick={() => navigate(`/events/${e.event_id}`)}
            onKeyDown={(k) => k.key === 'Enter' && navigate(`/events/${e.event_id}`)}
            tabIndex={0}
            className="cursor-pointer outline-none transition hover:bg-surface-2 focus-visible:bg-surface-2"
          >
            <Td className="whitespace-nowrap tabular">{day(e.trading_day)}</Td>
            {showCompany && (
              <Td>
                <span className="font-medium">{e.company_name}</span>
                {e.ticker && <span className="ml-1.5 text-xs text-muted">{e.ticker}</span>}
              </Td>
            )}
            <Td><TypeBadge type={e.event_type} /></Td>
            <Td><OutcomeBadge outcome={e.outcome} /></Td>
            {!compact && (
              <Td className="text-muted">
                {e.event_type === 'trial_readout'
                  ? <>{phaseLabel(e.phase)} · <span className="font-mono text-xs">{e.nct_number}</span></>
                  : e.fda_drug}
              </Td>
            )}
            <Td right><Ret value={e.stock_return_1d} /></Td>
            <Td right><Ret value={e.abnormal_return_1d} /></Td>
            {!compact && <Td right><Ret value={e.abnormal_return_5d} /></Td>}
          </tr>
        ))}
      </tbody>
    </Table>
  )
}
