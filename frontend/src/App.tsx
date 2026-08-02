// AgentForge – React App Root
import { BrowserRouter, Route, Routes, Link, useLocation } from 'react-router-dom'
import ResearchPage from '@/pages/ResearchPage'
import HistoryPage from '@/pages/HistoryPage'
import './index.css'

function NavBar() {
  const { pathname } = useLocation()
  return (
    <nav className="border-b border-gray-200 bg-white px-4 py-2.5">
      <div className="mx-auto flex max-w-6xl items-center gap-6">
        <Link to="/" className="flex items-center gap-1.5 text-base font-bold text-gray-900 hover:text-blue-600">
          🤖 AgentForge
        </Link>
        <Link
          to="/"
          className={`text-sm font-medium transition ${pathname === '/' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-900'}`}
        >
          Research
        </Link>
        <Link
          to="/history"
          className={`text-sm font-medium transition ${pathname === '/history' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-900'}`}
        >
          History
        </Link>
      </div>
    </nav>
  )
}

// Layout wraps NavBar + Routes — NavBar must be inside BrowserRouter to use hooks
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
