import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Card, ErrorBox, Loading, PageHeader, Ret, Table, Td, Th } from '../components/ui'
import { api } from '../lib/api'
import { money } from '../lib/format'

export default function Companies() {
  const navigate = useNavigate()
  const { data, error, isPending } = useQuery({ queryKey: ['companies'], queryFn: api.companies })

  return (
    <>
      <PageHeader title="Companies" subtitle="Each public company with its pipeline size, FDA history and how its stock has reacted to news." />
      <Card flush>
        {isPending ? <div className="px-5"><Loading /></div> : error ? <div className="p-4"><ErrorBox error={error} /></div> : (
          <Table>
            <thead>
              <tr>
                <Th>Company</Th>
                <Th>Ticker</Th>
                <Th right>Trials</Th>
                <Th right>FDA actions</Th>
                <Th right>Events</Th>
                <Th right>Avg day-1 vs XBI</Th>
                <Th right>Last close</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr
                  key={c.company_id}
                  onClick={() => navigate(`/companies/${c.company_id}`)}
                  onKeyDown={(k) => k.key === 'Enter' && navigate(`/companies/${c.company_id}`)}
                  tabIndex={0}
                  className="cursor-pointer outline-none transition hover:bg-surface-2 focus-visible:bg-surface-2"
                >
                  <Td><span className="font-medium">{c.name}</span><div className="text-xs text-muted">CIK {c.cik}</div></Td>
                  <Td className="font-mono text-xs">{c.ticker ?? '—'}</Td>
                  <Td right>{c.trials}</Td>
                  <Td right>{c.fda_actions}</Td>
                  <Td right>{c.events}</Td>
                  <Td right><Ret value={c.avg_abnormal_1d} /></Td>
                  <Td right>{money(c.last_close)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </>
  )
}
