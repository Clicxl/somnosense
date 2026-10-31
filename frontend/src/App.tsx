import { useEffect } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router'
import type { Session } from '@/lib/api'
import { useApi } from '@/lib/use-api'
import { cn } from '@/lib/utils'
import History from '@/pages/History'
import LiveView from '@/pages/LiveView'
import MorningReport from '@/pages/MorningReport'

export default function App() {
  const { pathname } = useLocation()
  const sessions = useApi<Session[]>('/api/sessions')
  const { reload } = sessions
  useEffect(reload, [pathname, reload]) // a Sleep Session may have ended since the last page
  const latest = sessions.data?.find((s) => s.ended_at)

  const links = [
    { to: '/', label: 'Live View', active: pathname === '/' },
    { to: latest && `/sessions/${latest.id}`, label: 'Morning Report', active: pathname.startsWith('/sessions/') },
    { to: '/history', label: 'History', active: pathname === '/history' },
  ]

  return (
    <>
      <header className="border-b-2 border-foreground">
        <nav className="mx-auto flex w-full max-w-3xl flex-wrap gap-x-5 gap-y-2 px-5 py-4 text-sm">
          {links.map(({ to, label, active }) =>
            to ? (
              <Link
                key={label}
                to={to}
                aria-current={active ? 'page' : undefined}
                className={cn(active ? 'font-semibold' : 'text-muted-foreground hover:text-foreground')}
              >
                {label}
              </Link>
            ) : (
              <span key={label} aria-disabled="true" title="No finished Sleep Session yet" className="text-muted-foreground/60">
                {label}
              </span>
            ),
          )}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-3xl pb-12">
        <Routes>
          <Route path="/" element={<LiveView />} />
          <Route path="/sessions/:id" element={<MorningReport />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
    </>
  )
}
