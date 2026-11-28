import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { PageHeader, TextLink } from './components/ui'
import Companies from './pages/Companies'
import CompanyDetail from './pages/CompanyDetail'
import Dashboard from './pages/Dashboard'
import EventDetail from './pages/EventDetail'
import Events from './pages/Events'
import Queries from './pages/Queries'
import Trials from './pages/Trials'

function NotFound() {
  return (
    <>
      <PageHeader title="Page not found" subtitle="That address doesn't match any page." />
      <TextLink to="/">← Back to the dashboard</TextLink>
    </>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="events" element={<Events />} />
        <Route path="events/:id" element={<EventDetail />} />
        <Route path="companies" element={<Companies />} />
        <Route path="companies/:id" element={<CompanyDetail />} />
        <Route path="trials" element={<Trials />} />
        <Route path="queries" element={<Queries />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
