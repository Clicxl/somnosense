import { NavLink, Route, Routes } from 'react-router'
import { cn } from '@/lib/utils'
import History from '@/pages/History'
import LiveView from '@/pages/LiveView'
import MorningReport from '@/pages/MorningReport'

const links = [
  { to: '/', label: 'Live View' },
  { to: '/sessions/1', label: 'Morning Report' }, // demo Sleep Session id
  { to: '/history', label: 'History' },
]

export default function App() {
  return (
    <>
      <header className="border-b p-4">
        <nav className="mx-auto flex w-full max-w-3xl flex-wrap gap-4">
          {links.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cn('text-sm', isActive ? 'font-semibold underline underline-offset-4' : 'text-muted-foreground')
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-3xl p-4">
        <Routes>
          <Route path="/" element={<LiveView />} />
          <Route path="/sessions/:id" element={<MorningReport />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
    </>
  )
}
