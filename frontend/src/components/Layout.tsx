import { useQuery } from '@tanstack/react-query'
import { NavLink, Outlet } from 'react-router-dom'
import { api } from '../lib/api'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/events', label: 'Events' },
  { to: '/companies', label: 'Companies' },
  { to: '/trials', label: 'Trials' },
  { to: '/queries', label: 'SQL Showcase' },
]

export default function Layout() {
  // Same query key as the dashboard, so this costs no extra request there.
  const { data: stats } = useQuery({ queryKey: ['stats'], queryFn: api.stats })

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2.5">
            <img src="/favicon.svg" alt="" className="h-7 w-7" />
            <span className="font-semibold tracking-tight text-ink">Biotech Catalyst Tracker</span>
          </NavLink>
          {stats?.demo_data && (
            <span
              className="rounded-full bg-mixed-soft px-2 py-0.5 text-xs font-medium text-mixed"
              title="Companies, trials and prices are fictional sample data from backend/seed_demo.py"
            >
              Demo data
            </span>
          )}
          <nav className="-mx-1 flex w-full gap-1 overflow-x-auto sm:ml-auto sm:w-auto">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    isActive ? 'bg-accent-soft text-accent' : 'text-muted hover:bg-surface-2 hover:text-ink'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-muted sm:px-6">
        CS3200 project · Data: SEC EDGAR, ClinicalTrials.gov, openFDA, daily prices
        {stats?.demo_data && ' · currently showing fictional demo data'}
      </footer>
    </div>
  )
}
