import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceArea, ReferenceDot, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { EventRow, OutcomeSummary, PricePoint, WindowPoint } from '../lib/api'
import { day, EVENT_TYPE_LABEL, money, outcomeColor, outcomeLabel, pct } from '../lib/format'

const axis = { stroke: 'var(--muted)', fontSize: 12, tickLine: false, axisLine: false } as const
const grid = <CartesianGrid stroke="var(--grid)" vertical={false} />
const tooltipStyle = {
  contentStyle: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, fontSize: 12, color: 'var(--text)' },
  labelStyle: { color: 'var(--muted)', marginBottom: 4 },
  itemStyle: { padding: 0 },
}

/** Stock vs XBI around one event, both rebased to 100 at the close before the news (day −1). */
export function ReactionChart({ data, ticker }: { data: WindowPoint[]; ticker: string }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 16, right: 16, bottom: 4, left: -8 }}>
        {grid}
        <XAxis dataKey="rel_day" {...axis} tickFormatter={(d: number) => (d === 0 ? 'Event' : d > 0 ? `+${d}` : `${d}`)} />
        <YAxis {...axis} domain={['auto', 'auto']} tickFormatter={(v: number) => v.toFixed(0)} width={48} />
        <ReferenceArea x1={0} x2={data.length ? Math.max(...data.map((d) => d.rel_day)) : 0} fill="var(--accent)" fillOpacity={0.05} />
        <ReferenceLine x={0} stroke="var(--accent)" strokeDasharray="4 4" />
        <ReferenceLine y={100} stroke="var(--border)" />
        <Tooltip
          {...tooltipStyle}
          labelFormatter={(d) => {
            const p = data.find((x) => x.rel_day === d)
            const n = Number(d)
            return `${n === 0 ? 'Event day' : `Day ${n > 0 ? '+' : ''}${n}`}${p ? ` · ${day(p.trade_date)}` : ''}`
          }}
          formatter={(v, name) => [`${Number(v).toFixed(1)} (${pct(Number(v) / 100 - 1)})`, name]}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        <Line isAnimationActive={false} type="monotone" dataKey="stock_indexed" name={ticker} stroke="var(--accent)" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
        <Line isAnimationActive={false} type="monotone" dataKey="xbi_indexed" name="XBI (biotech index)" stroke="var(--bench)" strokeWidth={2} strokeDasharray="5 4" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

