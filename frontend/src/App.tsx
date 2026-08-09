// AgentForge – App Root  ·  Industrial Foundry Edition
import { BrowserRouter, Route, Routes, Link, useLocation } from 'react-router-dom'
import ResearchPage from '@/pages/ResearchPage'
import HistoryPage from '@/pages/HistoryPage'
import './index.css'

function NavBar() {
  const { pathname } = useLocation()
  return (
    <nav
      className="border-b border-forge-border bg-forge-panel"
      style={{ boxShadow: '0 1px 0 rgba(255,106,61,0.12)' }}
    >
      <div className="mx-auto flex max-w-5xl items-center gap-1 px-5 py-0">
        {/* Logo */}
        <Link
          to="/"
          className="mr-5 flex items-center gap-2.5 py-3 font-display text-sm
                     font-bold uppercase tracking-widest text-forge-paper
                     transition-colors hover:text-forge-ember"
        >
          {/* Foundry mark — two triangles forming a flame/anvil */}
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
            <polygon points="11,2 20,18 2,18" stroke="#ff6a3d" strokeWidth="1.5"
                     fill="rgba(255,106,61,0.1)" strokeLinejoin="round" />
            <polygon points="11,8 17,18 5,18" fill="#ff6a3d" opacity="0.7" />
            <circle cx="11" cy="18" r="1.5" fill="#ff6a3d" />
          </svg>
          AgentForge
        </Link>

        {/* Separator */}
        <div className="h-4 w-px bg-forge-border mx-1" />

        {/* Nav links */}
        {[
          { to: '/',        label: 'Research' },
          { to: '/history', label: 'History'  },
        ].map(({ to, label }) => {
          const active = pathname === to
          return (
            <Link
              key={to}
              to={to}
              className={`relative px-3 py-3 font-mono text-xs uppercase tracking-widest
                transition-colors
                ${active ? 'text-forge-ember' : 'text-forge-steel hover:text-forge-paper'}`}
            >
              {label}
              {active && (
                <span className="absolute bottom-0 left-2 right-2 h-px bg-forge-ember" />
              )}
            </Link>
          )
        })}

        {/* Right: status dot */}
        <div className="ml-auto flex items-center gap-1.5">
          <span
            className="h-1.5 w-1.5 rounded-full bg-forge-success anim-ember-pulse"
            style={{ boxShadow: '0 0 4px rgba(95,191,143,0.7)' }}
          />
          <span className="font-mono text-[10px] uppercase tracking-widest text-forge-success/70">
            Online
          </span>
        </div>
      </div>
    </nav>
  )
}

function AppLayout() {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/" element={<ResearchPage />} />
        <Route path="/research/:sessionId" element={<ResearchPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Routes>
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}
