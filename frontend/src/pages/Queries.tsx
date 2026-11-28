import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Card, ErrorBox, Loading, PageHeader, Table, Td, Th } from '../components/ui'
import { api, type QueryResult, type ShowcaseQuery } from '../lib/api'

function formatCell(v: string | number | null): string {
  if (v === null) return 'NULL'
  if (typeof v === 'number') return Number.isInteger(v) ? v.toLocaleString('en-US') : v.toLocaleString('en-US', { maximumFractionDigits: 4 })
  return v
}

function QueryCard({ index, query, autoRun }: { index: number; query: ShowcaseQuery; autoRun: number }) {
  const [showSql, setShowSql] = useState(true)
  const [lastAutoRun, setLastAutoRun] = useState(0)
  const run = useMutation<QueryResult, Error>({ mutationFn: () => api.runQuery(query.slug) })

  // "Run all" bumps autoRun; each card runs itself once per bump.
  if (autoRun !== lastAutoRun) {
    setLastAutoRun(autoRun)
    if (autoRun > 0) run.mutate()
  }

  return (
    <Card
      title={<span className="flex items-baseline gap-2"><span className="tabular text-muted">Q{index}</span>{query.title}</span>}
      subtitle={<span className="font-mono">backend/queries/{query.file}</span>}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowSql((s) => !s)}>{showSql ? 'Hide SQL' : 'Show SQL'}</Button>
          <Button onClick={() => run.mutate()} disabled={run.isPending}>{run.isPending ? 'Running…' : run.data ? 'Run again' : 'Run query'}</Button>
        </div>
      }
    >
      <p className="text-base text-ink">{query.question}</p>
      {query.notes.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm text-muted">{query.notes.map((n) => <li key={n}>{n}</li>)}</ul>
      )}
      {showSql && (
        <pre className="mt-4 overflow-x-auto rounded-lg border border-line bg-surface-2 p-4 font-mono text-[12.5px] leading-relaxed text-ink">
          {query.sql}
        </pre>
      )}
      {run.error && <div className="mt-4"><ErrorBox error={run.error} /></div>}
      {run.isPending && !run.data && <Loading label="Running against MySQL…" />}
      {run.data && (
        <div className="mt-4">
          <div className="mb-2 text-xs text-muted">
            {run.data.row_count} {run.data.row_count === 1 ? 'row' : 'rows'} · {run.data.elapsed_ms} ms
          </div>
          <div className="overflow-hidden rounded-lg border border-line">
            <Table>
              <thead><tr>{run.data.columns.map((c) => <Th key={c} right={typeof run.data!.rows[0]?.[run.data!.columns.indexOf(c)] === 'number'}>{c}</Th>)}</tr></thead>
              <tbody>
                {run.data.rows.map((r, i) => (
                  <tr key={i}>
                    {r.map((v, j) => (
                      <Td key={j} right={typeof v === 'number'} className={v === null ? 'text-muted' : ''}>{formatCell(v)}</Td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </div>
      )}
    </Card>
  )
}

export default function Queries() {
  const { data, error, isPending } = useQuery({ queryKey: ['queries'], queryFn: api.queries })
  const [runAll, setRunAll] = useState(0)

  return (
    <>
      <PageHeader
        title="SQL showcase"
        subtitle="The queries behind the analysis, each with the question it answers. Run any of them live against the MySQL database. Each one is a .sql file in backend/queries, the same files used for the queries-and-output PDF."
        actions={<Button onClick={() => setRunAll((n) => n + 1)} disabled={!data}>Run all queries</Button>}
      />
      {isPending ? <Loading /> : error ? <ErrorBox error={error} /> : (
        <div className="space-y-6">
          {data.map((q, i) => <QueryCard key={q.slug} index={i + 1} query={q} autoRun={runAll} />)}
        </div>
      )}
    </>
  )
}
