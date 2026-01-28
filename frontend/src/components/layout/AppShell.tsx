import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { Shield, LogOut, FolderOpen, Cpu } from 'lucide-react'

export default function AppShell() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="border-b border-white/10 bg-black/30 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <Shield className="w-7 h-7 text-purple-400" />
            <span className="text-white font-semibold text-lg">SecureReq AI</span>
            <span className="text-white/40 text-sm hidden sm:inline">| Shift-Left Security Platform</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2 text-sm text-gray-300 hover:text-white">
              <FolderOpen className="w-4 h-4" /> Projects
            </Link>
            <Link to="/ai-console" className="flex items-center gap-2 text-sm text-gray-300 hover:text-white">
              <Cpu className="w-4 h-4" /> AI Console
            </Link>
            <div className="flex items-center gap-2 bg-green-500/20 border border-green-500/30 px-3 py-1.5 rounded-full">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-green-400 text-xs font-medium">AI Active</span>
            </div>
            {user && <span className="text-gray-400 text-sm hidden sm:inline">{user.email}</span>}
            <button onClick={() => { logout(); navigate('/login') }} className="text-gray-400 hover:text-white">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