/** Average 1-day abnormal return per outcome, one bar each. */
export function OutcomeBars({ data, onSelect }: { data: OutcomeSummary[]; onSelect?: (row: OutcomeSummary) => void }) {
  const rows = data.map((d) => ({
    ...d,
    label: `${outcomeLabel(d.outcome)} · ${EVENT_TYPE_LABEL[d.event_type].split(' ')[0]}`,
    value: (d.avg_abnormal_1d ?? 0) * 100,
  })).sort((a, b) => b.value - a.value)
  return (
    <ResponsiveContainer width="100%" height={Math.max(180, rows.length * 46)}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 48, bottom: 4, left: 8 }}>
        <CartesianGrid stroke="var(--grid)" horizontal={false} />
        <XAxis type="number" {...axis} tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v.toFixed(0)}%`} />
        <YAxis type="category" dataKey="label" {...axis} width={128} />
        <ReferenceLine x={0} stroke="var(--muted)" />
        <Tooltip
          {...tooltipStyle}
          cursor={{ fill: 'var(--surface-2)' }}
          formatter={(_v, _n, item) => {
            const r = item.payload as OutcomeSummary
            return [`${pct(r.avg_abnormal_1d)} day 1 · ${pct(r.avg_abnormal_5d)} 5-day · ${r.events} events`, 'Avg vs XBI']
          }}
        />
        <Bar isAnimationActive={false}
          dataKey="value"
          radius={4}
          barSize={22}
          label={{ position: 'right', fontSize: 12, fill: 'var(--text)', formatter: (v: unknown) => pct(Number(v) / 100) }}
          onClick={onSelect ? (d) => onSelect(d.payload as OutcomeSummary) : undefined}
          style={onSelect ? { cursor: 'pointer' } : undefined}
        >
          {rows.map((r) => <Cell key={`${r.event_type}-${r.outcome}`} fill={outcomeColor(r.outcome)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

/** Company closing price with XBI scaled to start at the same price, plus a dot on each event day. */
export function PriceHistoryChart({ prices, events, ticker, onEventClick }: {
  prices: PricePoint[]; events: EventRow[]; ticker: string; onEventClick?: (id: number) => void
}) {
  const first = prices.find((p) => p.xbi_close !== null)
  const scale = first && first.xbi_close ? first.close / first.xbi_close : 1
  const data = prices.map((p) => ({ ...p, xbi_scaled: p.xbi_close !== null ? p.xbi_close * scale : null }))
  const byDate = new Map(data.map((p) => [p.trade_date, p]))
  const visible = events.filter((e) => byDate.has(e.trading_day))

  return (
    <ResponsiveContainer width="100%" height={340}>
      <LineChart data={data} margin={{ top: 16, right: 16, bottom: 4, left: -4 }}>
        {grid}
        <XAxis dataKey="trade_date" {...axis} minTickGap={48}
          tickFormatter={(d: string) => new Date(`${d}T00:00:00Z`).toLocaleDateString('en-US', { month: 'short', year: '2-digit', timeZone: 'UTC' })} />
        <YAxis {...axis} domain={['auto', 'auto']} tickFormatter={(v: number) => `$${v.toFixed(0)}`} width={52} />
        <Tooltip
          {...tooltipStyle}
          labelFormatter={(d) => {
            const ev = events.find((e) => e.trading_day === d)
            return `${day(String(d))}${ev ? ` · ${EVENT_TYPE_LABEL[ev.event_type]} (${outcomeLabel(ev.outcome)})` : ''}`
          }}
          formatter={(v, name) => [money(Number(v)), name]}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        <Line isAnimationActive={false} type="linear" dataKey="close" name={ticker} stroke="var(--accent)" strokeWidth={1.75} dot={false} />
        <Line isAnimationActive={false} type="linear" dataKey="xbi_scaled" name="XBI (scaled to same start)" stroke="var(--bench)" strokeWidth={1.25} strokeDasharray="4 3" dot={false} />
        {visible.map((e) => (
          <ReferenceDot
            key={e.event_id}
            x={e.trading_day}
            y={byDate.get(e.trading_day)!.close}
            r={6}
            fill={outcomeColor(e.outcome)}
            stroke="var(--surface)"
            strokeWidth={2}
            onClick={onEventClick ? () => onEventClick(e.event_id) : undefined}
            style={onEventClick ? { cursor: 'pointer' } : undefined}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

/** Trials per phase, stacked by status. */
export function PhaseStatusBars({ data }: { data: { phase: string | null; status: string; n: number }[] }) {
  const statuses = [...new Set(data.map((d) => d.status))]
  const phases = [...new Set(data.map((d) => d.phase ?? 'NA'))].sort()
  const rows = phases.map((phase) => {
    const row: Record<string, string | number> = { phase: phase === 'NA' ? 'N/A' : 'Phase ' + phase.replace(/PHASE/g, '') }
    for (const s of statuses) row[s] = data.find((d) => (d.phase ?? 'NA') === phase && d.status === s)?.n ?? 0
    return row
  })
  const palette: Record<string, string> = {
    COMPLETED: 'var(--accent)', RECRUITING: 'var(--pos)', ACTIVE_NOT_RECRUITING: 'var(--mixed)',
    TERMINATED: 'var(--neg)', NOT_YET_RECRUITING: 'var(--bench)',
  }
  const label = (s: string) => s.charAt(0) + s.slice(1).toLowerCase().replace(/_/g, ' ')
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: -16 }}>
        {grid}
        <XAxis dataKey="phase" {...axis} />
        <YAxis {...axis} allowDecimals={false} />
        <Tooltip {...tooltipStyle} cursor={{ fill: 'var(--surface-2)' }} />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} formatter={(v: string) => label(v)} />
        {statuses.map((s, i) => (
          <Bar isAnimationActive={false} key={s} dataKey={s} name={s} stackId="a" fill={palette[s] ?? 'var(--bench)'}
            radius={i === statuses.length - 1 ? [4, 4, 0, 0] : 0} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
